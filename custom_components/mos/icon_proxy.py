"""
Serves guest artwork to browsers that cannot reach the MOS server.

The icons MOS ships for its guests live on the MOS server itself
(``/docker_icons``, ``/os_icons``, ``/lxc_custom``; see
``coordinator/guest_icons.py``), and a Docker container without one falls back
to the CDN URL in its MOS template. Both used to be handed to the frontend as
absolute URLs, which made the *browser* the thing that had to reach them. That
holds only on the local network:

- the MOS host is addressed by its LAN name or address, which resolves to
  nothing from a phone on mobile data, and
- it is normally addressed over plain ``http``, which a browser showing a
  dashboard served over ``https`` (Nabu Casa, any reverse proxy) refuses to
  load as mixed content - so even a VPN back into the LAN does not fix it.

So Home Assistant fetches the artwork instead and serves it from its own origin,
under a path the frontend can always reach:

    /api/mos/icon/<entry id>/<token>

``token`` is derived from the source URL, and the proxy only ever fetches a URL
that an entity has registered here - the request cannot name its own target, or
this would be an open proxy into the network Home Assistant sits on. The route
carries no authentication, because a browser sends none for an ``<img>``: the
config entry id in the path is what makes it unguessable, and what it protects
is a picture.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from hashlib import sha256
from http import HTTPStatus
import time
from typing import TYPE_CHECKING

import aiohttp
from aiohttp import hdrs, web

from custom_components.mos.const import (
    DEFAULT_TIMEOUT,
    DOMAIN,
    ICON_PROXY_HIT_TTL_SECONDS,
    ICON_PROXY_MAX_BYTES,
    ICON_PROXY_MAX_CACHED,
    ICON_PROXY_MISS_TTL_SECONDS,
    ICON_PROXY_URL,
    ICON_PROXY_VIEW_REGISTERED,
    LOGGER,
)
from custom_components.mos.utils import async_read_capped_body
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.http import KEY_HASS, HomeAssistantView

if TYPE_CHECKING:
    from custom_components.mos.api import MOSApiClient

_CACHE_CONTROL = f"private, max-age={int(ICON_PROXY_HIT_TTL_SECONDS)}"


@dataclass(frozen=True, slots=True)
class Icon:
    """One piece of artwork, as it is served."""

    body: bytes
    content_type: str
    etag: str

    @classmethod
    def from_response(cls, body: bytes, content_type: str) -> Icon:
        """
        Build an icon, tagging it with a validator derived from its bytes.

        The tag is what lets a browser revalidate instead of downloading again:
        the proxy path is derived from the *source URL*, so it stays the same
        when the artwork behind it is replaced, and the bytes are the only thing
        that can say whether what the browser holds is still current.

        Returns:
            The icon, ready to serve.

        """
        return cls(body=body, content_type=content_type, etag=f'"{sha256(body).hexdigest()[:32]}"')


def _token(url: str) -> str:
    """
    Derive the proxy path segment addressing an icon source.

    Derived from the URL rather than allocated, so it survives a restart: a
    browser holding a page from before it still asks for a token the entities
    register again on their first state write.

    Returns:
        A hex digest, shortened to the point where a collision is not a thing
        that happens between the handful of icons one server has.

    """
    return sha256(url.encode()).hexdigest()[:32]


class MOSIconProxy:
    """
    Fetches and caches the guest artwork of one config entry.

    Holds two maps, and only the second is a cache: ``_sources`` is the
    allow-list of URLs this entry has published pictures for, and it is what
    keeps a request from choosing where the proxy connects to. It is never
    evicted from - it costs a URL per icon the server has ever shown, and
    dropping an entry would blank a picture on a page still open somewhere until
    the next state write.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str, client: MOSApiClient) -> None:
        """Initialize an empty proxy for one config entry."""
        self._hass = hass
        self._entry_id = entry_id
        self._client = client
        # token -> the URL it stands for
        self._sources: dict[str, str] = {}
        # token -> (the icon or None if the source did not serve one, when it was fetched)
        self._cache: dict[str, tuple[Icon | None, float]] = {}

    @callback
    def async_url(self, source: str | None) -> str | None:
        """
        Return the proxy URL for an icon source, registering it on the way.

        Called from the ``entity_picture`` of every entity that has one, so it
        stays a dict write: the fetch happens when a browser asks, not here.

        Args:
            source: The absolute URL the icon actually lives at.

        Returns:
            The path to publish as ``entity_picture``, or ``None`` when there is
            no icon.

        """
        if not source:
            return None
        token = _token(source)
        self._sources[token] = source
        return ICON_PROXY_URL.format(entry_id=self._entry_id, token=token)

    async def async_icon(self, token: str) -> Icon | None:
        """
        Return an icon, fetching it if the cache has none.

        A failure is cached too, for a fraction of the time a success is: an
        icon that is briefly unreachable should come back on its own, but not at
        the cost of one upstream request per dashboard that has the page open.

        Returns:
            The icon, or ``None`` when there is no such token or the source did
            not answer with one.

        """
        source = self._sources.get(token)
        if source is None:
            return None

        now = time.monotonic()
        cached = self._cache.get(token)
        if cached is not None:
            ttl = ICON_PROXY_HIT_TTL_SECONDS if cached[0] else ICON_PROXY_MISS_TTL_SECONDS
            if now - cached[1] < ttl:
                return cached[0]

        icon = await self._async_fetch(source)
        self._cache.pop(token, None)
        self._cache[token] = (icon, now)
        while len(self._cache) > ICON_PROXY_MAX_CACHED:
            del self._cache[next(iter(self._cache))]
        return icon

    async def _async_fetch(self, source: str) -> Icon | None:
        """
        Fetch one icon from wherever it lives.

        Which of the two it is decides how it is fetched. An icon on the MOS
        server's own web root goes through the API client, so it inherits the
        session, the timeout and the request pacing every other call to that
        host already obeys. Anything else is a public CDN URL from a container's
        MOS template, fetched with a verifying session - the entry's
        ``verify_ssl`` option is a statement about the MOS server's own
        certificate, not a licence to skip verification for a third party.

        Returns:
            The icon, or ``None``.

        """
        root = f"{self._client.root_url}/"
        if source.startswith(root):
            asset = await self._client.async_fetch_static_asset(source.removeprefix(root))
            return Icon.from_response(*asset) if asset else None

        try:
            async with (
                asyncio.timeout(DEFAULT_TIMEOUT),
                async_get_clientsession(self._hass).get(source) as response,
            ):
                if response.status != HTTPStatus.OK or not (response.content_type or "").startswith("image/"):
                    return None
                body = await async_read_capped_body(response, ICON_PROXY_MAX_BYTES)
                if body is None:
                    return None
                return Icon.from_response(body, response.content_type)
        except (TimeoutError, aiohttp.ClientError) as exception:
            LOGGER.debug("Could not fetch the icon at %s: %s", source, exception)
            return None


