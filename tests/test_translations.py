"""Tests that every translation key referenced from code exists in translations/en.json."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

INTEGRATION_PATH = Path(__file__).resolve().parents[1] / "custom_components" / "mos"
TRANSLATION_KEY_PATTERN = re.compile(r'translation_key\s*=\s*"([a-z0-9_]+)"')


def _collect_keys(node: Any) -> set[str]:
    """Return every mapping key appearing anywhere in the translation tree."""
    if not isinstance(node, dict):
        return set()
    keys: set[str] = set()
    for key, value in node.items():
        keys.add(key)
        keys |= _collect_keys(value)
    return keys


def test_referenced_translation_keys_exist() -> None:
    """Every ``translation_key=`` used in the integration resolves in en.json.

    A missing key is invisible in unit tests - Home Assistant simply renders the
    raw key to the user - so it is checked statically here. Catches the easy
    mistake of adding a new exception/entity key in Python without adding the
    matching translation string.
    """
    translations = json.loads((INTEGRATION_PATH / "translations" / "en.json").read_text(encoding="utf-8"))
    available = _collect_keys(translations)

    referenced: set[str] = set()
    for path in sorted(INTEGRATION_PATH.rglob("*.py")):
        referenced |= set(TRANSLATION_KEY_PATTERN.findall(path.read_text(encoding="utf-8")))

    assert referenced, "no translation keys found - the scan pattern is probably wrong"
    missing = sorted(referenced - available)
    assert not missing, f"translation keys used in code but missing from translations/en.json: {missing}"
