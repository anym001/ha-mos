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
    ApiClientAuthenticationError → ConfigEntryAuthFailed (triggers reauth)
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
