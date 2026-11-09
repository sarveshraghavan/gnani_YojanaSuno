from app.dialogue.next_question import next_question, next_slot
from app.eligibility.engine import check_all, load_schemes


def test_next_question_selects_most_shared_missing_slot():
    results = check_all({}, load_schemes("schemes"))
    assert next_slot(results) == "owns_land"
    assert next_question(results, "en-IN") == "Is the farmland in your own name?"


def test_next_question_uses_requested_language_and_falls_back_to_english():
    results = check_all({}, load_schemes("schemes"))
    assert next_question(results, "ta-IN") == "விவசாய நிலம் உங்கள் பெயரில் உள்ளதா?"
    assert next_question(results, "kn-IN") == "Is the farmland in your own name?"


def test_no_followup_when_all_required_slots_are_known():
    slots = {
        "owns_land": True,
        "is_institutional_holder": False,
        "pays_income_tax": False,
        "state": "Tamil Nadu",
        "district": "Madurai",
        "crop": "rice",
        "season": "kharif",
        "area_notified": True,
        "component": "B",
        "state_application_open": True,
        "state_requirements_confirmed": True,
    }
    results = check_all(slots, load_schemes("schemes"))
    assert next_question(results) is None


def test_new_draft_slots_have_questions_in_all_supported_languages():
    from app.dialogue.next_question import QUESTIONS
    for slot in ("farmer_age", "cultivable_land_hectares", "kcc_farmer_category", "micro_irrigation_interest"):
        assert set(QUESTIONS[slot]) == {"en", "hi", "ta", "te"}


def test_draft_slot_extractors_validate_numeric_enum_and_boolean_answers():
    from app.dialogue.extractor import validate_slots
    assert validate_slots({"farmer_age": 36, "cultivable_land_hectares": 1.5,
        "kcc_farmer_category": "tenant_or_sharecropper", "micro_irrigation_interest": True}) == {
        "farmer_age": 36, "cultivable_land_hectares": 1.5,
        "kcc_farmer_category": "tenant_or_sharecropper", "micro_irrigation_interest": True}


def test_session_question_budget_is_six_and_per_slot_limit_is_two():
    from uuid import uuid4
    from app.main import SESSIONS, reserve_slot_question
    session_id = uuid4()
    SESSIONS.clear()
    assert reserve_slot_question(session_id, "owns_land")
    assert reserve_slot_question(session_id, "owns_land")
    assert not reserve_slot_question(session_id, "owns_land")
    for slot in ("state", "crop", "season", "has_grid_connected_pump"):
        assert reserve_slot_question(session_id, slot)
    assert not reserve_slot_question(session_id, "pays_income_tax")
    assert SESSIONS[str(session_id)]["questions_asked"] == 6
