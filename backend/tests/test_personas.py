"""Mock-only demo persona coverage through the real /api/voice route."""
import asyncio
import json
from uuid import uuid4

import httpx
import pytest

from app.main import app
from app.dialogue.extractor import MockExtractor
from app.voice import FakeTTS
from app.voice.base import STTResult


PERSONA4 = {
    "en": "I have a diesel pump and no electricity connection.",
    "hi": "मेरे पास डीज़ल पंप है और बिजली का कनेक्शन नहीं है।",
    "ta": "என்னிடம் டீசல் பம்ப் உள்ளது; மின் இணைப்பு இல்லை.",
    "te": "నా దగ్గర డీజిల్ పంపు ఉంది, విద్యుత్ కనెక్షన్ లేదు.",
}
LOCALE = {lang: lang + "-IN" for lang in PERSONA4}


@pytest.mark.parametrize("language", ["hi", "ta", "te", "en"])
def test_persona4_diesel_no_grid_runs_through_voice_api(language, monkeypatch):
    import app.main as main

    utterances = [PERSONA4[language], {"hi": "हाँ", "ta": "ஆம்", "te": "అవును", "en": "yes"}[language]]

    class PersonaSTT:
        def transcribe(self, *_args, **_kwargs):
            return STTResult(utterances.pop(0), LOCALE[language], 1.0)

    monkeypatch.setattr(main, "get_voice_providers", lambda: (PersonaSTT(), FakeTTS()))
    monkeypatch.setattr(main, "get_extractor", lambda: MockExtractor())
    session = uuid4()
    slots = {
        "state": "Tamil Nadu", "owns_land": True, "is_institutional_holder": False,
        "pays_income_tax": False, "district": "Madurai", "crop": "rice",
        "season": "kharif", "area_notified": True,
        "state_application_open": True, "state_requirements_confirmed": True,
    }

    async def send():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post("/api/voice", files={"audio": ("turn.wav", b"mock", "audio/wav")},
                data={"language": LOCALE[language], "session_id": str(session),
                      "pending_slot": "has_grid_connected_pump", "known_slots": json.dumps(slots)})
            assert first.status_code == 200
            first_body = first.json()
            assert first_body["stage"] == "confirming"
            return await client.post("/api/voice", files={"audio": ("turn.wav", b"mock", "audio/wav")},
                data={"language": LOCALE[language], "session_id": str(session),
                      "pending_slot": "__confirm__", "known_slots": json.dumps(first_body["slots"])})

    response = asyncio.run(send())
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "mock"
    assert body["stage"] == "complete"
    assert body["slots"]["has_grid_connected_pump"] is False
    kusum = next(row for row in body["results"] if row["scheme_id"] == "pm_kusum")
    assert kusum["status"] == "eligible"
    # Ensure the input follows the B path in the deterministic engine.
    from app.eligibility.engine import _mapped_rule_slots, load_schemes
    scheme = next(item for item in load_schemes() if item.id == "pm_kusum")
    assert _mapped_rule_slots(scheme, body["slots"])["component"] == "B"


@pytest.mark.parametrize("language", ["hi", "ta", "te", "en"])
@pytest.mark.parametrize("persona,slot,value,utterance,expected,spoken_reason", [
    (1, "owns_land", True, {"hi":"हाँ","ta":"ஆம்","te":"అవును","en":"yes"}, "eligible", "PM-KISAN"),
    (2, "owns_land", False, {"hi":"नहीं","ta":"இல்லை","te":"కాదు","en":"no"}, "not_eligible", {"hi":"जमीन","ta":"நிலம்","te":"భూమి","en":"land"}),
    (3, "pays_income_tax", True, {"hi":"हाँ","ta":"ஆம்","te":"అవును","en":"yes"}, "not_eligible", {"hi":"आयकर","ta":"வருமான வரி","te":"ఆదాయపు పన్ను","en":"income tax"}),
])
def test_personas_1_to_3_run_through_voice_api_in_all_languages(language, persona, slot, value, utterance, expected, spoken_reason, monkeypatch):
    import app.main as main

    consent = utterance[language]
    queue = [consent, {"hi":"हाँ","ta":"ஆம்","te":"అవును","en":"yes"}[language]]
    class PersonaSTT:
        def transcribe(self, *_args, **_kwargs):
            return STTResult(queue.pop(0), LOCALE[language], 1.0)
    monkeypatch.setattr(main, "get_voice_providers", lambda: (PersonaSTT(), FakeTTS()))
    monkeypatch.setattr(main, "get_extractor", lambda: MockExtractor())
    slots = {
        "state":"Tamil Nadu", "district":"Madurai", "crop":"rice", "season":"kharif",
        "area_notified":True, "is_institutional_holder":False, "pays_income_tax":False,
        "owns_land":True, "has_grid_connected_pump":False,
        "state_application_open":True, "state_requirements_confirmed":True,
    }
    slots.pop(slot)
    session = uuid4()
    async def conversation():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post("/api/voice", files={"audio":("turn.wav",b"mock","audio/wav")},
                data={"language":LOCALE[language],"session_id":str(session),"pending_slot":slot,"known_slots":json.dumps(slots)})
            assert first.status_code == 200 and first.json()["stage"] == "confirming"
            return await client.post("/api/voice", files={"audio":("turn.wav",b"mock","audio/wav")},
                data={"language":LOCALE[language],"session_id":str(session),"pending_slot":"__confirm__","known_slots":json.dumps(first.json()["slots"])})
    final = asyncio.run(conversation()).json()
    assert final["stage"] == "complete"
    pmk = next(row for row in final["results"] if row["scheme_id"] == "pm_kisan")
    assert pmk["status"] == expected, f"persona {persona} in {language}"
    spoken = spoken_reason if isinstance(spoken_reason, str) else spoken_reason[language]
    assert spoken in final["reply"]
