"""
Connection validators.

Validation functions that test whether the provided MOS connection details
(host, API token, TLS settings) can reach the API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.mos.api import MOSApiClient
from homeassistant.helpers.aiohttp_client import async_create_clientsession

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def validate_connection(
    hass: HomeAssistant,
    host: str,
    token: str,
    *,
    use_ssl: bool = False,
    verify_ssl: bool = True,
    port: int | None = None,
) -> dict[str, Any]:
    """
    Validate connection details by fetching ``/osinfo``.

    Args:
        hass: Home Assistant instance.
        host: The MOS host name or IP address.
        token: The API token to validate.
        use_ssl: Whether to use HTTPS.
        verify_ssl: Whether to verify the TLS certificate.
        port: Optional TCP port.

    Returns:
        The ``osinfo`` payload (used to derive the entry title).

    Raises:
        MOSApiClientAuthenticationError: If the token is rejected.
        MOSApiClientCommunicationError: If communication fails.
        MOSApiClientError: For other API errors.

    """
    client = MOSApiClient(
        host=host,
        token=token,
        session=async_create_clientsession(hass, verify_ssl=verify_ssl),
        use_ssl=use_ssl,
        port=port,
    )
    return await client.async_get_osinfo()


__all__ = [
    "validate_connection",
]
