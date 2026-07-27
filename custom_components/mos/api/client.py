"""
API Client for mos.

This module provides the API client for communicating with the local MOS REST API.
Most resources (``osinfo``, ``services``) live under ``/api/v1/mos/<resource>``;
a few (``disks``, ``pools``) live directly under ``/api/v1/<resource>``. It handles
authentication via a Bearer token, request timeouts, and translation of transport
errors into integration-specific exceptions.

For more information on creating API clients:
https://developers.home-assistant.io/docs/api_lib_index
"""

from __future__ import annotations

import asyncio
import socket
from typing import Any

import aiohttp

from custom_components.mos.const import (
    API_BASE_PATH,
    API_ROOT_PATH,
    DEFAULT_PORT_HTTP,
    DEFAULT_PORT_HTTPS,
    DEFAULT_TIMEOUT,
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
    """Exception to indicate an authentication error with the API."""


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """
    Verify that the API response is valid.

    Raises appropriate exceptions for authentication and HTTP errors.

    Args:
        response: The aiohttp ClientResponse to verify.

    Raises:
        MOSApiClientAuthenticationError: For 401/403 errors.
        aiohttp.ClientResponseError: For other HTTP errors.

    """
    if response.status in (401, 403):
        msg = "Invalid API token"
        raise MOSApiClientAuthenticationError(
            msg,
        )
    response.raise_for_status()


class MOSApiClient:
    """
    API client for the local MOS REST API.

    The client is read-only in this phase and talks to
    ``<scheme>://<host>:<port>/api/v1/mos/<resource>`` (``osinfo``, ``services``)
    and ``<scheme>://<host>:<port>/api/v1/<resource>`` (``disks``, ``pools``).
    Every request carries the configured Bearer token in the ``Authorization``
    header.

    TLS certificate verification is not handled here: it is controlled by the
    aiohttp session that is passed in (Home Assistant provides a verifying or a
    non-verifying shared session depending on the ``verify_ssl`` option).

    Attributes:
        _token: The API token used for Bearer authentication.
        _session: The aiohttp ClientSession for making requests.
        _base_url: The fully qualified base URL for ``/api/v1/mos`` resources.
        _root_base_url: The fully qualified base URL for ``/api/v1`` resources.

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

        Returns:
            The parsed ``disks`` payload.

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        return await self._get("disks", base_url=self._root_base_url)

    async def async_get_pools(self) -> list[dict[str, Any]]:
        """
        Get storage pool information from ``/pools``.

        Returns:
            The parsed ``pools`` payload.

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        return await self._get("pools", base_url=self._root_base_url)

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

    async def _api_wrapper(
        self,
        method: str,
        resource: str,
        data: dict | None = None,
        headers: dict | None = None,
        base_url: str | None = None,
    ) -> Any:
        """
        Wrapper for API requests with error handling.

        This method handles all HTTP requests and translates exceptions
        into integration-specific exceptions.

        Args:
            method: The HTTP method (get, post, patch, etc.).
            resource: The resource path relative to the API base URL.
            data: Optional data to send in the request body.
            headers: Optional additional headers to include in the request.
            base_url: Optional base URL override (see ``_get``).

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
            async with asyncio.timeout(DEFAULT_TIMEOUT):
                response = await self._session.request(
                    method=method,
                    url=f"{base_url or self._base_url}/{resource}",
                    headers=request_headers,
                    json=data,
                )
                _verify_response_or_raise(response)
                return await response.json()

        except MOSApiClientAuthenticationError:
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
            msg = f"Something really wrong happened! - {exception}"
            raise MOSApiClientError(
                msg,
            ) from exception