def _holds(if_none_match: str | None, etag: str) -> bool:
    """
    Whether the caller says it already has this exact icon.

    Returns:
        ``True`` for ``*`` or for a tag matching this one, weak or strong: the
        two forms mean the same thing for a whole file served as it is.

    """
    if not if_none_match:
        return False
    candidates = {candidate.strip().removeprefix("W/") for candidate in if_none_match.split(",")}
    return "*" in candidates or etag in candidates


class MOSIconProxyView(HomeAssistantView):
    """Serves the artwork the entities of a config entry point their pictures at."""

    url = ICON_PROXY_URL
    name = f"api:{DOMAIN}:icon"
    requires_auth = False

    async def get(self, request: web.Request, entry_id: str, token: str) -> web.Response:
        """
        Serve one icon.

        A browser that already holds the bytes gets 304 rather than them again.
        Icons outlive the hour they are cached for, so the alternative to
        revalidating cheaply is not "no requests" but re-downloading every icon
        on the dashboard once an hour.

        Returns:
            The image, 304 if the caller already has it, or 404 - for an entry
            that is not this integration's or not loaded, for a token no entity
            has published, and for a source that did not answer with an image.
            Those are the same answer on purpose: an unauthenticated caller
            learns nothing from which of them it was.

        """
        hass = request.app[KEY_HASS]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
            return web.Response(status=HTTPStatus.NOT_FOUND)

        icon = await entry.runtime_data.icon_proxy.async_icon(token)
        if icon is None:
            return web.Response(status=HTTPStatus.NOT_FOUND)

        headers = {hdrs.CACHE_CONTROL: _CACHE_CONTROL, hdrs.ETAG: icon.etag}
        if _holds(request.headers.get(hdrs.IF_NONE_MATCH), icon.etag):
            return web.Response(status=HTTPStatus.NOT_MODIFIED, headers=headers)
        return web.Response(body=icon.body, content_type=icon.content_type, headers=headers)


@callback
def async_register_icon_proxy_view(hass: HomeAssistant) -> None:
    """
    Register the icon route, once per Home Assistant rather than per config entry.

    The route is global while the proxies behind it are per entry, and
    registering the same path twice raises. It is never unregistered: Home
    Assistant has no API for that, and a route whose entry is gone answers 404
    on its own.
    """
    if hass.data.get(ICON_PROXY_VIEW_REGISTERED):
        return
    hass.data[ICON_PROXY_VIEW_REGISTERED] = True
    hass.http.register_view(MOSIconProxyView())
