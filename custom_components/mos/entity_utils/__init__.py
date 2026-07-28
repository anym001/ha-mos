"""Entity utilities package for mos."""

from .dynamic_entities import async_setup_dynamic_entities
from .permissions import has_read_access, has_write_access

__all__ = [
    "async_setup_dynamic_entities",
    "has_read_access",
    "has_write_access",
]
