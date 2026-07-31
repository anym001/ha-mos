"""
API Client for mos.

This module provides the API client for communicating with the local MOS REST API.
Most resources (``osinfo``, ``services``) live under ``/api/v1/mos/<resource>``;
a few (``disks``, ``pools``) live directly under ``/api/v1/<resource>``. It handles
authentication via a Bearer token, request timeouts, pacing requests to stay under
the server's per-token rate limit, and translation of transport errors into
integration-specific exceptions.

For more information on creating API clients:
https://developers.home-assistant.io/docs/api_lib_index
"""

from __future__ import annotations

import asyncio
from http import HTTPStatus
import socket
from typing import Any
from urllib.parse import quote

import aiohttp

from custom_components.mos.const import (
    API_BASE_PATH,
    API_MAX_CONCURRENT_REQUESTS,
    API_MIN_REQUEST_INTERVAL,
    API_ROOT_PATH,
    CONTAINER_ACTION_TIMEOUT,
    DEFAULT_PORT_HTTP,
    DEFAULT_PORT_HTTPS,
    DEFAULT_TIMEOUT,
    LOGGER,
)


class MOSApiClientError(Exception):
    """Base exception to indicate a general API error."""


class MOSApiClientCommunicationError(
    MOSApiClientError,
):
    """Exception to indicate a communication error with the API."""


class MOSApiClientAuthenticationError(
    MOSApiClientError,
):
    """Exception to indicate the server rejected the API token (HTTP 401)."""


class MOSApiClientPermissionError(
    MOSApiClientError,
):
    """
    Exception to indicate the token is valid but not authorized for a resource (HTTP 403).

    Deliberately *not* a subclass of ``MOSApiClientAuthenticationError``. A 403
    means the server accepted the token and refused the resource, so prompting
    for reauthentication cannot fix it - the user would enter the same (valid)
    token, the flow would succeed, and the next poll would fail again. The
    coordinator drops the affected resource instead; see
    ``MOSDataUpdateCoordinator._async_update_data``.
    """


class MOSApiClientRateLimitError(
    MOSApiClientError,
):
    """
    Exception to indicate the server is rate limiting requests (HTTP 429).

    Kept apart from ``MOSApiClientPermissionError`` on purpose: a 429 says
    nothing about the token or its scope, it says "try again later". MOS's
    default limit is 20 requests/second per token, and a poll fires all
    resources concurrently, so a burst - or another client sharing the token -
    can briefly cross it. The coordinator therefore treats a 429 like a
    transient per-resource failure: it keeps the affected resource's
    last-known-good data and retries on the next poll, rather than tearing down
    that resource's entities. See ``MOSDataUpdateCoordinator._async_update_data``.
    """


class _RateLimiter:
    """
    Paces outgoing requests so a burst cannot trip the server's rate limit.

    An async context manager: entering waits until the request may start,
    leaving frees the in-flight slot. Two independent bounds are applied, see
    ``API_MIN_REQUEST_INTERVAL`` and ``API_MAX_CONCURRENT_REQUESTS`` for what
    each is for:

    - request *starts* are spaced by at least ``min_interval``
    - at most ``max_concurrent`` requests are in flight at any moment

    One instance per ``MOSApiClient``, which is exactly the granularity MOS
    applies its limit at (per token). Sitting in the client rather than in the
    coordinator's poll loop is deliberate: write actions and config-flow
    validation spend from the same per-token budget, and a user toggling several
    switches at once would otherwise bypass the pacing entirely.

    Attributes:
        _semaphore: Bounds how many requests are in flight at once.
        _min_interval: Minimum seconds between two request starts.
        _schedule_lock: Serializes claiming the next start slot.
        _next_start: Event-loop time at which the next request may start.

    """

    def __init__(self, max_concurrent: int, min_interval: float) -> None:
        """
        Initialize the rate limiter.

        Args:
            max_concurrent: Maximum number of requests in flight at once.
            min_interval: Minimum seconds between two request starts.

        """
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._min_interval = min_interval
        self._schedule_lock = asyncio.Lock()
        self._next_start = 0.0

    async def __aenter__(self) -> None:
        """Wait for a free in-flight slot, then for this request's turn to start."""
        await self._semaphore.acquire()
        try:
            await self._wait_for_turn()
        except BaseException:
            # Nothing was sent, so hand the slot straight back - otherwise a
            # cancelled poll would permanently shrink the pool.
            self._semaphore.release()
            raise

    async def __aexit__(self, *_exc_info: object) -> None:
        """Release the in-flight slot, whether the request succeeded or not."""
        self._semaphore.release()

    async def _wait_for_turn(self) -> None:
        """
        Claim the next start slot and sleep until it comes round.

        The slot is claimed under the lock so concurrent callers queue up
        deterministically, but the waiting itself happens outside it - holding
        the lock while sleeping would serialize the sleeps on top of each other
        instead of letting them all count down against the same schedule.
        """
        async with self._schedule_lock:
            now = asyncio.get_running_loop().time()
            start_at = max(now, self._next_start)
            self._next_start = start_at + self._min_interval
            delay = start_at - now
        if delay > 0:
            await asyncio.sleep(delay)


