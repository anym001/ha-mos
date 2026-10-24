"""
Serves the MOS NAS Card and has the frontend load it on every page.

The card's source is in ``frontend/`` at the repository root, and it ships as
its built bundle, ``www/mos-card.js``. HACS lists a card that only works
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
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.helpers import issue_registry as ir

from .const import CARD_FILENAME, CARD_URL, DOMAIN, ISSUE_SEPARATE_CARD, LOGGER, SEPARATE_CARD_LEARN_MORE_URL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

CARD_PATH = Path(__file__).parent / "www" / CARD_FILENAME


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
    await async_check_separate_card(hass)


async def async_check_separate_card(hass: HomeAssistant) -> None:
    """
    Raise a repair issue while a dashboard resource still loads its own copy of the card.

    That copy comes from the card's former HACS listing or a manual install. The
    bundled card keeps the element, but a copy older than 0.2.5 throws on its own
    define and lists the card a second time in the picker, and either way it has
    to be updated by hand. Checked at every start, so removing the resource
    clears the issue on the next restart.
    """
    resources = hass.data[LOVELACE_DATA].resources
    await resources.async_get_info()
    separate = [
        url
        for item in resources.async_items()
        if (url := str(item.get("url", ""))).split("?", 1)[0].endswith(f"/{CARD_FILENAME}")
        and not url.startswith(CARD_URL)
    ]

    if not separate:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_SEPARATE_CARD)
        return

    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_SEPARATE_CARD,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_SEPARATE_CARD,
        translation_placeholders={"url": ", ".join(separate)},
        learn_more_url=SEPARATE_CARD_LEARN_MORE_URL,
    )
