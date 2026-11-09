from __future__ import annotations

import asyncio
import difflib
import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import yaml

from backend.app.config import settings
from backend.app.dialogue.extractor import MockExtractor
from backend.app.main import (
    ChatRequest, SESSIONS, chat, extract_slots, localized_copy, local_extract,
    redact_sensitive_numbers, short_answer, voice_retry_message,
)
from backend.app.voice.base import STTResult
from backend.app.voice.fakes import FakeTTS
from backend.app.main import app

CASE_FILE = Path(__file__).with_name("language_cases.yaml")
LOCALE = {"hi":"hi-IN", "ta":"ta-IN", "te":"te-IN", "en":"en-IN"}
LANGUAGE_CASES = yaml.safe_load(CASE_FILE.read_text(encoding="utf-8"))["languages"]
CASES = [dict(case, language=language) for language, items in LANGUAGE_CASES.items() for case in items]

def _case_slots(case, text=None):
    lang=case["language"]
    pending=case.get("pending_question")
    known=dict(case.get("initial_slots", {}))
    utterance=case["input_text"] if text is None else text
    extracted,_,reask=extract_slots(utterance,LOCALE[lang],known,pending)
    extracted.update(short_answer(utterance,pending))
    return extracted,reask

def _assert_expected(case, slots):
    for key,value in case.get("expected_slots",{}).items():
        assert slots.get(key)==value, f"{case['language']}/{case['id']} expected {key}={value!r}, got {slots.get(key)!r}"
    for key,value in case.get("forbidden_slots",{}).items():
        if value=="any": assert key not in slots, f"{case['language']}/{case['id']} must not set {key}"
        elif value=="changes": assert slots.get(key)==case.get("initial_slots",{}).get(key), f"{key} changed unexpectedly"
        else: assert slots.get(key)!=value, f"{case['language']}/{case['id']} must not set {key}={value!r}"

def _check_level1(case,monkeypatch):
    import backend.app.main as main
    monkeypatch.setattr(main,"get_extractor",lambda:MockExtractor())
    text=case["input_text"] or "unrecognized answer"
    session=uuid4()
    payload=chat(ChatRequest(text=text,language=LOCALE[case["language"]],
        known_slots=case.get("initial_slots",{}),session_id=session,
        pending_slot=case.get("pending_question")))
    action=case["expected_dialogue_action"]
    if action=="re-ask":
        assert payload.get("stage")=="clarify"
        assert payload.get("next_question")
    elif action=="correct":
        assert payload.get("stage")=="correction" and payload.get("next_slot")=="state"
        answer=chat(ChatRequest(text="Karnataka",language=LOCALE[case["language"]],
            known_slots=payload["slots"],session_id=session,pending_slot="state"))
        _assert_expected(case,answer["slots"])
        assert answer["slots"].get("water_source")=="canal"
        return payload
    elif action=="confirm":
        assert payload.get("confirmed") is True
    elif action=="fallback":
        assert payload.get("stage")=="clarify"
        assert voice_retry_message(LOCALE[case["language"]],1)
    else:
        _assert_expected(case,payload.get("slots",{}))
    if case["scenario"]=="sensitive_numbers":
        safe=redact_sensitive_numbers(text)
        assert "1234 5678 9012" not in safe and "123456789012" not in safe
        assert payload.get("privacy_warning")
        assert "1234 5678 9012" not in json.dumps(payload,ensure_ascii=False)
    if action not in {"re-ask","correct","confirm","fallback"}:
        slots,reask=_case_slots(case)
        _assert_expected(case,slots)
        assert not reask
    return payload

@pytest.mark.parametrize("case",CASES,ids=lambda c:f"{c['language']}-{c['id']}")
def test_level1_text_extraction_yes_no_and_dialogue(case,monkeypatch):
    _check_level1(case,monkeypatch)

class CaseSTT:
    def __init__(self,case):
        self.case=case
    def transcribe(self,audio,language,**kwargs):
        return STTResult(self.case["input_text"],language,self.case.get("mock_stt_confidence",1.0))

def _post_voice(case,session_id,monkeypatch):
    import backend.app.main as main
    monkeypatch.setattr(main,"get_voice_providers",lambda:(CaseSTT(case),FakeTTS()))
    monkeypatch.setattr(main,"get_extractor",lambda:MockExtractor())
    async def request():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
            return await client.post("/api/voice",files={"audio":("case.wav",b"synthetic audio","audio/wav")},data={
                "language":LOCALE[case["language"]],"session_id":str(session_id),
                "pending_slot":case.get("pending_question") or "",
                "known_slots":json.dumps(case.get("initial_slots",{}),ensure_ascii=False)})
    response=asyncio.run(request())
    assert response.status_code==200
    return response.json()

