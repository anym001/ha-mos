"""
API Client for mos.

This module provides the API client for communicating with the local MOS REST API
(``/api/v1/mos/<resource>``). It handles authentication via a Bearer token, request
timeouts, and translation of transport errors into integration-specific exceptions.

For more information on creating API clients:
https://developers.home-assistant.io/docs/api_lib_index
"""

from __future__ import annotations

import asyncio
import socket
from typing import Any

import aiohttp

from custom_components.mos.const import API_BASE_PATH, DEFAULT_PORT_HTTP, DEFAULT_PORT_HTTPS, DEFAULT_TIMEOUT


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
    ``<scheme>://<host>:<port>/api/v1/mos/<resource>``. Every request carries the
    configured Bearer token in the ``Authorization`` header.

    TLS certificate verification is not handled here: it is controlled by the
    aiohttp session that is passed in (Home Assistant provides a verifying or a
    non-verifying shared session depending on the ``verify_ssl`` option).

    Attributes:
        _token: The API token used for Bearer authentication.
        _session: The aiohttp ClientSession for making requests.
        _base_url: The fully qualified base URL for all MOS API resources.

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
        if port is None:
            port = DEFAULT_PORT_HTTPS if use_ssl else DEFAULT_PORT_HTTP
        self._base_url = f"{scheme}://{host}:{port}{API_BASE_PATH}"

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

    async def _get(self, resource: str) -> Any:
        """
        Perform an authenticated GET on a MOS API resource.

        Args:
            resource: The resource path relative to the API base (e.g. ``osinfo``).

        Returns:
            The parsed JSON response.

        """
        return await self._api_wrapper(method="get", resource=resource)

    async def _api_wrapper(
        self,
        method: str,
        resource: str,
        data: dict | None = None,
        headers: dict | None = None,
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
                    url=f"{self._base_url}/{resource}",
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
