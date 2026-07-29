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

# Minimum gap between the *starts* of two requests, in seconds.
#
# MOS rate limits to 20 requests/second per token (answering HTTP 429 beyond
# that), and a poll fires every enabled resource concurrently - ten today, more
# as endpoints are added. Unpaced, that whole burst lands inside a single second
# and eats half the budget in one go, leaving little room for anything else
# sharing the token (a second Home Assistant, the MOS web UI, a script) or for
# the write actions a user triggers while a poll is in flight.
#
# 100 ms caps this client at 10 requests/second, so a full poll spreads over
# roughly a second and half the server's budget stays free. This is a floor on
# the gap between starts, not a fixed delay added to every request: when nothing
# is queued a request goes out immediately, so a single switch toggle is exactly
# as fast as before.
API_MIN_REQUEST_INTERVAL = 0.1

# How many requests may be in flight at once - a safety valve on top of the
# pacing, not the main mechanism.
#
# API_MIN_REQUEST_INTERVAL bounds how fast requests *start*, not how many are
# outstanding. Against a server that has become very slow but not unresponsive,
# 10 starts/second against a DEFAULT_TIMEOUT of 10 s could leave ~100 connections
# open at once. Five is comfortably above what a healthy poll ever reaches (the
# pacing spreads it thin enough that only two or three overlap), so this only
# binds once something has already gone wrong.
API_MAX_CONCURRENT_REQUESTS = 5

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
# The grace period applies to setup as well as to the running integration: a
# Home Assistant restart or an entry reload can land in exactly the same window
# where the server rejects a still-valid token, and a rejected setup that is
# retried gets a *new* coordinator instance every time. During setup the failure
# surfaces as ConfigEntryNotReady, so Home Assistant retries with backoff.
#
# Five minutes comfortably covers a typical server reboot while keeping the
# reauth prompt reasonably prompt for a token that is genuinely gone.
AUTH_FAILURE_GRACE_PERIOD = timedelta(minutes=5)

# How many consecutive polls must have been rejected before escalating, on top
# of AUTH_FAILURE_GRACE_PERIOD having elapsed.
#
# The grace period alone is only half the guard. It is checked when a poll fails,
# so at a long scan interval it collapses to almost nothing: at the 3600 s
# maximum the *second* failed poll is already an hour into the streak, meaning
# two unlucky polls - a rate limiter, a proxy hiccup, a momentary 401 - are
# enough to tear the user into a reauth prompt. Requiring a minimum number of
# failures as well makes the guard "sustained *and* repeatedly observed",
# which behaves sensibly across the whole 30 s - 3600 s range:
#
#     30 s interval  -> grace period binds:   11 failures over 5 min
#     600 s interval -> failure count binds:   3 failures over 20 min
#
# Three is enough that a single flaky window cannot trip it, while a genuinely
# revoked token still surfaces within a few poll cycles.
AUTH_FAILURE_MIN_FAILURES = 3

# ``hass.data`` key holding the auth-failure streak per config entry. It cannot
# live on the coordinator: a failing setup is retried with a fresh coordinator,
# which would restart the grace period on every retry and never escalate.
AUTH_FAILURE_STORE = f"{DOMAIN}_auth_failure"

# How long an optional resource may fail *continuously* before its entities stop
# claiming to be available and go "unavailable" instead.
#
# A transient 403/429/communication error on an optional resource keeps its
# last-known-good data (see ``_retain_last_known_good``), which is exactly right
# for a passing hiccup: entities keep their values instead of being torn down
# over a momentary blip. But the retention has no natural end. Left uncapped, an
# endpoint that is gone for good - removed from the MOS API, permanently broken,
# a container runtime that never comes back - would serve the same frozen values
# forever, and the user has no way to tell a live reading from a stale one. A
# temperature that stopped updating three days ago still looks like a
# measurement, and automations keep acting on it.
#
# Past this threshold the data is kept but no longer presented as current: the
# entities report ``available = False``. Deliberately *not* dropped - removing
# them would delete their registry entries along with the recorder history,
# custom names and icons, and break every automation referencing the entity_id
# (see ``_async_remove_entities``). "Unavailable" is recoverable and honest;
# removal is neither.
#
# Fifteen minutes is long enough that no realistic transient - a server reboot,
# a container runtime restart, a burst of rate limiting - reaches it, and short
# enough that a genuinely dead endpoint is visible well within an hour.
RESOURCE_STALE_GRACE_PERIOD = timedelta(minutes=15)