@pytest.mark.parametrize("case",CASES,ids=lambda c:f"{c['language']}-{c['id']}")
def test_level2_voice_api_full_reply_with_mock_stt(case,monkeypatch,caplog):
    session=uuid4()
    payload=_post_voice(case,session,monkeypatch)
    action=case["expected_dialogue_action"]
    if action=="fallback":
        assert payload["stage"]=="retry"
        assert "1551" in payload["reply"]
        assert localized_copy("retry",LOCALE[case["language"]]).split(".")[0] in payload["reply"]
        second=_post_voice(case,session,monkeypatch)
        assert second["stage"]=="retry" and "1551" in second["reply"]
        assert voice_retry_message(LOCALE[case["language"]],2) in second["reply"]
        assert not any(payload.get("slots",{}).get(slot) is not None for slot in case.get("forbidden_slots",{}))
        return
    if action=="re-ask":
        _assert_expected(case,payload.get("slots",{}))
        assert payload.get("stage")=="clarify" and payload.get("next_question")
    elif action=="correct":
        assert payload.get("stage")=="correction" and payload.get("next_slot")=="state"
        followup=dict(case,input_text="Karnataka",pending_question="state",initial_slots=payload.get("slots",{}))
        corrected=_post_voice(followup,session,monkeypatch)
        _assert_expected(case,corrected.get("slots",{}))
        assert corrected["slots"].get("water_source")==case["initial_slots"]["water_source"]
    elif action=="confirm":
        _assert_expected(case,payload.get("slots",{}))
        assert payload.get("stage")=="complete"
        assert "PM-KISAN" in payload["reply"]
        assert payload["scope"]==localized_copy("scope",LOCALE[case["language"]])
        assert any(item["scheme_id"]=="pm_kisan" for item in payload["results"])
        assert any(item["scheme_id"]=="pm_kisan" and item["not_checked"] for item in payload["results"])
        assert any(item["scheme_id"]=="pm_kisan" and item["badge"]=="Unverified draft" for item in payload["results"])
    else:
        _assert_expected(case,payload.get("slots",{}))
    if case["scenario"]=="sensitive_numbers":
        assert "1234 5678 9012" not in json.dumps(payload,ensure_ascii=False)
        assert payload.get("privacy_warning") in payload.get("reply","")
        assert "123456789012" not in caplog.text
    if case["scenario"]=="disclosure":
        assert localized_copy("disclosures",LOCALE[case["language"]])[:10] in payload.get("reply","")

@pytest.mark.live
@pytest.mark.parametrize("case",CASES,ids=lambda c:f"{c['language']}-{c['id']}")
def test_level3_live_audio_round_trip_smoke(case,record_property):
    if case["scenario"]=="sensitive_numbers":
        pytest.skip("does not send Aadhaar-like fixture numbers to external APIs")
    import backend.app.main as main
    from backend.app.voice.providers import get_voice_providers
    from backend.app.voice.base import STTResult
    from backend.app.voice.gnani import GnaniProviderError
    # The live run must use the configured real provider and never infer keys in tests.
    if settings.use_mock_voice or not settings.gnani_api_key:
        pytest.skip("live provider settings are not enabled")
    _,tts=get_voice_providers()
    text=case["input_text"] or localized_copy("retry",LOCALE[case["language"]])
    safe_text=redact_sensitive_numbers(text)
    async def live_turn():
        audio=await tts.synthesize(safe_text,LOCALE[case["language"]])
        stt,_=get_voice_providers()
        return await stt.transcribe(audio,LOCALE[case["language"]],filename="language-case.wav",mime_type="audio/wav")
    result=asyncio.run(live_turn())
    similarity=difflib.SequenceMatcher(None," ".join(safe_text.casefold().split())," ".join(result.transcript.casefold().split())).ratio()
    record_property("round_trip_similarity_smoke_only",f"{similarity:.3f}")
    slots,_,_=main.extract_slots(result.transcript,result.language,{},case.get("pending_question"))
    record_property("level1_slots_from_round_trip",json.dumps(slots,ensure_ascii=False))
    print(f"LIVE ROUND-TRIP SMOKE ONLY | {case['language']} | {case['id']} | similarity={similarity:.0%}")