def _quote_segment(value: str) -> str:
    """
    Percent-encode a value so it can only ever be a single URL path segment.

    Container and VM names are interpolated into request paths. They come from
    the MOS API rather than from user input, and Docker and LXC both restrict
    names to characters that are harmless here - but nothing in this client
    enforces that, and the consequence of the assumption not holding is not a
    malformed URL, it is a request to a *different endpoint* carrying the
    Bearer token.

    yarl (which aiohttp parses the URL with) resolves ``..`` segments and starts
    a query string at ``?`` while parsing, so an unescaped name decides where
    the request goes::

        "../../auth/admin-tokens/me" -> /api/v1/auth/admin-tokens/me/start
        "x?all=true"                 -> /api/v1/docker/containers/x?all=true/start

    Encoding the segment removes that coupling: whatever the name contains, it
    stays one segment.

    Args:
        value: The raw path segment (a container or VM name).

    Returns:
        The segment with every reserved character percent-encoded.

    """
    return quote(value, safe="")


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """
    Verify that the API response is valid.

    Raises appropriate exceptions for authentication and HTTP errors.

    Args:
        response: The aiohttp ClientResponse to verify.

    Raises:
        MOSApiClientAuthenticationError: For 401 (token rejected).
        MOSApiClientPermissionError: For 403 (token accepted, resource denied).
        MOSApiClientRateLimitError: For 429 (rate limited, retry later).
        aiohttp.ClientResponseError: For other HTTP errors.

    """
    if response.status == HTTPStatus.UNAUTHORIZED:
        msg = "Invalid API token"
        raise MOSApiClientAuthenticationError(
            msg,
        )
    if response.status == HTTPStatus.FORBIDDEN:
        msg = f"API token is not authorized for {response.url.path}"
        raise MOSApiClientPermissionError(
            msg,
        )
    if response.status == HTTPStatus.TOO_MANY_REQUESTS:
        msg = f"Rate limited on {response.url.path}"
        raise MOSApiClientRateLimitError(
            msg,
        )
    response.raise_for_status()


