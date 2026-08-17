"""Tests for the icon translations in icons.json.

Entity icons live in ``icons.json`` rather than on the ``EntityDescription``
(``script/architecture-check`` enforces that). Two things can silently break
that the static check cannot see: a key in ``icons.json`` that no entity ever
asks for, and — for the hardware readings, whose key is built at runtime from
the reading's category — an entity asking for a key the file does not define.
Neither surfaces as an error; the icon just quietly disappears in the frontend.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from custom_components.mos.sensor.hardware import _ICON_CATEGORIES, _icon_translation_key
from homeassistant.helpers import icon as icon_helper

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from homeassistant.core import HomeAssistant

ICONS_FILE = Path(__file__).resolve().parents[1] / "custom_components" / "mos" / "icons.json"


def _entity_icons() -> dict[str, dict[str, dict]]:
    """Return the ``entity`` section of icons.json, keyed by platform."""
    return json.loads(ICONS_FILE.read_text(encoding="utf-8"))["entity"]


@pytest.mark.unit
def test_every_icon_entry_defines_a_default() -> None:
    """A section with only ``state`` icons leaves the entity iconless in every other state."""
    for platform, entries in _entity_icons().items():
        for translation_key, section in entries.items():
            assert "default" in section, f"{platform}.{translation_key} has no default icon"


@pytest.mark.unit
@pytest.mark.parametrize("category", [*sorted(_ICON_CATEGORIES), "a-category-mos-invented"])
def test_hardware_readings_only_ask_for_icons_that_exist(category: str) -> None:
    """The runtime-built key must always name a section icons.json actually defines.

    Includes an unrecognised category: MOS assigns these per server, so a
    category this integration has never seen is a normal case, not a bug, and
    it has to land on the ``other`` icon rather than on nothing.
    """
    key = _icon_translation_key({"category": category})
    assert key in _entity_icons()["sensor"], f"category {category!r} resolves to unknown icon key {key!r}"


async def test_icon_translations_are_served_to_the_frontend(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Icon translations reach the frontend through the icon helper, not the state attributes.

    Worth asserting because it is the whole delivery mechanism: unlike a
    hardcoded ``icon=``, an icon translation never appears in
    ``state.attributes``, so no other test would notice the file going missing
    or growing a wrong platform key.
    """
    served = (await icon_helper.async_get_icons(hass, "entity", integrations=["mos"]))["mos"]

    assert served == _entity_icons()
    assert served["sensor"]["pool_usage"]["default"] == "mdi:harddisk"
    assert served["switch"]["docker_power"]["default"] == "mdi:power"
    assert served["binary_sensor"]["docker_running"]["default"] == "mdi:docker"
