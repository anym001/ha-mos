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
    ├── MOSApiClientPermissionError (403 - token valid, resource denied)
    └── MOSApiClientRateLimitError (429 - rate limited, retry later)

    401, 403 and 429 are kept apart on purpose. Only 401 says anything about the
    token itself; 403 says the token is fine but its scope does not cover that
    resource, which no amount of reauthenticating can fix; 429 says the token
    and scope are both fine and the request should simply be retried later.

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
    ApiClientPermissionError   → treated as a *transient* per-resource failure:
        the resource keeps its last-known-good data and is re-probed on the next
        poll, so a spurious 403 (e.g. the MOS server reloading) never tears down
        that resource's entities until a reload. Scope restrictions the token
        genuinely lacks are handled ahead of the first poll from the token's
        permission scope (see ``_seed_forbidden_resources``), so a 403 that still
        reaches here is by construction not an explicit denial. Never escalates
        to reauth. If an always-fetched resource (osinfo, system_load) is denied,
        UpdateFailed instead - the integration cannot work without those.
    ApiClientRateLimitError    → same transient per-resource handling as a 403:
        keep last-known-good data, retry next poll. An always-fetched resource
        being rate limited fails the cycle (UpdateFailed, auto-retry).
    ApiClientCommunicationError → UpdateFailed (auto-retry)
    ApiClientError             → UpdateFailed (auto-retry)
"""

from .client import (
    MOSApiClient,
    MOSApiClientAuthenticationError,
    MOSApiClientCommunicationError,
    MOSApiClientError,
    MOSApiClientPermissionError,
    MOSApiClientRateLimitError,
)

__all__ = [
    "MOSApiClient",
    "MOSApiClientAuthenticationError",
    "MOSApiClientCommunicationError",
    "MOSApiClientError",
    "MOSApiClientPermissionError",
    "MOSApiClientRateLimitError",
]
