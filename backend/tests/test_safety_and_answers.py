from uuid import UUID

from app.main import (
    SESSION_TTL_SECONDS,
    SESSIONS,
    clean_slot_updates,
    merge_session,
    purge_expired_sessions,
    redact_sensitive_numbers,
    short_answer,
)


def test_regional_yes_no_and_romanized_hindi():
    assert short_answer("haan", "owns_land") == {"owns_land": True}
    assert short_answer("ji haan", "owns_land") == {"owns_land": True}
    assert short_answer("nahi", "owns_land") == {"owns_land": False}
    assert short_answer("nahin", "owns_land") == {"owns_land": False}
    assert short_answer("ஆம்", "area_notified") == {"area_notified": True}
    assert short_answer("இல்லை", "area_notified") == {"area_notified": False}
    assert short_answer("అవును", "state_application_open") == {"state_application_open": True}
    assert short_answer("కాదు", "state_application_open") == {"state_application_open": False}
    assert short_answer("లేదు", "state_application_open") == {"state_application_open": False}


def test_negation_and_family_tax_answers_are_not_flipped():
    assert short_answer("It's not in my name", "owns_land") == {"owns_land": False}
    assert short_answer("No tax, but my brother pays", "pays_income_tax") == {"pays_income_tax": True}
    assert short_answer("maybe, I am not sure", "owns_land") == {}


def test_sensitive_digit_runs_are_redacted_or_dropped_from_slots():
    redacted = redact_sensitive_numbers("Aadhaar 123456789012 and phone 9876543210")
    assert "123456789012" not in redacted
    assert "9876543210" not in redacted
    assert clean_slot_updates({"district": "123456789012", "state": 987654321012, "owns_land": True, "aadhaar": "123456789012"}) == {"owns_land": True}


def test_expired_sessions_are_removed():
    SESSIONS.clear()
    session_id = UUID("22222222-2222-4222-8222-222222222222")
    merge_session(session_id, {"state": "Tamil Nadu"})
    assert str(session_id) in SESSIONS
    SESSIONS[str(session_id)]["last_seen"] = 1000.0
    purge_expired_sessions(now=1000 + SESSION_TTL_SECONDS + 1)
    assert str(session_id) not in SESSIONS
