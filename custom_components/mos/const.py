"""Constants for mos."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

# Integration metadata
DOMAIN = "mos"
ATTRIBUTION = "Data provided by the local MOS API"

# API
API_BASE_PATH = "/api/v1/mos"
CONF_API_TOKEN = "api_token"
DEFAULT_TIMEOUT = 10

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
