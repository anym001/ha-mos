"""
Server-hosted guest icons for mos.

MOS ships the artwork it shows for Docker containers, LXC containers and VMs as
plain static files under its own web root, outside ``/api/v1`` and needing no
token::

    /docker_icons/<container name>.png
    /os_icons/<distribution>.png        - the stock per-distribution artwork
    /lxc_custom/<guest name>.png        - a custom icon uploaded for one guest

Which of the two applies to an LXC container or a VM is a property of the guest,
not something to guess at: ``/lxc/containers`` reports ``custom_icon`` and
``distribution``, ``/vm/machines`` reports ``customIcon`` and ``icon``. Neither
field appears on the ``/usage`` endpoints the coordinator polls, so this module
fetches them from the plain endpoints - rarely, because they change when someone
edits a guest, not every poll.

Every candidate URL is then confirmed with a HEAD before it is handed to the
frontend. A guest with no artwork answers 404, and an ``entity_picture`` that
404s renders as a broken image on every card showing that entity - visibly worse
than no picture at all. The results are cached, so the steady state costs no
requests.

Preferring these over the icon URL in a container's MOS template (see
``docker_templates.resolve_icon``) is deliberate: the template points at a public
CDN, which a dashboard on a network without internet access cannot load, while
this one is served by the same host the dashboard is already talking to.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from custom_components.mos.api import MOSApiClient

from custom_components.mos.api import MOSApiClientError, MOSApiClientNotFoundError, MOSApiClientPermissionError
from custom_components.mos.const import LOGGER

_DOCKER_ICON_DIR = "docker_icons"
_OS_ICON_DIR = "os_icons"
# Shared by LXC and VMs despite the name: MOS stores a VM's uploaded icon in the
# same directory as an LXC container's.
_CUSTOM_ICON_DIR = "lxc_custom"

# How long "this icon does not exist" is trusted before being asked again. A
# positive answer is never re-checked - the file cannot stop existing in a way
# that matters, since the browser would simply show nothing - but a negative one
# has to expire, or artwork added after the integration started would never
# appear until Home Assistant restarts.
_MISS_TTL_SECONDS = 3600.0

# How long a guest's configuration is reused before being re-read. Bounds how
# long a newly uploaded custom icon stays invisible; a poll that sees a guest it
# has no configuration for refetches immediately regardless.
_DETAIL_TTL_SECONDS = 900.0

# The floor on how often an unrecognised guest may trigger an early refetch. See
# ``GuestIconCache._async_details`` for why the trigger needs one at all.
_DETAIL_RETRY_SECONDS = 60.0


def _asset_path(directory: str, stem: str | None) -> str | None:
    """
    Build the web-root-relative path of an icon, or ``None`` if there is no name for it.

    The stem is percent-encoded: it is a guest name straight from the server,
    and a name containing ``/`` or ``?`` would otherwise address something other
    than the intended file.

    Returns:
        The path (e.g. ``docker_icons/Plex.png``), or ``None``.

    """
    if not isinstance(stem, str) or not stem.strip():
        return None
    return f"{directory}/{quote(stem, safe='')}.png"


def docker_icon_path(name: str | None) -> str | None:
    """
    Return the icon path for a Docker container.

    Docker has no per-container icon flag: MOS names the file after the
    container, and a container with no artwork simply 404s.

    Returns:
        The path, or ``None`` for a container with no name.

    """
    return _asset_path(_DOCKER_ICON_DIR, name)


def lxc_icon_path(detail: dict[str, Any]) -> str | None:
    """
    Return the icon path for an LXC container, from its ``/lxc/containers`` entry.

    ``custom_icon`` decides the directory. A container reporting no
    ``distribution`` is treated as custom too, rather than yielding nothing:
    the flag and the field are two views of the same fact, and disagreeing about
    them costs one cached HEAD, not a wrong picture.

    The distribution is used verbatim. MOS reports it lower-cased and stores the
    files under the same spelling (``os_icons/debian.png`` exists,
    ``os_icons/Debian.png`` does not), so normalising it here would be inventing
    a rule rather than following one - and the existence check catches any
    mismatch anyway.

    Returns:
        The path, or ``None`` when neither source names a file.

    """
    if detail.get("custom_icon") or not detail.get("distribution"):
        return _asset_path(_CUSTOM_ICON_DIR, detail.get("name"))
    return _asset_path(_OS_ICON_DIR, detail.get("distribution"))


def vm_icon_path(detail: dict[str, Any]) -> str | None:
    """
    Return the icon path for a VM, from its ``/vm/machines`` entry.

    The same rule as LXC, under MOS's camelCase spelling for the VM endpoint:
    ``customIcon`` picks the directory, and ``icon`` names the stock artwork.

    Returns:
        The path, or ``None`` when neither source names a file.

    """
    if detail.get("customIcon") or not detail.get("icon"):
        return _asset_path(_CUSTOM_ICON_DIR, detail.get("name"))
    return _asset_path(_OS_ICON_DIR, detail.get("icon"))


class GuestIconCache:
    """
    Resolves guest icon URLs, caching both halves of the lookup.

    The two halves are cached separately because they go stale for different
    reasons: which file a guest points at changes when the guest is edited,
    while whether that file exists changes when artwork is uploaded.
    """

    def __init__(self, client: MOSApiClient) -> None:
        """Initialize an empty cache bound to an API client."""
        self._client = client
        # icon path -> (exists, when it was checked)
        self._probes: dict[str, tuple[bool, float]] = {}
        # endpoint label -> (name -> configuration, when it was fetched)
        self._details: dict[str, tuple[dict[str, dict[str, Any]], float]] = {}
        # Endpoint labels the token's scope refuses. Never asked for again.
        self._denied: set[str] = set()
        # Endpoint labels this MOS version has no endpoint for. Still asked for,
        # but at the slow rate only.
        self._unsupported: set[str] = set()

    @property
    def denied_sources(self) -> frozenset[str]:
        """
        Configuration endpoints the token's scope refuses, given up on for good.

        Named after the coordinator's own ``forbidden_resources``, which records
        the same fact about the resources it polls. Surfaced in diagnostics so a
        "why do my guests have no icons" report does not have to be guessed at.
        """
        return frozenset(self._denied)

    @property
    def unsupported_sources(self) -> frozenset[str]:
        """
        Configuration endpoints this MOS version does not have.

        The counterpart to the coordinator's ``unsupported_resources``, and like
        it, still re-probed: a MOS update that adds the endpoint is picked up
        without a reload.
        """
        return frozenset(self._unsupported)

    async def async_icon_url(self, path: str | None) -> str | None:
        """
        Turn a candidate icon path into an absolute URL, if the server has that file.

        Returns:
            The absolute URL, or ``None`` when there is no such icon.

        """
        if path is None:
            return None

        now = time.monotonic()
        cached = self._probes.get(path)
        if cached is not None and (cached[0] or now - cached[1] < _MISS_TTL_SECONDS):
            exists = cached[0]
        else:
            exists = await self._client.async_static_asset_exists(path)
            self._probes[path] = (exists, now)

        return f"{self._client.root_url}/{path}" if exists else None

    async def _async_details(
        self,
        label: str,
        fetch: Callable[[], Awaitable[Any]],
        names: set[str],
    ) -> dict[str, dict[str, Any]]:
        """
        Return per-guest configuration keyed by name, refetching only when needed.

        Refetches when the entry has expired, or - much sooner - when a guest in
        this poll has no cached configuration at all, since a guest created since
        the last fetch would otherwise wait out the whole TTL without a picture.

        That second trigger is floored at ``_DETAIL_RETRY_SECONDS`` rather than
        acted on immediately, because it cannot distinguish "created since the
        last fetch" from "this endpoint does not list that guest at all". Without
        the floor the latter would refetch on every single poll, forever.

        How a failure is treated follows the same split the rest of the
        integration applies to the resources it polls (see the exception
        hierarchy in ``api/__init__.py``), because the reasoning is identical -
        only the consequence is smaller, being a picture rather than an entity:

        - A **scope denial** is a fact about the token, not a server hiccup. The
          server named the resource it refused, so asking again can only repeat
          the refusal; the endpoint is dropped for the life of the entry, and a
          widened scope is picked up by reloading, exactly as it is for the
          coordinator's ``forbidden_resources``.
        - A **404** means this MOS version predates the endpoint. It stays in the
          rotation so a MOS update is picked up without a reload, but the
          early-refetch trigger is dropped for it: every guest is permanently
          "unknown" on an endpoint that lists none, which is precisely the case
          the floor alone cannot bound below one request a minute, forever.
        - Anything else is transient and retried at the bounded rate.

        The timestamp is written on every attempt, not only on success, so a
        failing endpoint is retried at the same bounded rate. A failed fetch
        keeps the previous entry - an icon is not worth taking a poll down over,
        nor worth blanking a working picture for - so this never raises.

        Returns:
            The cached configuration, which may be empty or stale on failure.

        """
        cached = self._details.get(label)
        previous = cached[0] if cached else {}

        if label in self._denied:
            return previous

        if cached is not None:
            age = time.monotonic() - cached[1]
            unknown = set() if label in self._unsupported else names - cached[0].keys()
            if age < (_DETAIL_RETRY_SECONDS if unknown else _DETAIL_TTL_SECONDS):
                return cached[0]

        try:
            payload = await fetch()
        except MOSApiClientPermissionError as exception:
            LOGGER.debug(
                "API token has no read access to the %s configuration - guest icons fall back to the "
                "per-guest name, and it will not be requested again: %s",
                label,
                exception,
            )
            self._denied.add(label)
            self._details[label] = (previous, time.monotonic())
            return previous
        except MOSApiClientNotFoundError as exception:
            LOGGER.debug("This MOS version has no %s configuration endpoint for icons: %s", label, exception)
            self._unsupported.add(label)
            self._details[label] = (previous, time.monotonic())
            return previous
        except MOSApiClientError as exception:
            LOGGER.debug("Could not fetch %s configuration for icons: %s", label, exception)
            self._details[label] = (previous, time.monotonic())
            return previous

        self._unsupported.discard(label)
        details = {name: entry for entry in payload or [] if isinstance(entry, dict) and (name := entry.get("name"))}
        self._details[label] = (details, time.monotonic())
        return details

    async def async_docker_icon_url(self, name: str | None) -> str | None:
        """
        Return the server-hosted icon URL for a Docker container.

        Returns:
            The URL, or ``None`` when the server hosts no icon for it.

        """
        return await self.async_icon_url(docker_icon_path(name))

    async def async_add_lxc_icons(self, containers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Stamp each LXC container with its ``icon_url``.

        Returns:
            The containers, each with ``icon_url`` added (possibly ``None``).

        """
        if not containers:
            return containers
        names = {name for container in containers if (name := container.get("name"))}
        details = await self._async_details("lxc", self._client.async_get_lxc_container_details, names)
        return [
            {
                **container,
                "icon_url": await self.async_icon_url(
                    lxc_icon_path(details.get(container.get("name") or "") or container)
                ),
            }
            for container in containers
        ]

    async def async_add_vm_icons(self, machines: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Stamp each VM with its ``icon_url``.

        Returns:
            The machines, each with ``icon_url`` added (possibly ``None``).

        """
        if not machines:
            return machines
        names = {name for machine in machines if (name := machine.get("name"))}
        details = await self._async_details("vm", self._client.async_get_vm_machine_details, names)
        return [
            {
                **machine,
                "icon_url": await self.async_icon_url(vm_icon_path(details.get(machine.get("name") or "") or machine)),
            }
            for machine in machines
        ]
