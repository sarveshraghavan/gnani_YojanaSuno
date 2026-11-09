"""Conservative Evon slot extraction. This module never evaluates eligibility."""
from __future__ import annotations

import json
from typing import Any

import httpx

from ..config import settings

BOOLEAN_SLOTS = {"owns_land", "is_institutional_holder", "pays_income_tax",
                 "area_notified", "state_application_open", "state_requirements_confirmed",
                 "has_grid_connected_pump", "micro_irrigation_interest"}
STRING_SLOTS = {"state", "district", "crop", "season"}
NUMERIC_SLOTS = {"farmer_age", "cultivable_land_hectares"}
ENUM_SLOTS = {"kcc_farmer_category": {"owner_cultivator", "tenant_or_sharecropper", "farmer_group"}}
ALLOWED_SLOTS = BOOLEAN_SLOTS | STRING_SLOTS | NUMERIC_SLOTS | set(ENUM_SLOTS) | {"component", "water_source"}
WATER_SOURCES = {"borewell", "canal", "rain", "well", "other"}
COMPONENTS = {"B", "C"}


def validate_slots(value: Any) -> dict[str, Any]:
    """Keep only known fields with the exact expected type/value domain."""
    if not isinstance(value, dict):
        return {}
    cleaned: dict[str, Any] = {}
    for key, item in value.items():
        if key not in ALLOWED_SLOTS or item is None:
            continue
        if key in BOOLEAN_SLOTS and type(item) is bool:
            cleaned[key] = item
        elif key in STRING_SLOTS and isinstance(item, str) and item.strip():
            normalized = item.strip()[:120]
            if key == "season":
                normalized = normalized.casefold()
                if normalized not in {"kharif", "rabi"}:
                    continue
            cleaned[key] = normalized
        elif key == "component" and isinstance(item, str) and item.upper() in COMPONENTS:
            cleaned[key] = item.upper()
        elif key == "water_source" and isinstance(item, str) and item.casefold() in WATER_SOURCES:
            cleaned[key] = item.casefold()
        elif key in NUMERIC_SLOTS and type(item) in {int, float} and 0 <= item <= (120 if key == "farmer_age" else 10000):
            cleaned[key] = item
        elif key in ENUM_SLOTS and isinstance(item, str) and item.casefold() in ENUM_SLOTS[key]:
            cleaned[key] = item.casefold()
    return cleaned


def parse_json_slots(content: str) -> dict[str, Any]:
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end < start:
        return {}
    try:
        parsed = json.loads(content[start:end + 1])
    except (json.JSONDecodeError, TypeError):
        return {}
    return validate_slots(parsed)


class MockExtractor:
    is_mock = True

    def extract(self, text: str, language: str, known: dict[str, Any],
                pending_slot: str | None = None) -> dict[str, Any]:
        return {}


class EvonExtractor:
    is_mock = False

    def __init__(self, base_url: str, model: str, api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key.strip()
        self.last_error: str | None = None

    def _url(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        if self.base_url.endswith("/v1"):
            return self.base_url + "/chat/completions"
        return self.base_url + "/v1/chat/completions"

    def extract(self, text: str, language: str, known: dict[str, Any],
                pending_slot: str | None = None) -> dict[str, Any]:
        schema = {
            "owns_land": "boolean|null", "is_institutional_holder": "boolean|null",
            "pays_income_tax": "boolean|null", "state": "string|null",
            "district": "string|null", "crop": "string|null", "season": "string|null",
            "area_notified": "boolean|null", "component": "B|C|null",
            "state_application_open": "boolean|null", "state_requirements_confirmed": "boolean|null",
            "has_grid_connected_pump": "boolean|null",
            "farmer_age": "number|null", "cultivable_land_hectares": "number|null",
            "kcc_farmer_category": "owner_cultivator|tenant_or_sharecropper|farmer_group|null",
            "micro_irrigation_interest": "boolean|null",
            "water_source": "borewell|canal|rain|well|other|null",
        }
        system = (
            "Extract explicitly stated farm facts as one JSON object and no other text. "
            "Never guess; use null when a fact is not stated. Use native-script understanding "
            "for the farmer's language, but return normalized state/crop strings in the source script. "
            "Do not decide scheme eligibility. Every key must follow this schema: " + json.dumps(schema)
        )
        user = (f"Farmer language: {language}. Pending question slot: {pending_slot}. "
                f"Existing confirmed facts: {json.dumps(known, ensure_ascii=False)}. "
                f"Farmer utterance: {text}")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model, "temperature": 0.6, "top_p": 0.95,
            "max_tokens": 300,
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
        }
        try:
            response = httpx.post(self._url(), headers=headers, json=payload,
                                  timeout=httpx.Timeout(20.0, connect=4.0))
            if response.status_code >= 400:
                self.last_error = f"HTTP {response.status_code}"
                return {}
            content = response.json()["choices"][0]["message"]["content"]
            result = parse_json_slots(content)
            self.last_error = None
            return result
        except Exception as exc:
            # Caller falls back to local conservative extraction; never log transcript or key.
            self.last_error = type(exc).__name__
            return {}


def get_extractor():
    if settings.use_mock_llm or not settings.evon_base_url:
        return MockExtractor()
    return EvonExtractor(settings.evon_base_url, settings.evon_model, settings.evon_api_key)
