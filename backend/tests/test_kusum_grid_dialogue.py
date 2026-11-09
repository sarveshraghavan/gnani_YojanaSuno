from __future__ import annotations

from uuid import uuid4

import pytest

from app.dialogue.component_aliases import PUMP_COMPONENT_ALIASES, parse_pump_component
from app.dialogue.extractor import MockExtractor
from app.main import (
    ChatRequest, EligibilityRequest, SESSIONS, check_eligibility, chat, extract_slots,
    question_for_slot, short_answer,
)


LOCALES = ("en-IN", "hi-IN", "ta-IN", "te-IN")
ANSWERS = (
    ("B", False), ("C", True), ("பி", False), ("சி", True),
    ("பீ", False), ("சீ", True), ("bee", False), ("see", True),
    ("பி பிரிவு", False), ("बी", False), ("సి", True),
)


@pytest.mark.parametrize("language", LOCALES)
@pytest.mark.parametrize("answer,expected", ANSWERS)
def test_component_answers_normalize_to_the_grid_connection_slot(language, answer, expected, monkeypatch):
    # The locale is included because all supported speech locales must accept
    # the same common B/C spellings, including code-mixed answers.
    import app.main as main
    monkeypatch.setattr(main, "get_extractor", lambda: MockExtractor())
    slots, _, should_reask = extract_slots(answer, language, {}, "component")
    assert slots.get("has_grid_connected_pump") is expected, f"{language} answer {answer!r} was not normalized"
    assert slots.get("component") == ("C" if expected else "B")
    assert not should_reask


@pytest.mark.parametrize("answer,expected", ANSWERS)
def test_alias_table_maps_spoken_forms_to_component(answer, expected):
    assert parse_pump_component(answer) == ("C" if expected else "B")


@pytest.mark.parametrize("utterance,expected", [
    ("no grid connection", False), ("बिजली का कनेक्शन नहीं है", False),
    ("மின் இணைப்பு இல்லை", False), ("విద్యుత్ కనెక్షన్ ఉంది", True),
])
def test_grid_status_can_be_extracted_without_a_pending_question(utterance, expected):
    from app.main import local_extract
    assert local_extract(utterance)["has_grid_connected_pump"] is expected


@pytest.mark.parametrize("language,question", [
    ("en-IN", "Does your pump have an electricity (grid) connection?"),
    ("hi-IN", "क्या आपके पंप में बिजली (ग्रिड) का कनेक्शन है?"),
    ("ta-IN", "உங்கள் பம்ப்புக்கு மின் இணைப்பு உள்ளதா?"),
    ("te-IN", "మీ పంపుకు విద్యుత్ (గ్రిడ్) కనెక్షన్ ఉందా?"),
])
def test_plain_grid_connection_question_is_localized(language, question):
    assert question_for_slot("has_grid_connected_pump", language) == question


@pytest.mark.parametrize("slot,translations", [
    ("state_application_open", {
        "en-IN": "Has the government in your state said farmers can apply now?",
        "hi-IN": "क्या आपके राज्य की सरकार ने बताया है कि किसान अभी आवेदन कर सकते हैं?",
        "ta-IN": "உங்கள் மாநில அரசு, விவசாயிகள் இப்போது விண்ணப்பிக்கலாம் என்று தெரிவித்துள்ளதா?",
        "te-IN": "మీ రాష్ట్ర ప్రభుత్వం రైతులు ఇప్పుడు దరఖాస్తు చేసుకోవచ్చని తెలిపిందా?",
    }),
    ("state_requirements_confirmed", {
        "en-IN": "Has the state agriculture office checked that your pump meets the local rules?",
        "hi-IN": "क्या राज्य के कृषि कार्यालय ने जाँचा है कि आपका पंप वहाँ के नियमों के अनुसार है?",
        "ta-IN": "மாநில வேளாண்மை அலுவலகம் உங்கள் பம்ப் உள்ளூர் விதிகளுக்கு ஏற்ப உள்ளதா என்று சரிபார்த்துள்ளதா?",
        "te-IN": "రాష్ట్ర వ్యవసాయ కార్యాలయం మీ పంపు అక్కడి నిబంధనలకు సరిపోతుందో చూసిందా?",
    }),
])
def test_state_specific_questions_are_plainly_worded_in_four_languages(slot, translations):
    for language, text in translations.items():
        assert question_for_slot(slot, language) == text


@pytest.mark.parametrize("answer,expected", [("yes", True), ("no", False), ("ஆம்", True), ("இல்லை", False), ("అవును", True), ("లేదు", False), ("हाँ", True), ("नहीं", False)])
def test_boolean_slot_accepts_localized_yes_no(answer, expected):
    assert short_answer(answer, "has_grid_connected_pump") == {
        "has_grid_connected_pump": expected
    }


@pytest.mark.parametrize("language,answer,expected", [
    ("en-IN", "Yes", True), ("hi-IN", "हाँ", True),
    ("ta-IN", "ஆம்", True), ("te-IN", "కాదు", False),
])
def test_chat_fills_grid_connection_slot_in_each_language(language, answer, expected, monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "get_extractor", lambda: MockExtractor())
    response = chat(ChatRequest(text=answer, language=language,
        session_id=uuid4(), pending_slot="has_grid_connected_pump"))
    assert response["slots"]["has_grid_connected_pump"] is expected
    assert response.get("stage") != "clarify"


def test_component_slot_stops_after_two_failed_answers_and_surfaces_incomplete_result(monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "get_extractor", lambda: MockExtractor())
    SESSIONS.clear()
    session_id = uuid4()
    complete_other_slots = {
        "owns_land": True, "is_institutional_holder": False, "pays_income_tax": False,
        "state": "Tamil Nadu", "district": "Madurai", "crop": "rice",
        "season": "kharif", "area_notified": True,
        "state_application_open": True, "state_requirements_confirmed": True,
    }
    first = check_eligibility(EligibilityRequest(slots=complete_other_slots, session_id=session_id, language="en-IN"))
    assert first["next_slot"] == "has_grid_connected_pump"
    assert first["next_question"].endswith(question_for_slot("has_grid_connected_pump", "en-IN"))

    first_failure = chat(ChatRequest(text="I don't know", language="en-IN", known_slots=complete_other_slots,
        session_id=session_id, pending_slot="has_grid_connected_pump"))
    assert first_failure["stage"] == "clarify"
    assert first_failure["next_question"].endswith(question_for_slot("has_grid_connected_pump", "en-IN"))

    second_failure = chat(ChatRequest(text="still not sure", language="en-IN", known_slots=complete_other_slots,
        session_id=session_id, pending_slot="has_grid_connected_pump"))
    assert second_failure["stage"] == "slot_abandoned"
    assert second_failure["next_question"] is None

    final = check_eligibility(EligibilityRequest(slots=complete_other_slots, session_id=session_id, language="en-IN"))
    assert final["stage"] == "incomplete"
    assert final["next_slot"] is None
    kusum = next(item for item in final["results"] if item["scheme_id"] == "pm_kusum")
    assert kusum["status"] == "need_more_info"
    assert kusum["missing_slots"] == ["has_grid_connected_pump"]
    assert kusum["not_checked_slots"] == ["has_grid_connected_pump"]
    assert "has_grid_connected_pump" in kusum["not_checked"]
    assert "1551" in final["reply"]
