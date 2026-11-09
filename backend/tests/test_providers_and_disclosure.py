import asyncio
import json
from io import BytesIO
from uuid import UUID

import httpx
from fastapi import UploadFile

from app.config import settings
from app.dialogue.disclosure import disclosure_for
from app.dialogue.extractor import EvonExtractor, get_extractor, parse_json_slots, validate_slots
from app.main import SESSIONS, ChatRequest, chat, voice_turn
from app.voice.fakes import FakeSTT, FakeTTS
from app.voice.gnani import GnaniProviderError, PrismaSTT, TimbreTTS
from app.voice.providers import get_voice_providers


class FakeAsyncClient:
    calls = []
    responses = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_gnani_stt_request_shape_and_optional_confidence(monkeypatch):
    FakeAsyncClient.calls = []
    FakeAsyncClient.responses = [httpx.Response(200, json={
        "transcript": "मेरी जमीन", "detected_language_code": "hi-IN"})]
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    result = asyncio.run(PrismaSTT("never-print-this", endpoint="https://stt.test")
                         .transcribe(b"wav-bytes", "hi-IN", filename="farm.wav", mime_type="audio/wav"))
    url, request = FakeAsyncClient.calls[0]
    assert url == "https://stt.test"
    assert request["headers"]["X-API-Key-ID"] == "never-print-this"
    assert request["files"]["audio_file"] == ("farm.wav", b"wav-bytes", "audio/wav")
    assert request["data"]["language_code"] == "hi-IN"
    assert result.transcript == "मेरी जमीन" and result.confidence is None


def test_gnani_tts_request_shape_and_raw_audio(monkeypatch):
    FakeAsyncClient.calls = []
    FakeAsyncClient.responses = [httpx.Response(200, content=b"RIFF-wav", headers={"content-type": "audio/wav"})]
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    result = asyncio.run(TimbreTTS("key", endpoint="https://tts.test").synthesize("வணக்கம்", "ta-IN"))
    url, request = FakeAsyncClient.calls[0]
    assert url == "https://tts.test"
    assert request["headers"]["X-API-Key-ID"] == "key"
    assert request["json"]["language"] == "ta-IN"
    assert request["json"]["voice"] == "Asmita"
    assert result == b"RIFF-wav"


def test_gnani_retries_one_network_failure(monkeypatch):
    FakeAsyncClient.calls = []
    FakeAsyncClient.responses = [httpx.ConnectError("offline"), httpx.Response(200, json={"transcript":"yes"})]
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    result = asyncio.run(PrismaSTT("key").transcribe(b"audio", "en-IN"))
    assert result.transcript == "yes"
    assert len(FakeAsyncClient.calls) == 2


def test_evon_parser_valid_malformed_extra_and_wrong_types():
    assert parse_json_slots('reason {"owns_land":true,"state":"Tamil Nadu"} done') == {
        "owns_land": True, "state": "Tamil Nadu"}
    assert parse_json_slots("not json") == {}
    assert parse_json_slots('{"owns_land":"yes","state":4,"unknown":true}') == {}
    assert validate_slots({"water_source":"Borewell", "component":"A", "pays_income_tax":1}) == {
        "water_source": "borewell"}


def test_evon_request_uses_plain_json_prompt_and_validates(monkeypatch):
    seen = {}

    def post(url, **kwargs):
        seen.update(url=url, **kwargs)
        return httpx.Response(200, json={"choices":[{"message":{"content":"{\"owns_land\":true,\"extra\":true}"}}]})

    monkeypatch.setattr(httpx, "post", post)
    result = EvonExtractor("http://localhost:8000/v1", "model").extract("ஆம்", "ta", {})
    assert result == {"owns_land": True}
    assert seen["url"] == "http://localhost:8000/v1/chat/completions"
    payload = seen["json"]
    assert payload["temperature"] == 0.6 and payload["top_p"] == 0.95
    assert payload["max_tokens"] == 300
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert "tools" not in payload
    assert payload["messages"][0]["role"] == "system"
    assert "Farmer language: ta" in payload["messages"][1]["content"]


