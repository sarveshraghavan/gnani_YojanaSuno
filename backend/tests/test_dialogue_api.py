from app.main import ChatRequest, EligibilityRequest, SESSIONS, chat, check_eligibility
from uuid import UUID


def test_chat_merges_short_answers_and_check_returns_next_question(monkeypatch):
    monkeypatch.delenv("EVON_BASE_URL", raising=False)
    SESSIONS.clear()
    session_id = UUID("11111111-1111-4111-8111-111111111111")

    first_turn = chat(ChatRequest(
        text="Yes",
        known_slots={
            "owns_land": True, "state": "Tamil Nadu", "district": "Madurai",
            "crop": "rice", "season": "kharif", "area_notified": True,
            "component": "B", "state_application_open": True,
            "state_requirements_confirmed": True,
        },
        pending_slot="is_institutional_holder",
        session_id=session_id,
    ))
    assert first_turn["slots"]["owns_land"] is True
    assert first_turn["slots"]["is_institutional_holder"] is True

    second_turn = chat(ChatRequest(
        text="No",
        pending_slot="is_institutional_holder",
        session_id=session_id,
    ))
    assert second_turn["slots"]["owns_land"] is True
    assert second_turn["slots"]["is_institutional_holder"] is False

    checked = check_eligibility(EligibilityRequest(
        session_id=session_id,
        language="en-IN",
    ))
    assert checked["slots"]["owns_land"] is True
    assert checked["slots"]["is_institutional_holder"] is False
    assert checked["next_slot"] == "pays_income_tax"
    assert checked["next_question"] == "Did anyone in your farmer family pay income tax last year?"
    assert checked["results"] == []

    tax_turn = chat(ChatRequest(text="No", pending_slot="pays_income_tax", session_id=session_id))
    assert tax_turn["slots"]["pays_income_tax"] is False
    confirmation = check_eligibility(EligibilityRequest(session_id=session_id, language="en-IN"))
    assert confirmation["next_slot"] == "__confirm__"
    assert "Is that right?" in confirmation["next_question"]

    declined = chat(ChatRequest(text="No", pending_slot="__confirm__", session_id=session_id))
    assert declined["stage"] == "fix_detail"
    assert declined["pending_slot"] == "__fix_slot__"
    slot_choice = chat(ChatRequest(text="crop", pending_slot="__fix_slot__", session_id=session_id))
    assert slot_choice["stage"] == "correction"
    assert slot_choice["pending_slot"] == "crop"
    corrected = chat(ChatRequest(text="wheat", pending_slot="crop", session_id=session_id))
    assert corrected["slots"]["crop"] == "wheat"
    confirmation = check_eligibility(EligibilityRequest(session_id=session_id, language="en-IN"))
    assert confirmation["next_slot"] == "__confirm__"

    confirmed = chat(ChatRequest(text="Yes", pending_slot="__confirm__", session_id=session_id))
    assert confirmed["confirmed"] is True
    final = check_eligibility(EligibilityRequest(session_id=session_id, language="en-IN", confirmed=True))
    assert final["stage"] == "complete"
    assert final["scope"].startswith("Preliminary screening only")
    assert all("not_checked" in result for result in final["results"])
