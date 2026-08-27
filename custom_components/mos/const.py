"""Constants for mos."""

from datetime import timedelta
from enum import StrEnum
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

# Integration metadata
DOMAIN = "mos"
ATTRIBUTION = "Data provided by the local MOS API"


class MOSDeviceKind(StrEnum):
    """
    What kind of thing a container device represents.

    Written to the device's ``model_id``, which is the one field on a device
    that is machine-readable by contract: ``model`` is a display string, the
    name is the user's, and ``identifiers`` carry an internal format nothing
    outside this integration should be parsing. A dashboard card that wants
    "every Docker container on this server" filters the device registry on
    ``model_id`` and stays correct through renames, translations and any later
    change to how identifiers are built.

    The values are part of that contract - changing one breaks every card and
    template already matching on it, so treat them as fixed once released.
    """

    DOCKER = "docker_container"
    COMPOSE = "compose_stack"
    LXC = "lxc_container"
    VM = "virtual_machine"
    DISK = "disk"
    POOL = "storage_pool"
    UPS = "ups"


# The human-readable ``model`` shown on the device page, for the kinds that have
# no hardware model of their own.
#
# Deliberately incomplete: a disk and a UPS are real hardware, and ``model`` is
# where their actual model belongs ("Samsung SSD 970", "ACMT1000E") rather than
# a restatement of what kind of thing they are. The UPS fills it from its NUT
# driver already (``MOSDeviceHardware``), and leaves it blank when the driver
# reports nothing - a blank field reads as "not reported", which a generic
# "UPS" would quietly destroy. Everything listed here is something MOS itself
# provides, where there is no other model to state.
#
# Not translatable: ``DeviceInfo`` can translate a device's name but not its
# model, which matches how Home Assistant treats models everywhere else.
DEVICE_KIND_MODEL_NAMES: dict[MOSDeviceKind, str] = {
    MOSDeviceKind.DOCKER: "Docker Container",
    MOSDeviceKind.COMPOSE: "Compose Stack",
    MOSDeviceKind.LXC: "LXC Container",
    MOSDeviceKind.VM: "Virtual Machine",
    MOSDeviceKind.POOL: "Storage Pool",
}

# API
API_BASE_PATH = "/api/v1/mos"
API_ROOT_PATH = "/api/v1"
CONF_API_TOKEN = "api_token"  # noqa: S105 - the config entry key, not a credential
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
# or shutting down often rejects a request while its auth service (or a
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
# A transient 429/communication error on an optional resource keeps its
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

# Every resource name a MOS token's permission scope can carry
# (``GET /auth/admin-tokens/me`` → ``permissions.resources``), as returned by a
# custom-mode token on MOS 0.5.x. Kept as the authoritative list so a mapping
# below cannot silently name a resource MOS does not have - the failure mode is
# invisible, since an unknown name never matches and therefore never denies.
MOS_PERMISSION_RESOURCES = frozenset(
    {
        "auth",
        "disks",
        "pools",
        "iscsi",
        "docker",
        "lxc",
        "vm",
        "users",
        "shares",
        "cron",
        "system",
        "mos",
        "terminal",
        # Added alongside /nut/status; only a custom-mode token lists it, same as
        # every other name here (full/readonly carry no resources block at all).
        "nut",
    }
)

# Maps a coordinator data key to the resource name MOS uses in a token's
# permission scope. Two jobs: honouring a scoped token's read restrictions before
# the first poll, and naming the right thing when telling a user what to grant -
# the data keys below are internal, only the values appear in the MOS web UI.
#
# The scope is the *first* path segment - not the data key, and not a later
# segment that happens to look like a resource name. /api/v1/mos/services and
# /api/v1/mos/sensors are governed by "mos", while /api/v1/docker/mos/containers
# is governed by "docker" despite the "mos" in the middle of it: a token with
# mos denied still reads it. Verified against MOS 0.5.x with tokens setting
# "mos", "system" and "auth" to "none" one at a time.
PERMISSION_RESOURCE_BY_KEY = {
    "osinfo": "mos",
    "system_load": "system",
    "services": "mos",
    "sensors": "mos",
    "disks": "disks",
    "pools": "pools",
    "lxc_containers": "lxc",
    "docker_containers": "docker",
    "docker_engine_containers": "docker",
    "compose_stacks": "docker",
    "docker_groups": "docker",
    "vm_machines": "vm",
    "nut": "nut",
}

# The subset whose entities may be dropped when the scope denies them, which is
# every mapped resource except the always-fetched ones: a denial there is fatal
# for the whole poll (see ALWAYS_FETCHED_RESOURCES), so there is nothing to skip.
# Derived rather than spelled out so the two cannot drift apart.
READ_PERMISSION_RESOURCES = {
    key: resource for key, resource in PERMISSION_RESOURCE_BY_KEY.items() if key not in ALWAYS_FETCHED_RESOURCES
}

# The Docker container label MOS stores a configured web interface under, and the
# OCI image labels worth surfacing, mapped to the attribute name each gets.
#
# Named here rather than at their point of use because the coordinator keeps only
# these labels and drops the rest (see ``_merge_docker_engine_state``). Docker
# labels are free-form - anything the image author or the user put there rides
# along, and coordinator data ends up in the diagnostics download that people
# attach to public issues. Keeping the allow-list in one place means a new label
# cannot be read by an entity while the merge silently withholds it.
DOCKER_WEB_UI_LABEL = "mos.webui"
DOCKER_IMAGE_LABEL_ATTRIBUTES = {
    "org.opencontainers.image.title": "image_title",
    "org.opencontainers.image.description": "image_description",
    "org.opencontainers.image.source": "image_source",
}
DOCKER_LABELS_KEPT = frozenset({DOCKER_WEB_UI_LABEL, *DOCKER_IMAGE_LABEL_ATTRIBUTES})

# Optional resource categories - can be disabled via the options flow
CONF_ENABLE_DISKS = "enable_disks"
CONF_ENABLE_POOLS = "enable_pools"
CONF_ENABLE_SERVICES = "enable_services"
CONF_ENABLE_LXC = "enable_lxc"
CONF_ENABLE_DOCKER = "enable_docker"
CONF_ENABLE_DOCKER_STATS = "enable_docker_stats"
CONF_ENABLE_COMPOSE = "enable_compose"
CONF_ENABLE_VM = "enable_vm"
CONF_ENABLE_SENSORS = "enable_sensors"
CONF_ENABLE_NUT = "enable_nut"
DEFAULT_ENABLE_DISKS = True
DEFAULT_ENABLE_POOLS = True
DEFAULT_ENABLE_SERVICES = True
DEFAULT_ENABLE_LXC = True
DEFAULT_ENABLE_DOCKER = True
# The only category that defaults to off, because it is the only one whose cost
# scales with how much of it there is. Every other resource is one request per
# poll no matter how many disks, pools or containers it covers; container stats
# are one request *per container*, since Docker reports usage one container at a
# time (see ``async_get_docker_container_stats``). On a server with fifty
# containers that turns a ten-request poll into a sixty-request one, stretches
# the poll from about a second to about ten, and adds a sensor per container
# that writes to the recorder on every cycle.
#
# None of that is wrong to pay for - it is just not a cost to sign someone up
# for silently. Switching it on creates the entities; which containers are
# actually polled then follows from which of those entities the user leaves
# enabled (see ``DockerStatsContext``).
DEFAULT_ENABLE_DOCKER_STATS = False
DEFAULT_ENABLE_COMPOSE = True
DEFAULT_ENABLE_VM = True
DEFAULT_ENABLE_SENSORS = True
DEFAULT_ENABLE_NUT = True
