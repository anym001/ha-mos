"""Tests that every translation key referenced from code exists in translations/en.json."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
from typing import Any

INTEGRATION_PATH = Path(__file__).resolve().parents[1] / "custom_components" / "mos"
TRANSLATION_KEY_PATTERN = re.compile(r'translation_key\s*=\s*"([a-z0-9_]+)"')

# Home Assistant exception classes whose message is shown to the end user and
# therefore must be translated, never a hardcoded string. Deliberately excludes
# this integration's own MOSApiClient* exceptions: those are internal
# transport-level errors, always caught and re-raised as one of these
# translatable types before reaching the user (see api/__init__.py's exception
# mapping docstring).
TRANSLATABLE_EXCEPTIONS = frozenset(
    {
        "HomeAssistantError",
        "ConfigEntryAuthFailed",
        "ConfigEntryNotReady",
        "ConfigEntryError",
        "UpdateFailed",
        "ServiceValidationError",
    }
)


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


def _key_paths(node: Any, prefix: str = "") -> set[str]:
    """Return the dotted path of every leaf in the translation tree.

    Paths rather than bare key names, unlike `_collect_keys`: a string that ended
    up under the wrong parent - `reconfigure.data.ssl` instead of
    `reconfigure.data_description.ssl` - has the right name and the wrong home,
    and only the path shows it.
    """
    if not isinstance(node, dict):
        return {prefix}
    return {path for key, value in node.items() for path in _key_paths(value, f"{prefix}.{key}" if prefix else key)}


def test_every_language_carries_the_same_keys() -> None:
    """Every translation file has exactly the key set of en.json.

    Home Assistant falls back to English for a key a language file is missing -
    no error, no log line, the field simply renders in English. Nothing else
    here looks at anything but en.json, so a string added to one file and
    forgotten in the other would be invisible until a user noticed it.
    """
    translations_path = INTEGRATION_PATH / "translations"
    expected = _key_paths(json.loads((translations_path / "en.json").read_text(encoding="utf-8")))

    for path in sorted(translations_path.glob("*.json")):
        if path.name == "en.json":
            continue
        actual = _key_paths(json.loads(path.read_text(encoding="utf-8")))
        assert not expected - actual, f"{path.name} is missing keys present in en.json: {sorted(expected - actual)}"
        assert not actual - expected, f"{path.name} has keys en.json does not: {sorted(actual - expected)}"


def _exception_class_name(func: ast.expr) -> str | None:
    """Return the raised exception's class name, for both `Foo(...)` and `module.Foo(...)` call forms."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _untranslated_raises(path: Path) -> list[str]:
    """Return one message per `raise` of a translatable exception missing translation_domain/translation_key."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
            continue
        name = _exception_class_name(node.exc.func)
        if name not in TRANSLATABLE_EXCEPTIONS:
            continue
        keyword_names = {kw.arg for kw in node.exc.keywords}
        if not {"translation_domain", "translation_key"} <= keyword_names:
            problems.append(
                f"{path.relative_to(INTEGRATION_PATH.parent)}:{node.lineno}: {name}(...) is missing translation_domain/translation_key"
            )
    return problems


def test_translatable_exceptions_use_translation_key() -> None:
    """
    Every user-facing HA exception is raised with translation_domain/translation_key, never a bare string.

    A hardcoded message still works at runtime - Home Assistant just displays
    the raw text - so nothing else catches the regression of someone adding a
    new HomeAssistantError/UpdateFailed/... with a plain string instead of
    wiring it through translations/en.json (and now de.json).
    """
    problems: list[str] = []
    for path in sorted(INTEGRATION_PATH.rglob("*.py")):
        problems.extend(_untranslated_raises(path))

    assert not problems, "\n".join(problems)
