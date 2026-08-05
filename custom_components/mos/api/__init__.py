"""
API package for mos.

Architecture:
    Three-layer data flow: Entities → Coordinator → API Client.
    Only the coordinator should call the API client. Entities must never
    import or call the API client directly.

Exception hierarchy:
    MOSApiClientError (base)
    ├── MOSApiClientCommunicationError (network/timeout)
    │   └── MOSApiClientNotFoundError (404 - server has no such endpoint)
    ├── MOSApiClientAuthenticationError (401, and the 403 that rejects the token)
    ├── MOSApiClientPermissionError (the 403 that denies one resource)
    └── MOSApiClientRateLimitError (429 - rate limited, retry later)

    These are kept apart on purpose. An authentication error says the server does
    not know this token; a permission error says the token is fine but its scope
    does not cover that resource, which no amount of reauthenticating can fix;
    404 says the server simply does not have that endpoint, which is the normal
    answer from a MOS version older than the endpoint; 429 says the token and
    scope are both fine and the request should simply be retried later.

    The split does not follow the status code, because MOS's does not either: it
    answers 403 both for a token it does not know and for a resource outside a
    valid token's scope, and only the response body says which. That is decided
    in ``_raise_for_forbidden``, which is where the reasoning lives. 401 exists
    on the server only for a request carrying no credentials at all, which this
    client cannot produce.

    404 is the one that is *nested*, under the communication error: any handler
    that does not care about the distinction keeps treating it as "this resource
    is not answering", which is the safe reading everywhere it is not handled
    explicitly.

Coordinator exception mapping:
    ApiClientAuthenticationError → UpdateFailed (auto-retry, ConfigEntryNotReady
        during setup) while transient, escalating to ConfigEntryAuthFailed
        (reauth) only after auth has been rejected for AUTH_FAILURE_GRACE_PERIOD
        *and* AUTH_FAILURE_MIN_FAILURES consecutive polls, so a rebooting or
        unreachable server that briefly rejects a request does not throw away a
        still-valid token. The grace period is a duration rather than a poll
        count so it does not shrink at a short scan interval; the minimum
        failure count is the other half of that, so it does not collapse to two
        polls at a long one. It is kept per config entry so setup retries do not
        restart it.
    ApiClientPermissionError   → a permanent per-resource denial, recorded in
        ``forbidden_resources`` and not requested again (see
        ``_absorb_scope_denials``). The server named the resource, so retrying
        can only repeat the refusal; the scope has to change and the entry be
        reloaded. Its entities are kept rather than deleted - the data is carried
        forward and the resource counts as stale, so they report unavailable
        instead of losing their history. Never escalates to reauth: the token is
        valid. If an always-fetched resource (osinfo, system_load) is denied,
        UpdateFailed instead - the integration cannot work without those.
    ApiClientNotFoundError     → reported as an unsupported endpoint rather than a
        failure, for an optional resource that has never returned data: it is
        logged once, no entities are created for it, and it is re-probed on every
        poll so a server that gains the endpoint in an update is picked up without
        a reload. A 404 on a resource that *did* answer before is a regression
        rather than a missing feature, and falls back to the transient handling
        below. On an always-fetched resource (osinfo, system_load) it fails the
        cycle like any other unreachable resource - a server without those is not
        a MOS server this integration can talk to.
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
    MOSApiClientNotFoundError,
    MOSApiClientPermissionError,
    MOSApiClientRateLimitError,
)

__all__ = [
    "MOSApiClient",
    "MOSApiClientAuthenticationError",
    "MOSApiClientCommunicationError",
    "MOSApiClientError",
    "MOSApiClientNotFoundError",
    "MOSApiClientPermissionError",
    "MOSApiClientRateLimitError",
]
