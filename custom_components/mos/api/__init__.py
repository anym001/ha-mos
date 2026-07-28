"""
API package for mos.

Architecture:
    Three-layer data flow: Entities → Coordinator → API Client.
    Only the coordinator should call the API client. Entities must never
    import or call the API client directly.

Exception hierarchy:
    MOSApiClientError (base)
    ├── MOSApiClientCommunicationError (network/timeout)
    └── MOSApiClientAuthenticationError (401/403)

Coordinator exception mapping:
    ApiClientAuthenticationError → UpdateFailed (auto-retry, ConfigEntryNotReady
        during setup) while transient, escalating to ConfigEntryAuthFailed
        (reauth) only after auth has been rejected continuously for
        AUTH_FAILURE_GRACE_PERIOD, so a rebooting/unreachable server that briefly
        returns 401/403 does not throw away a still-valid token (the grace period
        is a duration, not a poll-cycle count, so it does not shrink when the scan
        interval is short, and it is kept per config entry so setup retries do
        not restart it).
    ApiClientCommunicationError → UpdateFailed (auto-retry)
    ApiClientError             → UpdateFailed (auto-retry)
"""

from .client import MOSApiClient, MOSApiClientAuthenticationError, MOSApiClientCommunicationError, MOSApiClientError

__all__ = [
    "MOSApiClient",
    "MOSApiClientAuthenticationError",
    "MOSApiClientCommunicationError",
    "MOSApiClientError",
]