def test_provider_selection_all_voice_flag_and_key_combinations(monkeypatch):
    for use_mock in (True, False):
        for key in ("", "configured"):
            monkeypatch.setattr(settings, "use_mock_voice", use_mock)
            monkeypatch.setattr(settings, "gnani_api_key", key)
            providers = get_voice_providers()
            should_mock = use_mock or not key
            assert isinstance(providers[0], FakeSTT) is should_mock
            assert isinstance(providers[1], FakeTTS) is should_mock


def test_extractor_selection_all_mock_flag_and_url_combinations(monkeypatch):
    for use_mock in (True, False):
        for base_url in ("", "http://localhost:8000/v1"):
            monkeypatch.setattr(settings, "use_mock_llm", use_mock)
            monkeypatch.setattr(settings, "evon_base_url", base_url)
            extractor = get_extractor()
            assert extractor.is_mock is (use_mock or not base_url)


def test_disclosure_is_localized_and_sent_once_per_session():
    SESSIONS.clear()
    assert "AI" in disclosure_for("en-IN")
    assert "AI" in disclosure_for("hi-IN")
    assert "AI" in disclosure_for("ta-IN")
    assert "AI" in disclosure_for("te-IN")
    session_id = UUID("33333333-3333-4333-8333-333333333333")
    first = chat(ChatRequest(text="Hello", language="en-IN", session_id=session_id))
    second = chat(ChatRequest(text="hello again", language="en-IN", session_id=session_id))
    assert first["disclosure"]
    assert second["disclosure"] == ""


def test_voice_route_degrades_gracefully_when_stt_returns_auth_or_server_error(monkeypatch):
    import app.main as main

    class FailingSTT:
        async def transcribe(self, *args, **kwargs):
            raise GnaniProviderError("provider returned HTTP 401 or 500")

    monkeypatch.setattr(main, "get_voice_providers", lambda: (FailingSTT(), FakeTTS()))
    upload = UploadFile(filename="test.wav", file=BytesIO(b"audio"))
    result = asyncio.run(voice_turn(upload, "en-IN", UUID("44444444-4444-4444-8444-444444444444"), None, "{}"))
    assert result["stage"] == "retry"
    assert "1551" in result["reply"]
    assert result["session_id"]


def test_voice_route_falls_back_for_mocked_http_timeouts_401_and_500(monkeypatch):
    import app.main as main

    for failure in (httpx.Response(401), httpx.Response(500), httpx.ReadTimeout("timed out")):
        FakeAsyncClient.calls = []
        FakeAsyncClient.responses = [failure, failure] if isinstance(failure, httpx.ReadTimeout) else [failure]
        monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
        monkeypatch.setattr(main, "get_voice_providers", lambda: (PrismaSTT("key"), FakeTTS()))
        upload = UploadFile(filename="test.wav", file=BytesIO(b"audio"))
        result = asyncio.run(voice_turn(upload, "en-IN", UUID("55555555-5555-4555-8555-555555555555"), None, "{}"))
        assert result["stage"] == "retry"
        assert "1551" in result["reply"]


def test_tts_http_failure_returns_text_and_kisan_fallback(monkeypatch):
    import app.main as main

    FakeAsyncClient.responses = [httpx.Response(500)]
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(main, "get_voice_providers", lambda: (
        FakeSTT("yes"), TimbreTTS("key")))
    slots = {"owns_land": True, "is_institutional_holder": False, "pays_income_tax": False,
             "state": "Tamil Nadu", "district": "Madurai", "crop": "rice", "season": "kharif",
             "area_notified": True, "component": "B", "state_application_open": True,
             "state_requirements_confirmed": True}
    upload = UploadFile(filename="test.wav", file=BytesIO(b"audio"))
    result = asyncio.run(voice_turn(upload, "en-IN", UUID("66666666-6666-4666-8666-666666666666"),
                                    "__confirm__", json.dumps(slots)))
    assert result["stage"] == "complete"
    assert result["audio_base64"] is None
    assert "1551" in result["fallback_audio_text"]


def test_evon_malformed_or_server_error_falls_back_to_empty(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(500, text="unavailable"))
    assert EvonExtractor("http://localhost:8000/v1", "model").extract("yes", "en", {}) == {}
