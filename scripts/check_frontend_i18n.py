"""Resolve the landing page's translation keys and report untranslated text."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.tests.test_i18n_complete import LANGS, landing_tables, ALLOWED_ENGLISH  # noqa: E402

HTML = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
KEYS = set()
for attr in ("data-i", "data-ip", "data-ia", "data-im", "data-ititle", "data-prompt-key"):
    KEYS.update(re.findall(rf'{attr}="([^"]+)"', HTML))


def remaining_english(text: str) -> list[str]:
    residue = text
    for word in ALLOWED_ENGLISH:
        residue = residue.replace(word, "")
    return sorted(set(re.findall(r"[A-Za-z]{3,}(?:-[A-Za-z]+)*", residue)))


def main() -> int:
    tables = landing_tables()
    errors = []
    for lang in ("hi", "ta", "te", "en"):
        resolved = {key: tables[lang].get(key) for key in sorted(KEYS)}
        missing = [key for key, value in resolved.items() if value is None]
        leftovers = [(key, remaining_english(value)) for key, value in resolved.items() if value and lang != "en" and remaining_english(value)]
        print(f"{lang}: resolved {len(resolved) - len(missing)}/{len(KEYS)} page strings")
        if missing:
            errors.append(f"{lang}: missing keys {missing}")
        if leftovers:
            errors.extend(f"{lang}: {key}: untranslated English {words}" for key, words in leftovers)
    if errors:
        print("Untranslated or missing strings:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("No English leftovers outside the proper-name allow-list.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
