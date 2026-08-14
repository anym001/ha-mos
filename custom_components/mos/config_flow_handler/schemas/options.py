"""
Options flow schemas.

Schemas for the options flow that allows users to modify settings
after initial configuration.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from custom_components.mos.const import (
    CONF_ENABLE_DISKS,
    CONF_ENABLE_DOCKER,
    CONF_ENABLE_DOCKER_STATS,
    CONF_ENABLE_LXC,
    CONF_ENABLE_NUT,
    CONF_ENABLE_POOLS,
    CONF_ENABLE_SENSORS,
    CONF_ENABLE_SERVICES,
    CONF_ENABLE_VM,
    DEFAULT_ENABLE_DISKS,
    DEFAULT_ENABLE_DOCKER,
    DEFAULT_ENABLE_DOCKER_STATS,
    DEFAULT_ENABLE_LXC,
    DEFAULT_ENABLE_NUT,
    DEFAULT_ENABLE_POOLS,
    DEFAULT_ENABLE_SENSORS,
    DEFAULT_ENABLE_SERVICES,
    DEFAULT_ENABLE_VM,
    DEFAULT_SCAN_INTERVAL,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers import selector


def get_options_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """
    Get schema for options flow.

    Args:
        defaults: Optional dictionary of current option values.

    Returns:
        Voluptuous schema for options configuration.

    """
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL,
                    max=MAX_SCAN_INTERVAL,
                    step=1,
                    unit_of_measurement="s",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Optional(
                CONF_ENABLE_DISKS,
                default=defaults.get(CONF_ENABLE_DISKS, DEFAULT_ENABLE_DISKS),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_ENABLE_POOLS,
                default=defaults.get(CONF_ENABLE_POOLS, DEFAULT_ENABLE_POOLS),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_ENABLE_SERVICES,
                default=defaults.get(CONF_ENABLE_SERVICES, DEFAULT_ENABLE_SERVICES),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_ENABLE_LXC,
                default=defaults.get(CONF_ENABLE_LXC, DEFAULT_ENABLE_LXC),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_ENABLE_DOCKER,
                default=defaults.get(CONF_ENABLE_DOCKER, DEFAULT_ENABLE_DOCKER),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_ENABLE_DOCKER_STATS,
                default=defaults.get(CONF_ENABLE_DOCKER_STATS, DEFAULT_ENABLE_DOCKER_STATS),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_ENABLE_VM,
                default=defaults.get(CONF_ENABLE_VM, DEFAULT_ENABLE_VM),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_ENABLE_SENSORS,
                default=defaults.get(CONF_ENABLE_SENSORS, DEFAULT_ENABLE_SENSORS),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_ENABLE_NUT,
                default=defaults.get(CONF_ENABLE_NUT, DEFAULT_ENABLE_NUT),
            ): selector.BooleanSelector(),
        },
    )


__all__ = [
    "get_options_schema",
]