@pytest.mark.parametrize("language",["hi","ta","te","en"])
def test_scripted_full_conversation_asks_slots_then_confirms_and_reports(language,monkeypatch):
    scenarios=[c for c in CASES if c["language"]==language]
    prompts={c["id"]:c["input_text"] for c in scenarios}
    answers={"owns_land":{"hi":"हाँ","ta":"ஆம்","te":"అవును","en":"yes"}[language],
        "is_institutional_holder":{"hi":"नहीं","ta":"இல்லை","te":"కాదు","en":"no"}[language],
        "pays_income_tax":{"hi":"नहीं","ta":"இல்லை","te":"లేదు","en":"no"}[language],
        "district":"Madurai","crop":{"hi":"धान","ta":"நெல்","te":"వరి","en":"rice"}[language],
        "season":{"hi":"खरीफ","ta":"காரிஃப்","te":"ఖరీఫ్","en":"kharif"}[language],
        "area_notified":{"hi":"हाँ","ta":"ஆம்","te":"అవును","en":"yes"}[language],
        "has_grid_connected_pump":{"hi":"बिजली का कनेक्शन नहीं है","ta":"மின் இணைப்பு இல்லை","te":"విద్యుత్ కనెక్షన్ లేదు","en":"no electricity connection"}[language],
        "state_application_open":{"hi":"हाँ","ta":"ஆம்","te":"అవును","en":"yes"}[language],
        "state_requirements_confirmed":{"hi":"हाँ","ta":"ஆம்","te":"అవును","en":"yes"}[language]}
    answers["state"]={"hi":"तमिलनाडु","ta":"தமிழ்நாடு","te":"తమిళనాడు","en":"Tamil Nadu"}[language]
    answers["water_source"]={"hi":"बोरवेल","ta":"ஆழ்துளை கிணறு","te":"బోరుబావి","en":"borewell"}[language]
    first={"hi":"तमिलनाडु में बोरवेल से सिंचाई करता हूँ।","ta":"தமிழ்நாட்டில் ஆழ்துளை கிணறு பயன்படுத்துகிறேன்.","te":"తమిళనాడులో బోరుబావి వాడతాను.","en":"Tamil Nadu, borewell irrigation."}[language]
    queue=[first]
    class QueueSTT:
        def transcribe(self,*args,**kwargs):return STTResult(queue.pop(0),LOCALE[language],1.0)
    import backend.app.main as main
    monkeypatch.setattr(main,"get_voice_providers",lambda:(QueueSTT(),FakeTTS()))
    monkeypatch.setattr(main,"get_extractor",lambda:MockExtractor())
    session=uuid4()
    async def conversation():
        transport=httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport,base_url="http://test") as client:
            # Seed the other basic facts as if collected in one natural
            # opening utterance; keep this scripted flow within the six-question ceiling.
            known={"owns_land":True,"is_institutional_holder":False,"pays_income_tax":False,
                "district":"Madurai","crop":"rice","season":"kharif","area_notified":True,
                "has_grid_connected_pump":False,"state_application_open":True,
                "state_requirements_confirmed":True}
            pending=""
            response=await client.post("/api/voice",files={"audio":("turn.wav",b"x","audio/wav")},data={"language":LOCALE[language],"session_id":str(session),"known_slots":json.dumps(known,ensure_ascii=False)})
            body=response.json(); assert response.status_code==200
            assert body["next_slot"] and body["next_question"]
            assert localized_copy("disclosures",LOCALE[language])[:10] in body.get("reply","")
            for _ in range(15):
                if body.get("stage")=="confirming": break
                pending=body["next_slot"]
                queue.append(answers[pending])
                response=await client.post("/api/voice",files={"audio":("turn.wav",b"x","audio/wav")},data={"language":LOCALE[language],"session_id":str(session),"pending_slot":pending,"known_slots":json.dumps(body.get("slots",known),ensure_ascii=False)})
                body=response.json(); assert response.status_code==200
                assert body.get("stage") in {"collecting","confirming"}
                assert body.get("next_slot")
            assert body["stage"]=="confirming"
            queue.append({"hi":"हाँ","ta":"ஆம்","te":"అవును","en":"yes"}[language])
            response=await client.post("/api/voice",files={"audio":("turn.wav",b"x","audio/wav")},data={"language":LOCALE[language],"session_id":str(session),"pending_slot":"__confirm__","known_slots":json.dumps(body["slots"],ensure_ascii=False)})
            final=response.json();assert response.status_code==200
            return final
    final=asyncio.run(conversation())
    assert final["stage"]=="complete"
    assert final["scope"]==localized_copy("scope",LOCALE[language])
    pmk=next(row for row in final["results"] if row["scheme_id"]=="pm_kisan")
    assert pmk["status"]=="eligible" and pmk["not_checked"] and pmk["badge"]=="Unverified draft"
    assert "PM-KISAN" in final["reply"]
