from io import BytesIO
import wave
import asyncio
import json
from uuid import UUID

from fastapi import UploadFile

from app.dialogue.next_question import next_question
from app.eligibility.engine import check_all, load_schemes
from app.main import local_extract, voice_turn
from app.voice import FakeSTT, FakeTTS


def test_fake_stt_rules_and_silent_tts_flow_without_credentials():
    stt = FakeSTT("I own land in Tamil Nadu")
    transcript = stt.transcribe(b"fake audio bytes", "en-IN")
    slots = {
        **local_extract(transcript.transcript),
        "is_institutional_holder": False,
        "pays_income_tax": False,
        "district": "Madurai",
        "crop": "rice",
        "season": "kharif",
        "area_notified": True,
        "component": "B",
        "state_application_open": True,
        "state_requirements_confirmed": True,
    }
    results = check_all(slots, load_schemes("schemes"))
    assert all(result.status == "eligible" for result in results)
    assert next_question(results) is None

    audio = FakeTTS().synthesize("Screening is complete", "en-IN")
    with wave.open(BytesIO(audio), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getframerate() == 24000
        assert wav.getnframes() > 0


def test_mock_voice_endpoint_runs_a_full_question_turn(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "get_voice_providers", lambda: (
        FakeSTT("I own land in Tamil Nadu"), FakeTTS()))
    upload = UploadFile(filename="test.wav", file=BytesIO(b"mock audio"))
    result = asyncio.run(main.voice_turn(
        audio=upload, language="en-IN",
        session_id=UUID("22222222-2222-4222-8222-222222222222"),
        pending_slot=None, known_slots="{}"))

    assert result["mode"] == "mock"
    assert result["transcript"] == "I own land in Tamil Nadu"
    assert result["stage"] == "collecting"
    assert result["next_question"]
    with wave.open(BytesIO(__import__("base64").b64decode(result["audio_base64"])), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getframerate() == 24000


def test_low_confidence_mock_audio_asks_for_repeat(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "get_voice_providers", lambda: (
        FakeSTT("unreliable words", confidence=0.2), FakeTTS()))
    upload = UploadFile(filename="test.wav", file=BytesIO(b"mock audio"))
    result = asyncio.run(main.voice_turn(
        audio=upload, language="en-IN", session_id=None,
        pending_slot=None, known_slots="{}"))

    assert result["stage"] == "retry"
    assert "1551" in result["reply"]
    assert result["audio_base64"]
