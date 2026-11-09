import operator
from pathlib import Path
from typing import Any

import yaml

from .models import Condition, Result, Scheme

OPS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
    "in": lambda value, options: value in options,
}

DEFAULT_SCHEMES_DIR = Path(__file__).resolve().parents[2] / "schemes"
UNKNOWN_VALUES = {"", "unsure", "unknown", "not sure", "don't know"}


def load_schemes(folder: str | Path | None = None) -> list[Scheme]:
    """Load and validate scheme YAML. Defaults to backend/schemes regardless of cwd."""
    scheme_dir = Path(folder) if folder is not None else DEFAULT_SCHEMES_DIR
    schemes = []
    for path in sorted(scheme_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data is not None:
            schemes.append(Scheme.model_validate(data))
    return schemes


def _unknown(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip().casefold() in UNKNOWN_VALUES)


def _passes(condition: Condition, value: Any) -> bool:
    try:
        return bool(OPS[condition.op](value, condition.value))
    except (TypeError, ValueError):
        # Malformed or incomparable user data must never produce a positive match.
        return False


def _mapped_rule_slots(scheme: Scheme, slots: dict[str, Any]) -> dict[str, Any]:
    """Apply explicit scheme-data slot mappings before deterministic rules."""
    mapped = dict(slots)
    for source_slot, cases in scheme.slot_mappings.items():
        value = slots.get(source_slot)
        # An explicitly supplied target (legacy `component`) always wins over
        # the derived mapping. This preserves older clients and user corrections.
        targets = {target for mapping in cases.values() for target in mapping}
        explicit_targets = targets.intersection(slots)
        if explicit_targets:
            continue
        if type(value) is bool and value in cases:
            mapped.update(cases[value])
    return mapped


def _required_slots_view(scheme: Scheme, slots: dict[str, Any]) -> dict[str, Any]:
    """Treat legacy B/C input as an answer to the replacement grid slot."""
    normalized = dict(slots)
    if _unknown(normalized.get("has_grid_connected_pump")):
        component = normalized.get("component")
        if component in {"B", "C"}:
            normalized["has_grid_connected_pump"] = component == "C"
    return normalized


def evaluate(scheme: Scheme, slots: dict[str, Any]) -> Result:
    required_slots = _required_slots_view(scheme, slots)
    missing = [slot for slot in scheme.required_slots if _unknown(required_slots.get(slot))]
    rule_slots = _mapped_rule_slots(scheme, slots)
    failed = [
        condition
        for condition in scheme.rules
        if not _unknown(rule_slots.get(condition.slot))
        and not _passes(condition, rule_slots[condition.slot])
    ]
    # A known failure beats missing info; avoid asking for facts that cannot change the result.
    if failed:
        status = "not_eligible"
    elif missing:
        status = "need_more_info"
    else:
        status = "eligible"
    return Result(
        scheme_id=scheme.id,
        scheme_name=scheme.name,
        status=status,
        missing_slots=missing,
        failed_rules=failed,
        scheme_version=scheme.version,
    )


def check_all(slots: dict[str, Any], schemes: list[Scheme]) -> list[Result]:
    return [evaluate(scheme, slots) for scheme in schemes]
