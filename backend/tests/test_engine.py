from app.eligibility.engine import _mapped_rule_slots, evaluate, load_schemes
from app.eligibility.models import Condition, Scheme
from datetime import date, timedelta


def test_pm_kisan_cases():
    scheme = next(item for item in load_schemes("schemes") if item.id == "pm_kisan")
    eligible = {
        "owns_land": True,
        "is_institutional_holder": False,
        "pays_income_tax": False,
    }
    assert evaluate(scheme, eligible).status == "eligible"
    assert evaluate(scheme, {**eligible, "pays_income_tax": True}).status == "not_eligible"
    assert evaluate(scheme, {"owns_land": True}).status == "need_more_info"


def test_known_failure_beats_missing_information():
    scheme = next(item for item in load_schemes("schemes") if item.id == "pm_kisan")
    result = evaluate(scheme, {"owns_land": False})
    assert result.status == "not_eligible"
    assert result.missing_slots == ["is_institutional_holder", "pays_income_tax"]


def test_unknown_values_are_reported_as_missing():
    scheme = next(item for item in load_schemes("schemes") if item.id == "pm_kisan")
    result = evaluate(scheme, {
        "owns_land": "unsure",
        "is_institutional_holder": False,
        "pays_income_tax": False,
    })
    assert result.status == "need_more_info"
    assert result.missing_slots == ["owns_land"]


def test_rule_operators():
    scheme = Scheme(
        id="operators",
        name="Operator fixture",
        version="1",
        source_url="https://example.test",
        last_verified="2026-11-06",
        benefit="test",
        required_slots=["equal", "not_equal", "greater", "at_least", "less", "at_most", "member"],
        rules=[
            Condition(slot="equal", op="eq", value="yes"),
            Condition(slot="not_equal", op="ne", value=0),
            Condition(slot="greater", op="gt", value=2),
            Condition(slot="at_least", op="gte", value=3),
            Condition(slot="less", op="lt", value=5),
            Condition(slot="at_most", op="lte", value=4),
            Condition(slot="member", op="in", value=["B", "C"]),
        ],
    )
    result = evaluate(scheme, {
        "equal": "yes", "not_equal": 1, "greater": 3,
        "at_least": 3, "less": 4, "at_most": 4, "member": "C",
    })
    assert result.status == "eligible"


def test_scheme_slot_mapping_derives_component_inside_the_rules_engine():
    scheme = Scheme(
        id="kusum-grid-mapping", name="PM-KUSUM mapping fixture", version="1",
        source_url="https://example.test", last_verified="2026-11-06", benefit="test",
        required_slots=["has_grid_connected_pump"],
        slot_mappings={"has_grid_connected_pump": {
            True: {"component": "C"}, False: {"component": "B"}}},
        rules=[Condition(slot="component", op="eq", value="C")],
    )
    assert evaluate(scheme, {"has_grid_connected_pump": True}).status == "eligible"
    assert evaluate(scheme, {"has_grid_connected_pump": False}).status == "not_eligible"
    assert evaluate(scheme, {}).status == "need_more_info"


def test_pm_kusum_grid_mapping_and_explicit_component_precedence():
    scheme = next(item for item in load_schemes() if item.id == "pm_kusum")
    assert scheme.version == "2026-11-demo-2"
    assert _mapped_rule_slots(scheme, {"has_grid_connected_pump": True})["component"] == "C"
    assert _mapped_rule_slots(scheme, {"has_grid_connected_pump": False})["component"] == "B"
    assert _mapped_rule_slots(scheme, {"has_grid_connected_pump": True, "component": "B"})["component"] == "B"
    base = {"state": "Tamil Nadu", "state_application_open": True, "state_requirements_confirmed": True}
    assert evaluate(scheme, {**base, "has_grid_connected_pump": True}).status == "eligible"
    assert evaluate(scheme, {**base, "has_grid_connected_pump": False}).status == "eligible"
    assert evaluate(scheme, base).status == "need_more_info"
    # Older clients may still send component directly; it answers the new slot.
    assert evaluate(scheme, {**base, "component": "B"}).status == "eligible"
    # Explicit component input wins even when it conflicts with grid-derived C.
    explicit_b = Scheme(
        id="explicit-b", name="Explicit B", version="1", source_url="https://example.test",
        last_verified="2026-11-08", benefit="test", required_slots=["has_grid_connected_pump"],
        slot_mappings={"has_grid_connected_pump": {True: {"component": "C"}, False: {"component": "B"}}},
        rules=[Condition(slot="component", op="eq", value="B")],
    )
    assert evaluate(explicit_b, {"has_grid_connected_pump": True, "component": "B"}).status == "eligible"


def test_pm_kusum_grid_and_legacy_component_screens():
    scheme = next(item for item in load_schemes() if item.id == "pm_kusum")
    base = {"state": "Tamil Nadu", "state_application_open": True, "state_requirements_confirmed": True}
    # For the real registry, both B and C satisfy the component rule; check the
    # resolved rule input separately above and ensure unanswered stays missing.
    assert evaluate(scheme, {**base, "has_grid_connected_pump": True}).missing_slots == []
    assert evaluate(scheme, {**base, "has_grid_connected_pump": False}).missing_slots == []
    missing = evaluate(scheme, base)
    assert missing.status == "need_more_info"
    assert missing.missing_slots == ["has_grid_connected_pump"]
    assert evaluate(scheme, {**base, "component": "C"}).missing_slots == []


def test_registry_loads_all_versioned_schemes():
    schemes = load_schemes("schemes")
    assert {item.id for item in schemes} == {"pm_kisan", "pmfby", "pm_kusum"}
    assert all(item.version and item.source_url and item.last_verified for item in schemes)
    pm_kisan = next(item for item in schemes if item.id == "pm_kisan")
    assert any("Other excluded family categories" in item for item in pm_kisan.not_checked)


def test_verified_scheme_cannot_be_older_than_90_days():
    today = date.today()
    for scheme in load_schemes():
        if scheme.verified:
            verified_on = date.fromisoformat(scheme.last_verified)
            assert today - verified_on <= timedelta(days=90), scheme.id

