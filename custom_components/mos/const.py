"""Constants for mos."""

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
# Docker start/stop is proxied synchronously to the Docker Engine, which itself
# waits up to ~10s (SIGTERM grace period) before killing the container. That's
# right at the edge of DEFAULT_TIMEOUT, so containers that take a few seconds to
# shut down can trip our own timeout even though the stop succeeds a moment later.
DOCKER_ACTION_TIMEOUT = 30

# Connection defaults
DEFAULT_SSL = False
DEFAULT_VERIFY_SSL = True
DEFAULT_PORT_HTTP = 80
DEFAULT_PORT_HTTPS = 443

# Platform parallel updates - applied to all platforms
PARALLEL_UPDATES = 1

# Polling (seconds)
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 3600

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
