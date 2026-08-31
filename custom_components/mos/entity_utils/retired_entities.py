"""
Registry cleanup for entities this integration no longer creates.

Home Assistant does not forget an entity when its ``EntityDescription`` is
deleted from the code. The registry entry survives, and the registry writes an
``unavailable`` state for every registered entity with no object behind it, so
a retired sensor stays on its device page forever with no way for the user to
tell it apart from one that is merely broken.

Removing the registry entry is what actually retires it. It runs on every setup
rather than once, because an entry restored from a backup, or one that was
loaded while an older version was installed, brings the stale rows back.
"""

from typing import TYPE_CHECKING

from custom_components.mos.const import LOGGER
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er

if TYPE_CHECKING:
    from collections.abc import Collection

    from homeassistant.core import HomeAssistant

# Unique ID suffixes of entities the integration used to create. The unique ID
# is ``{entry_id}_{kind}_{name}_{key}``, so the key alone identifies them across
# every device kind that carried one.
RETIRED_UNIQUE_ID_SUFFIXES = ("_memory_percent",)


@callback
def async_remove_retired_entities(
    hass: HomeAssistant,
    entry_id: str,
    suffixes: Collection[str] = RETIRED_UNIQUE_ID_SUFFIXES,
) -> None:
    """
    Delete this entry's registry entries for entities that are no longer created.

    Args:
        hass: The Home Assistant instance.
        entry_id: The config entry whose entities are being cleaned up.
        suffixes: Unique ID suffixes to retire.

    """
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry_id):
        if entity.unique_id.endswith(tuple(suffixes)):
            LOGGER.debug("Removing retired entity %s", entity.entity_id)
            registry.async_remove(entity.entity_id)
