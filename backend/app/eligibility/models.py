from typing import Any, Literal

from pydantic import BaseModel, Field


class Condition(BaseModel):
    slot: str
    op: Literal["eq", "ne", "gt", "gte", "lt", "lte", "in"]
    value: Any
    source_ref: str = ""


class Scheme(BaseModel):
    id: str
    name: str
    version: str
    source_url: str
    sources: list[str] = Field(default_factory=list)
    last_verified: str
    verified: bool = False
    benefit: str
    required_slots: list[str]
    rules: list[Condition]
    slot_mappings: dict[str, dict[bool, dict[str, Any]]] = Field(default_factory=dict)
    not_checked: list[str] = Field(default_factory=list)
    next_steps: dict[str, Any] = Field(default_factory=dict)


class Result(BaseModel):
    scheme_id: str
    scheme_name: str
    status: Literal["eligible", "not_eligible", "need_more_info"]
    missing_slots: list[str] = Field(default_factory=list)
    failed_rules: list[Condition] = Field(default_factory=list)
    scheme_version: str
