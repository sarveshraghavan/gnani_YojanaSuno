import asyncio
import httpx
import pytest
from app.main import app

from app.main import voice_fallback_text
from app.voice.gnani import GnaniProviderError, reject_provider_error, unavailable_error

@pytest.mark.parametrize("provider", ["Prisma", "Timbre"])
@pytest.mark.parametrize("failure", [401, 429, 500])
def test_each_gnani_provider_sanitizes_mocked_http_failures(provider, failure):
    transport=httpx.MockTransport(lambda request:httpx.Response(failure,request=request,content=b"private response body"))
    with httpx.Client(transport=transport) as client:
        response=client.get("https://provider.test")
    with pytest.raises(GnaniProviderError,match=f"{provider} returned HTTP {failure}") as error:
        reject_provider_error(provider,response)
    assert "private response body" not in str(error.value)

@pytest.mark.parametrize("provider", ["Prisma", "Timbre"])
def test_each_gnani_provider_sanitizes_mocked_timeout(provider):
    def handler(request): raise httpx.ReadTimeout("private timeout detail",request=request)
    with pytest.raises(httpx.ReadTimeout) as timeout:
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            client.get("https://provider.test")
    safe=unavailable_error(provider,timeout.value)
    assert "private timeout detail" not in str(safe)

@pytest.mark.parametrize("language", ["hi-IN", "ta-IN", "te-IN", "en-IN"])
def test_voice_error_fallback_is_textual_and_includes_1551(language):
    reply=voice_fallback_text("The audio service is unavailable.",language)
    assert "1551" in reply and reply.startswith("The audio service is unavailable.")


@pytest.mark.parametrize("which", ["stt", "tts"])
@pytest.mark.parametrize("failure", [401, 429, 500, "timeout"])
def test_voice_api_never_500s_for_provider_failures(monkeypatch, which, failure):
    class BrokenSTT:
        async def transcribe(self,*args,**kwargs): raise GnaniProviderError(f"HTTP {failure}")
    class GoodSTT:
        async def transcribe(self,*args,**kwargs):
            from app.voice.base import STTResult
            return STTResult("Tamil Nadu","ta-IN",1.0)
    class BrokenTTS:
        async def synthesize(self,*args,**kwargs): raise GnaniProviderError(f"HTTP {failure}")
    from app.voice.fakes import FakeTTS
    monkeypatch.setattr("app.main.get_voice_providers",lambda:(BrokenSTT() if which=="stt" else GoodSTT(),BrokenTTS() if which=="tts" else FakeTTS()))
    async def request():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
            return await client.post("/api/voice",files={"audio":("clip.wav",b"wav","audio/wav")},data={"language":"ta-IN"})
    response=asyncio.run(request())
    assert response.status_code==200
    body=response.json()
    assert body["reply"]
    assert "1551" in body["fallback_audio_text"]

