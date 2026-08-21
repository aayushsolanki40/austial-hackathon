"""Minimal i18n loader for api.swadely.com.

Per the workspace convention: user-facing/business strings live in i18n JSON
locale files, not inline in source. As the app grows into multiple domain
modules (payments, tokenization, KYC, wallet, compliance-reporting), a single
flat JSON per locale becomes unwieldy, so strings are split module-wise: one
JSON file per app module, per locale, under
``src/i18n/locales/<locale>/<module>.json`` (e.g. ``locales/en/app.json``,
``locales/en/health.json``).

Each module file's top-level keys (and, for one level of nesting, their
sub-keys) are merged into a single lookup table namespaced by
``<module>.<key>`` (and ``<module>.<key>.<subkey>`` for nested keys) -- e.g.
file ``app.json`` key ``"title"`` becomes lookup key ``"app.title"``, and file
``health.json`` key ``"check"`` -> ``"database_label"`` becomes lookup key
``"health.check.database_label"``. This keeps the external lookup key format
(``"app.title"``, ``"health.protected.message"``) unchanged for call sites,
which look strings up via ``translate(key)`` instead of importing raw
literals.

Kept intentionally simple: no pluralization/interpolation machinery, since
nothing in this project's strings needs it yet. Adding another locale is just
"drop in a new ``locales/<locale>/`` directory with one JSON file per module
-- ``translate()`` picks it up automatically the first time that locale is
requested.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

DEFAULT_LOCALE = "en"

_LOCALES_DIR = Path(__file__).parent / "locales"


@cache
def _load_locale(locale: str) -> dict[str, str]:
    locale_dir = _LOCALES_DIR / locale
    if not locale_dir.is_dir():
        raise FileNotFoundError(f"No i18n locale directory for {locale!r} at {locale_dir}")

    strings: dict[str, str] = {}
    for module_file in sorted(locale_dir.glob("*.json")):
        module = module_file.stem
        module_strings = json.loads(module_file.read_text(encoding="utf-8"))
        for key, value in module_strings.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    strings[f"{module}.{key}.{sub_key}"] = sub_value
            else:
                strings[f"{module}.{key}"] = value
    return strings


def translate(key: str, locale: str = DEFAULT_LOCALE) -> str:
    """Look up ``key`` in the given ``locale``'s JSON file (default locale otherwise)."""
    strings = _load_locale(locale)
    if key not in strings:
        raise KeyError(f"Missing i18n key {key!r} for locale {locale!r}")
    return strings[key]


# Short alias, mirroring the common `t()` i18n convention.
t = translate