# How many consecutive polls must have failed before a resource counts as stale,
# on top of RESOURCE_STALE_GRACE_PERIOD having elapsed.
#
# Same two-part guard as AUTH_FAILURE_*, and for the same reason: at a 3600 s
# interval the duration alone would collapse to "two unlucky polls in a row",
# while a count alone would mean 90 s at the 30 s default - far too eager.
#
# Which half binds flips at a 450 s interval:
#
#     30 s interval   -> grace period binds: stale after 15 min (30 polls)
#     300 s interval  -> grace period binds: stale after 15 min (4 polls)
#     3600 s interval -> failure count binds: stale after 2 h (3 polls)
#
# That the threshold stretches at long intervals is intended, not a side effect.
# Someone polling hourly never has data fresher than an hour, so "stale" has to
# be defined more generously for them; holding them to a flat 15 minutes would
# mean two unlucky polls could take a resource down.
#
# The count also guards against a case the duration cannot see. During a
# server-wide outage the poll fails before per-resource classification is
# reached, so the elapsed timer keeps running while nothing is being observed.
# Requiring failures to have been *counted* means an outage cannot age a
# resource into staleness behind the coordinator's back; the streak has to be
# re-observed after the server is answering again.
RESOURCE_STALE_MIN_FAILURES = 3

# Resources fetched on every poll regardless of the options flow. A failure on one
# of these - denied (403), rate limited (429) or unreachable - is fatal for the
# update, since there is nothing meaningful left to show, so it surfaces as
# UpdateFailed rather than silently dropping the resource. Every other resource
# only fails for itself and keeps its last-known-good data.
ALWAYS_FETCHED_RESOURCES = frozenset({"osinfo", "system_load"})

# Maps a coordinator data key to the resource name MOS uses in a token's
# permission scope (``GET /auth/admin-tokens/me`` → ``permissions.resources``),
# so a scoped token's read restrictions can be honoured before the first poll
# rather than being discovered through a 403.
#
# Only "lxc", "docker" and "vm" are confirmed against the MOS API; the rest are
# best-effort. That is safe because ``has_read_access`` only treats an *explicit*
# ``"none"`` as denied - a name MOS spells differently simply won't match, and
# the resource is probed normally and dropped on a 403 like before.
READ_PERMISSION_RESOURCES = {
    "services": "services",
    "disks": "disks",
    "pools": "pools",
    "lxc_containers": "lxc",
    "docker_containers": "docker",
    "docker_engine_containers": "docker",
    "vm_machines": "vm",
    # Sensors have no permission scope of their own - they are covered by the
    # general "mos" scope.
    "sensors": "mos",
}

# Optional resource categories - can be disabled via the options flow
CONF_ENABLE_DISKS = "enable_disks"
CONF_ENABLE_POOLS = "enable_pools"
CONF_ENABLE_SERVICES = "enable_services"
CONF_ENABLE_LXC = "enable_lxc"
CONF_ENABLE_DOCKER = "enable_docker"
CONF_ENABLE_VM = "enable_vm"
CONF_ENABLE_SENSORS = "enable_sensors"
DEFAULT_ENABLE_DISKS = True
DEFAULT_ENABLE_POOLS = True
DEFAULT_ENABLE_SERVICES = True
DEFAULT_ENABLE_LXC = True
DEFAULT_ENABLE_DOCKER = True
DEFAULT_ENABLE_VM = True
DEFAULT_ENABLE_SENSORS = True
