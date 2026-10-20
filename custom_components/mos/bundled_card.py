"""
Serves the MOS NAS Card and has the frontend load it on every page.

The card is developed in its own repository, ``anym001/ha-mos-card``, and ships
here as its built bundle, ``www/mos-card.js``. HACS lists a card that only works
with one integration as part of that integration, not as a repository of its
own, so installing this integration is what makes ``custom:mos-card`` available.

It is announced through ``add_extra_js_url`` rather than as a Lovelace resource:
that works for dashboards in YAML mode too, writes nothing into the user's
resource collection, and leaves nothing behind once the integration is removed.
"""

from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http.server import StaticPathConfig

from .const import CARD_URL, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

CARD_PATH = Path(__file__).parent / "www" / "mos-card.js"


def _content_hash(path: Path) -> str | None:
    """Return a short hash of the bundle, or None if it is missing."""
    try:
        return sha256(path.read_bytes()).hexdigest()[:16]
    except FileNotFoundError:
        return None


async def async_register_card(hass: HomeAssistant) -> None:
    """
    Serve the bundled card and add it to every frontend page.

    Called once per Home Assistant from ``async_setup``. The URL carries the
    bundle's content hash, so the static route can be cached for good while a
    new bundle still reaches the browser on the first load after an update.

    A missing bundle is logged and skipped rather than failing setup: the
    entities do not depend on the card.
    """
    digest = await hass.async_add_executor_job(_content_hash, CARD_PATH)
    if digest is None:
        LOGGER.warning("The bundled MOS NAS Card is missing at %s; the card will not be available", CARD_PATH)
        return

    await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=True)])
    add_extra_js_url(hass, f"{CARD_URL}?v={digest}")
