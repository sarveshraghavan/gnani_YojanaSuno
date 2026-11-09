"""Normalized, explicit aliases for spoken PM-KUSUM B/C answers."""
from __future__ import annotations

import re
import unicodedata


def normalize_answer(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    chars = [char if char.isspace() or unicodedata.category(char)[0] in {"L", "M", "N"} else " "
             for char in normalized]
    return re.sub(r"\s+", " ", "".join(chars)).strip()


PUMP_COMPONENT_ALIASES = {
    **{normalize_answer(alias): "B" for alias in (
        "b", "bee", "be", "component b", "b component",
        "बी", "बी घटक", "बी पंप",
        "பி", "பீ", "பி பிரிவு", "பீ பிரிவு", "பி கூறு", "பீ கூறு",
        "బి", "బీ", "బి భాగం", "బీ భాగం", "బి పంపు", "బీ పంపు",
    )},
    **{normalize_answer(alias): "C" for alias in (
        "c", "see", "sea", "component c", "c component",
        "सी", "सी घटक", "सी पंप",
        "சி", "சீ", "சி பிரிவு", "சீ பிரிவு", "சி கூறு", "சீ கூறு",
        "సి", "సీ", "సి భాగం", "సీ భాగం", "సి పంపు", "సీ పంపు",
    )},
}


def parse_pump_component(text: str) -> str | None:
    """Return B/C only for a complete known spoken alias; never use fuzzy matches."""
    return PUMP_COMPONENT_ALIASES.get(normalize_answer(text))


def as_grid_connection(component: str) -> bool:
    """Component C is the grid-connected pump path; B is the standalone path."""
    return component == "C"
