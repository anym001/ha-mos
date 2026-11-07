"""Gate the usage figures of Docker, Compose, LXC and VM guests on their running state."""

from collections.abc import Callable
from typing import Any

from homeassistant.helpers.typing import StateType

type GuestValueFn = Callable[[dict[str, Any]], StateType]


def state_is_running(guest: dict[str, Any]) -> bool:
    """Return whether a guest reporting a ``state`` string is running."""
    return guest.get("state") == "running"


def while_running(
    value_fn: GuestValueFn, is_running: Callable[[dict[str, Any]], bool] = state_is_running
) -> GuestValueFn:
    """
    Wrap a usage value function so a guest that is not running reads unknown.

    A stopped guest can still carry figures - the last ones measured, or zeroes.
    Neither is a measurement, so the sensor reports ``None`` instead and stays
    available.

    Args:
        value_fn: Reads the figure from the guest payload.
        is_running: Decides from the same payload whether the guest is running.

    Returns:
        A value function returning ``None`` for a guest that is not running.

    """

    def _value(guest: dict[str, Any]) -> StateType:
        return value_fn(guest) if is_running(guest) else None

    return _value
