from app.main import compose, localized_copy


def test_eligible_pm_kisan_gets_localized_csc_steps_in_final_reply():
    result = {"name": "PM-KISAN", "status": "eligible", "missing": [], "reasons": []}
    for language in ("en", "hi", "ta", "te"):
        reply = compose([result], language)
        assert reply.endswith(localized_copy("pm_kisan_next_steps", language))


def test_pm_kisan_next_steps_are_not_recommended_after_known_failure():
    result = {"name": "PM-KISAN", "status": "not_eligible", "missing": [], "reasons": []}
    reply = compose([result], "ta")
    assert "பொது சேவை மையத்திற்குச் செல்லுங்கள்" not in reply