class MOSApiClient:
    """
    API client for the local MOS REST API.

    The client is mostly read-only, with one write action (starting/stopping
    an LXC container). It talks to ``<scheme>://<host>:<port>/api/v1/mos/<resource>``
    (``osinfo``, ``services``) and ``<scheme>://<host>:<port>/api/v1/<resource>``
    (``disks``, ``pools``). Every request carries the configured Bearer token
    in the ``Authorization`` header.

    TLS certificate verification is not handled here: it is controlled by the
    aiohttp session that is passed in (Home Assistant provides a verifying or a
    non-verifying shared session depending on the ``verify_ssl`` option).

    Every request - read, write, or config-flow validation - is paced through a
    per-client rate limiter so a poll cannot exhaust the server's per-token
    budget; see ``_RateLimiter``.

    Attributes:
        _token: The API token used for Bearer authentication.
        _session: The aiohttp ClientSession for making requests.
        _base_url: The fully qualified base URL for ``/api/v1/mos`` resources.
        _root_base_url: The fully qualified base URL for ``/api/v1`` resources.
        _rate_limiter: Paces requests to stay under the server's rate limit.

    """

    def __init__(
        self,
        host: str,
        token: str,
        session: aiohttp.ClientSession,
        *,
        use_ssl: bool = False,
        port: int | None = None,
    ) -> None:
        """
        Initialize the API client.

        Args:
            host: The MOS host name or IP address.
            token: The API token for Bearer authentication.
            session: The aiohttp ClientSession to use for requests.
            use_ssl: Whether to use HTTPS instead of HTTP.
            port: Optional TCP port. Defaults to 443 (SSL) or 80 (plain).

        """
        self._token = token
        self._session = session
        self._rate_limiter = _RateLimiter(
            max_concurrent=API_MAX_CONCURRENT_REQUESTS,
            min_interval=API_MIN_REQUEST_INTERVAL,
        )

        scheme = "https" if use_ssl else "http"
        port = int(port) if port is not None else (DEFAULT_PORT_HTTPS if use_ssl else DEFAULT_PORT_HTTP)
        root_url = f"{scheme}://{host}:{port}"
        self._base_url = f"{root_url}{API_BASE_PATH}"
        self._root_base_url = f"{root_url}{API_ROOT_PATH}"

    async def async_get_osinfo(self) -> dict[str, Any]:
        """
        Get operating system / hardware information from ``/osinfo``.

        Returns:
            The parsed ``osinfo`` payload.

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        return await self._get("osinfo")

    async def async_get_services(self) -> dict[str, Any]:
        """
        Get enabled/running status of system services from ``/services``.

        Returns:
            The parsed ``services`` payload.

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        return await self._get("services")

    async def async_get_disks(self) -> list[dict[str, Any]]:
        """
        Get physical disk information from ``/disks``.

        Requests ``performance=true`` for I/O throughput figures and
        ``skipStandby=true`` so spun-down disks aren't woken just to be polled.

        Returns:
            The parsed ``disks`` payload.

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        return await self._get("disks?performance=true&skipStandby=true", base_url=self._root_base_url)

    async def async_get_pools(self) -> list[dict[str, Any]]:
        """
        Get storage pool information from ``/pools``.

        Requests ``includeMetrics=true`` for the pool usage/performance figures.

        Returns:
            The parsed ``pools`` payload.

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        return await self._get("pools?includeMetrics=true", base_url=self._root_base_url)

    async def async_get_system_load(self) -> dict[str, Any]:
        """
        Get live system health telemetry from ``/system/load``.

        Despite its name the payload covers more than CPU load: it also
        includes memory, swap, network and temperature figures, all sampled
        at request time. This is a live snapshot, unlike the mostly static
        ``osinfo`` payload.

        Returns:
            The parsed ``system/load`` payload.

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        return await self._get("system/load", base_url=self._root_base_url)

    async def async_get_sensors(self) -> dict[str, list[dict[str, Any]]]:
        """
        Get hardware sensor readings from ``/sensors``.

        Returns:
            The parsed ``sensors`` payload: a dict keyed by category (``fan``,
            ``temperature``, ``power``, ``voltage``, ``psu``, ``other``), each a
            list of individual readings.

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        return await self._get("sensors")

    async def async_get_lxc_containers(self) -> list[dict[str, Any]]:
        """
        Get LXC container status and resource usage from ``/lxc/containers/usage``.

        This endpoint is used instead of the plainer ``/lxc/containers`` because
        it is a strict superset: it includes the same name/state/autostart/network
        fields plus live CPU and memory usage, in a single call.

        Returns:
            The parsed ``lxc/containers/usage`` payload.

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        return await self._get("lxc/containers/usage", base_url=self._root_base_url)

    async def async_start_lxc_container(self, name: str) -> dict[str, Any]:
        """
        Start a single LXC container via ``POST /lxc/containers/{name}/start``.

        This is a write action (unlike every other method on this client): it
        actually starts the container on the MOS server, not just reads state.

        Returns:
            The parsed ``OperationResult`` payload (``{"success", "message"}``).

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        return await self._post(
            f"lxc/containers/{_quote_segment(name)}/start",
            base_url=self._root_base_url,
            timeout=CONTAINER_ACTION_TIMEOUT,
        )

    async def async_stop_lxc_container(self, name: str) -> dict[str, Any]:
        """
        Stop a single LXC container via ``POST /lxc/containers/{name}/stop``.

        Returns:
            The parsed ``OperationResult`` payload (``{"success", "message"}``).

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        return await self._post(
            f"lxc/containers/{_quote_segment(name)}/stop",
            base_url=self._root_base_url,
            timeout=CONTAINER_ACTION_TIMEOUT,
        )

    async def async_get_docker_containers(self) -> list[dict[str, Any]]:
        """
        Get Docker container update status from ``/docker/mos/containers``.

        Despite the OpenAPI summary calling these "images", the payload is
        keyed by container (``name``, ``autostart``) and includes the
        installed vs. available image version/digest for update tracking.

        Returns:
            The parsed ``docker/mos/containers`` payload.

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        return await self._get("docker/mos/containers", base_url=self._root_base_url)

    async def async_get_docker_engine_containers(self) -> list[dict[str, Any]]:
        """
        Get the live container list, including running state, via the raw Docker Engine proxy.

        Unlike ``/docker/mos/containers`` (image/update-tracking metadata
        only - no running state), ``GET /docker/containers/json`` is proxied
        straight through to the Docker Engine API (a deliberate MOS design
        choice - Docker requests are passed through directly, unlike LXC
        which has purpose-built MOS endpoints). Used to merge a ``state``
        field into the ``docker_containers`` payload for the power switch.

        Returns:
            The raw Docker Engine container list (``Id``, ``Names``,
            ``State``, ...).

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        return await self._get("docker/containers/json?all=true", base_url=self._root_base_url)

    async def async_start_docker_container(self, name: str) -> None:
        """
        Start a single Docker container via the raw Docker Engine proxy.

        Calls ``POST /docker/containers/{name}/start``, proxied straight
        through to Docker's own ``POST /containers/{id}/start`` (accepts a
        container name, not just an ID). Docker returns 204 No Content on
        success, unlike the LXC endpoints' JSON ``OperationResult`` body.

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        await self._post(
            f"docker/containers/{_quote_segment(name)}/start",
            base_url=self._root_base_url,
            timeout=CONTAINER_ACTION_TIMEOUT,
        )

    async def async_stop_docker_container(self, name: str) -> None:
        """
        Stop a single Docker container via the raw Docker Engine proxy.

        Calls ``POST /docker/containers/{name}/stop`` (see
        ``async_start_docker_container`` for details).

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        await self._post(
            f"docker/containers/{_quote_segment(name)}/stop",
            base_url=self._root_base_url,
            timeout=CONTAINER_ACTION_TIMEOUT,
        )

    async def async_get_vm_machines(self) -> list[dict[str, Any]]:
        """
        Get VM status and resource usage from ``/vm/machines/usage``.

        Like ``/lxc/containers/usage``, this is used instead of the plainer
        ``/vm/machines`` because it is a strict superset: it includes the
        same name/state/autostart fields plus live CPU and memory usage, in
        a single call.

        Returns:
            The parsed ``vm/machines/usage`` payload.

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        return await self._get("vm/machines/usage", base_url=self._root_base_url)

    async def async_start_vm_machine(self, name: str) -> dict[str, Any]:
        """
        Start a single VM via ``POST /vm/machines/{name}/start``.

        Returns:
            The parsed ``OperationResult`` payload (``{"success", "message"}``).

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        return await self._post(f"vm/machines/{_quote_segment(name)}/start", base_url=self._root_base_url)

    async def async_stop_vm_machine(self, name: str) -> dict[str, Any]:
        """
        Stop a single VM via ``POST /vm/machines/{name}/stop``.

        Returns:
            The parsed ``OperationResult`` payload (``{"success", "message"}``).

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        return await self._post(f"vm/machines/{_quote_segment(name)}/stop", base_url=self._root_base_url)

    async def async_get_token_permissions(self) -> dict[str, Any]:
        """
        Introspect the permission scope of the token used for authentication.

        Calls ``GET /auth/admin-tokens/me``, which is reachable regardless of
        the token's own scope (unlike other ``/auth`` resources, which are
        blocked for readonly tokens). Only available on MOS versions that
        support token permission scoping; older servers respond with a 404,
        which surfaces as ``MOSApiClientCommunicationError`` like any other
        failed request.

        Returns:
            A payload of the shape ``{"id", "name", "role", "isBootToken",
            "permissions": {"mode": "full" | "readonly" | "custom",
            "resources": {...}}}``.

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        return await self._get("auth/admin-tokens/me", base_url=self._root_base_url)

    async def _get(self, resource: str, *, base_url: str | None = None) -> Any:
        """
        Perform an authenticated GET on a MOS API resource.

        Args:
            resource: The resource path relative to the API base (e.g. ``osinfo``).
            base_url: Optional base URL override. Defaults to the ``/api/v1/mos``
                base used by ``osinfo``/``services``; pass ``self._root_base_url``
                for resources living directly under ``/api/v1`` (e.g. ``disks``,
                ``pools``).

        Returns:
            The parsed JSON response.

        """
        return await self._api_wrapper(method="get", resource=resource, base_url=base_url)

    async def _post(
        self,
        resource: str,
        *,
        base_url: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Any:
        """
        Perform an authenticated POST on a MOS API resource (a write action).

        Args:
            resource: The resource path relative to the API base.
            base_url: Optional base URL override (see ``_get``).
            timeout: Request timeout in seconds. Defaults to ``DEFAULT_TIMEOUT``;
                pass a longer value for actions proxied to something with its own
                grace period (e.g. Docker's stop/start).

        Returns:
            The parsed JSON response.

        """
        return await self._api_wrapper(method="post", resource=resource, base_url=base_url, timeout=timeout)

    async def _api_wrapper(
        self,
        method: str,
        resource: str,
        *,
        data: dict | None = None,
        headers: dict | None = None,
        base_url: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Any:
        """
        Wrapper for API requests with pacing and error handling.

        This method handles all HTTP requests and translates exceptions
        into integration-specific exceptions. Every request passes through
        ``_rate_limiter`` first, so nothing reaches the server unpaced.

        Args:
            method: The HTTP method (get, post, patch, etc.).
            resource: The resource path relative to the API base URL.
            data: Optional data to send in the request body.
            headers: Optional additional headers to include in the request.
            base_url: Optional base URL override (see ``_get``).
            timeout: Request timeout in seconds.

        Returns:
            The JSON response from the API.

        Raises:
            MOSApiClientAuthenticationError: If authentication fails.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        request_headers = {"Authorization": f"Bearer {self._token}"}
        if headers:
            request_headers.update(headers)

        try:
            # The rate limiter is entered *outside* the timeout so that waiting
            # for a turn never counts against the request's own budget: a queued
            # request would otherwise report a spurious timeout without a single
            # byte having been sent.
            async with self._rate_limiter, asyncio.timeout(timeout):
                response = await self._session.request(
                    method=method,
                    url=f"{base_url or self._base_url}/{resource}",
                    headers=request_headers,
                    json=data,
                )
                _verify_response_or_raise(response)
                if response.status == 204 or not await response.read():
                    # The raw Docker Engine proxy returns 204 No Content on
                    # successful start/stop, unlike every JSON-bodied MOS
                    # endpoint.
                    return None
                return await response.json()

        except (
            MOSApiClientAuthenticationError,
            MOSApiClientPermissionError,
            MOSApiClientRateLimitError,
        ):
            # These are already the precise exception for this response; let them
            # past the catch-all below instead of being flattened into a generic
            # MOSApiClientError.
            raise
        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise MOSApiClientCommunicationError(
                msg,
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise MOSApiClientCommunicationError(
                msg,
            ) from exception
        except Exception as exception:
            # Anything reaching this branch is not a recognized HTTP/transport
            # failure - i.e. a bug rather than a server hiccup - so the traceback
            # is logged here, where the except block still has it. Every caller
            # further up only sees the resulting MOSApiClientError, which loses
            # the stack trace on `str(exception)` alone.
            LOGGER.exception("Unexpected error performing %s on %s", method, resource)
            msg = f"Something really wrong happened! - {exception}"
            raise MOSApiClientError(
                msg,
            ) from exception
