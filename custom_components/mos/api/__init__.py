"""
API package for mos.

Architecture:
    Three-layer data flow: Entities → Coordinator → API Client.
    Only the coordinator should call the API client. Entities must never
    import or call the API client directly.

Exception hierarchy:
    MOSApiClientError (base)
    ├── MOSApiClientCommunicationError (network/timeout)
    ├── MOSApiClientAuthenticationError (401 - token rejected)
    └── MOSApiClientPermissionError (403 - token valid, resource denied)

    401 and 403 are kept apart on purpose. Only 401 says anything about the
    token itself; 403 says the token is fine but its scope does not cover that
    resource, which no amount of reauthenticating can fix.

Coordinator exception mapping:
    ApiClientAuthenticationError → UpdateFailed (auto-retry, ConfigEntryNotReady
        during setup) while transient, escalating to ConfigEntryAuthFailed
        (reauth) only after auth has been rejected for AUTH_FAILURE_GRACE_PERIOD
        *and* AUTH_FAILURE_MIN_FAILURES consecutive polls, so a rebooting or
        unreachable server that briefly returns 401 does not throw away a
        still-valid token. The grace period is a duration rather than a poll
        count so it does not shrink at a short scan interval; the minimum
        failure count is the other half of that, so it does not collapse to two
        polls at a long one. It is kept per config entry so setup retries do not
        restart it.
    ApiClientPermissionError   → the affected resource is dropped for the rest of
        the coordinator's lifetime and the remaining resources keep updating.
        Never escalates to reauth. If an always-fetched resource (osinfo,
        system_load) is denied, UpdateFailed instead - the integration cannot
        work without those.
    ApiClientCommunicationError → UpdateFailed (auto-retry)
    ApiClientError             → UpdateFailed (auto-retry)
"""

from .client import (
    MOSApiClient,
    MOSApiClientAuthenticationError,
    MOSApiClientCommunicationError,
    MOSApiClientError,
    MOSApiClientPermissionError,
)

__all__ = [
    "MOSApiClient",
    "MOSApiClientAuthenticationError",
    "MOSApiClientCommunicationError",
    "MOSApiClientError",
    "MOSApiClientPermissionError",
]
