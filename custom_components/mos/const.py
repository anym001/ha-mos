"""Constants for mos."""

from datetime import timedelta
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

# Integration metadata
DOMAIN = "mos"
ATTRIBUTION = "Data provided by the local MOS API"

# API
API_BASE_PATH = "/api/v1/mos"
API_ROOT_PATH = "/api/v1"
CONF_API_TOKEN = "api_token"
DEFAULT_TIMEOUT = 10
# Docker/LXC start/stop is proxied synchronously through to the container
# runtime, which itself waits up to ~10s (SIGTERM grace period) before killing
# the container. That's right at the edge of DEFAULT_TIMEOUT, so containers
# that take a few seconds to shut down can trip our own timeout even though
# the stop succeeds a moment later.
CONTAINER_ACTION_TIMEOUT = 30

# Connection defaults
DEFAULT_SSL = False
DEFAULT_VERIFY_SSL = True
DEFAULT_PORT_HTTP = 80
DEFAULT_PORT_HTTPS = 443

# Platform parallel updates - applied to all platforms
PARALLEL_UPDATES = 1

# Polling (seconds)
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 3600

# How long authentication may be rejected *continuously* before the coordinator
# escalates to a reauth flow (ConfigEntryAuthFailed). A server that is rebooting
# or shutting down often returns a transient 401/403 while its auth service (or a
# reverse proxy in front of it) is not ready yet, even though the configured
# token is still perfectly valid. Escalating on the first such failure wrongly
# tears the user into a reauth/reconfigure prompt.
#
# This is a *duration*, deliberately not a count of poll cycles: a count would be
# coupled to the scan interval (3 failures at the 30 s default is only 90 s - far
# too short for a real reboot), whereas a grace period behaves the same whether
# the user polls every 30 s or every 10 min. A genuinely expired/revoked token
# keeps failing past the grace period and still triggers reauth; a momentarily
# unavailable server recovers (or drops to a connection error, which resets the
# timer) well before it elapses. Until then the failure is surfaced as a
# retryable UpdateFailed, so entities go "unavailable" and the token is untouched.
#
# This applies to the *running* integration only. During initial setup a rejected
# token is escalated to reauth immediately (the config flow just validated it).
#
# Five minutes comfortably covers a typical server reboot while keeping the
# reauth prompt reasonably prompt for a token that is genuinely gone.
AUTH_FAILURE_GRACE_PERIOD = timedelta(minutes=5)

# Optional resource categories - can be disabled via the options flow
CONF_ENABLE_DISKS = "enable_disks"
CONF_ENABLE_POOLS = "enable_pools"
CONF_ENABLE_SERVICES = "enable_services"
CONF_ENABLE_LXC = "enable_lxc"
CONF_ENABLE_DOCKER = "enable_docker"
CONF_ENABLE_VM = "enable_vm"
DEFAULT_ENABLE_DISKS = True
DEFAULT_ENABLE_POOLS = True
DEFAULT_ENABLE_SERVICES = True
DEFAULT_ENABLE_LXC = True
DEFAULT_ENABLE_DOCKER = True
DEFAULT_ENABLE_VM = True
