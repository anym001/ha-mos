"""
Per-container MOS template cache for mos.

Two things a Docker container entity wants are missing from every endpoint the
coordinator polls: the container's icon, and a web link that survives the
container being stopped. Both live in the container's MOS template
(``/docker/mos/templates/{name}``), which has to be fetched one container at a
time - the collection endpoint returns template *names* only.

Fetching that on every poll would be an N+1 against data that changes only when
someone edits the container. It does not have to be: MOS recreates a container
when its template is edited, giving it a new Docker id, and that id already
arrives with each poll's engine payload (see ``_merge_docker_engine_state``).
So the id doubles as the cache's invalidation signal and the steady state costs
no requests at all.

The templates' installed/removed name list is deliberately *not* used for
invalidation: editing a container leaves its name in place, so a cache keyed on
that list would keep serving a stale port mapping indefinitely.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from custom_components.mos.api import MOSApiClientError, MOSApiClientNotFoundError
from custom_components.mos.const import DOCKER_WEB_UI_LABEL, LOGGER

if TYPE_CHECKING:
    from custom_components.mos.api import MOSApiClient

# MOS writes the host placeholder as ``[ADDRESS]`` in the container label and as
# ``[IP]`` in the template; the two mean the same thing.
_HOST_PLACEHOLDER = re.compile(r"\[(?:ADDRESS|IP)\]")
_PORT_PLACEHOLDER = re.compile(r"\[PORT:(\d+)\]")


def _resolve_port(port: int, container: dict[str, Any], template: dict[str, Any] | None) -> int | None:
    """
    Translate the port a web interface placeholder names into the host port.

    The number inside ``[PORT:n]`` is *not* reliably the container port. MOS
    writes whichever side of the mapping was configured, and one server had
    both conventions at once: Dozzle (``8080:9001``) and Nextcloud
    (``443:7443``) named the container port, while qbittorrent
    (``8080:8092``), filebrowser-quantum (``80:8100``) and omnitools
    (``80:8990``) named the host port. So both sides are tried.

    The container port is tried first, which is what keeps a remapped container
    pointing where Docker publishes it - verified by remapping one from
    ``3000:3000`` to ``3001:3000``, where the placeholder kept naming 3000 and
    the reachable port became 3001. Reversing the two would send that link back
    to the port nothing listens on.

    The live mapping is preferred over the template because it reflects what
    Docker is actually doing, including containers changed outside MOS. It only
    exists while the container runs, though - Docker reports no ports for a
    stopped container - so the template's configured pairs stand in.

    Host networking publishes nothing and needs neither source: a container on
    the host's network stack is reachable on the very port it listens on.

    Returns:
        The host port, or ``None`` if no source knows this port.

    """
    for published in container.get("ports") or []:
        if published.get("PrivatePort") == port and published.get("PublicPort"):
            return int(published["PublicPort"])

    for published in container.get("ports") or []:
        if published.get("PublicPort") == port:
            return port

    # Compared exactly rather than by substring: this field carries a
    # user-defined network's own name, and one called "hostnet" publishes its
    # ports like any other bridge.
    if container.get("network_mode") == "host":
        return port

    for configured in (template or {}).get("ports") or []:
        sides = (str(configured.get("container")), str(configured.get("host")))
        if str(port) in sides and configured.get("host"):
            try:
                return int(configured["host"])
            except TypeError, ValueError:
                return None
    return None


def resolve_web_ui_url(container: dict[str, Any], template: dict[str, Any] | None, host: str | None) -> str | None:
    """
    Build the clickable web interface URL for a container, or ``None``.

    ``None`` covers every case where the link cannot be known to be right: no
    web interface configured, no host to point at, or a port whose mapping
    neither the running container nor its template can supply. That is
    deliberate - a link that silently points at the wrong port looks like a
    working link and fails only when someone clicks it.

    Returns:
        The resolved URL, or ``None`` when it cannot be determined.

    """
    raw = (container.get("labels") or {}).get(DOCKER_WEB_UI_LABEL) or (template or {}).get("web_ui_url")
    # Type-checked rather than merely truth-checked: both halves come straight
    # from the server, and a link is not worth taking a poll down over.
    if not isinstance(raw, str) or not raw or not isinstance(host, str) or not host:
        return None

    resolved = _HOST_PLACEHOLDER.sub(host, raw)

    unresolved = False

    def _substitute(match: re.Match[str]) -> str:
        nonlocal unresolved
        port = _resolve_port(int(match.group(1)), container, template)
        if port is None:
            unresolved = True
            return match.group(0)
        return str(port)

    resolved = _PORT_PLACEHOLDER.sub(_substitute, resolved)
    return None if unresolved else resolved


def resolve_icon(template: dict[str, Any] | None) -> str | None:
    """
    Return the template's icon URL if it is one a browser can load.

    The URLs MOS ships point at public CDNs (GitHub raw, jsDelivr), so they are
    fetched by the browser showing the dashboard rather than by Home Assistant.
    Anything that is not plain http(s) is dropped rather than handed to the
    frontend as an entity picture.

    Returns:
        The icon URL, or ``None`` when the template has none usable.

    """
    icon = (template or {}).get("icon")
    if isinstance(icon, str) and icon.startswith(("http://", "https://")):
        return icon
    return None


class DockerTemplateCache:
    """
    Caches one MOS template per Docker container, keyed by container id.

    An entry's value may be ``None``: containers created outside MOS have no
    template and answer 404. That negative result is cached like any other, so
    a hand-rolled container does not cost a request on every poll.
    """

    def __init__(self, client: MOSApiClient) -> None:
        """Initialize an empty cache bound to an API client."""
        self._client = client
        # name -> (container id the template was fetched for, template or None)
        self._entries: dict[str, tuple[str | None, dict[str, Any] | None]] = {}

    def get(self, name: str) -> dict[str, Any] | None:
        """
        Return the cached template for a container.

        Returns:
            The template, or ``None`` if the container has none or none has been
            fetched yet.

        """
        cached = self._entries.get(name)
        return cached[1] if cached else None

    async def async_refresh(self, containers: list[dict[str, Any]]) -> None:
        """
        Fetch templates for containers that are new or have been recreated.

        Containers that disappeared are dropped from the cache. A container
        whose id is unchanged is not re-fetched, which is the normal case and
        makes this a no-op on almost every poll.

        A container with no id - the engine proxy was unavailable this poll -
        is only fetched if nothing is cached for it yet, so a proxy outage
        cannot trigger a refetch storm.

        Failures other than 404 leave the previous entry untouched and are
        retried next poll: an icon and a web link are worth less than the poll
        they would otherwise take down.
        """
        current_names = {name for container in containers if (name := container.get("name"))}
        for stale_name in self._entries.keys() - current_names:
            del self._entries[stale_name]

        for container in containers:
            name = container.get("name")
            if not name:
                continue
            container_id = container.get("container_id")
            cached = self._entries.get(name)
            if cached is not None and cached[0] == container_id:
                continue

            try:
                template = await self._client.async_get_docker_template(name)
            except MOSApiClientNotFoundError:
                LOGGER.debug("No MOS template for Docker container %s; caching that", name)
                self._entries[name] = (container_id, None)
            except MOSApiClientError as exception:
                LOGGER.debug("Could not fetch MOS template for Docker container %s: %s", name, exception)
            else:
                self._entries[name] = (container_id, template if isinstance(template, dict) else None)
