"""Async Gnani adapters based on the current REST API documentation."""
from __future__ import annotations

import httpx

from .base import STTResult

REQUEST_TIMEOUT = httpx.Timeout(connect=8.0, read=45.0, write=45.0, pool=8.0)
RETRIES = 2  # initial attempt plus one retry for connection/timeout failures

# Single source of truth: locales and v2.5 voices are listed in current Gnani docs.
LANGUAGE_VOICE_MAP = {
    "hi-IN": {"stt": True, "tts": True, "voice": "Nalini"},
    "ta-IN": {"stt": True, "tts": True, "voice": "Asmita"},
    "te-IN": {"stt": True, "tts": True, "voice": "Suhana"},
    "en-IN": {"stt": True, "tts": True, "voice": "Kaveri"},
}


def voice_mapping(language: str) -> dict | None:
    normalized = language.strip().casefold()
    if normalized in {"hi", "ta", "te", "en"}:
        normalized += "-in"
    code = {"hi-in":"hi-IN", "ta-in":"ta-IN", "te-in":"te-IN", "en-in":"en-IN"}.get(normalized)
    return LANGUAGE_VOICE_MAP.get(code) if code else None


class GnaniProviderError(RuntimeError):
    """Sanitized provider error; it never contains credentials or response bodies."""


def reject_provider_error(provider: str, response: httpx.Response) -> None:
    """Raise a safe, body-free error for a non-success HTTP response."""
    if response.status_code >= 400:
        raise GnaniProviderError(f"{provider} returned HTTP {response.status_code}.")


def unavailable_error(provider: str, cause: Exception | None = None) -> GnaniProviderError:
    return GnaniProviderError(f"{provider} could not be reached after one retry.")


class PrismaSTT:
    def __init__(self, api_key: str, model: str = "prisma-v3.0",
                 endpoint: str = "https://api.vachana.ai/stt/v3", client_factory=None):
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint
        self.client_factory = client_factory

    async def transcribe(self, audio: bytes, language: str, **metadata: str) -> STTResult:
        filename = metadata.get("filename", "farmer-audio.wav")
        mime_type = metadata.get("mime_type", "audio/wav")
        data = {"model": self.model, "language_code": language}
        last_error: Exception | None = None
        for attempt in range(RETRIES):
            try:
                async with (self.client_factory or httpx.AsyncClient)(timeout=REQUEST_TIMEOUT) as client:
                    response = await client.post(
                        self.endpoint,
                        headers={"X-API-Key-ID": self.api_key},
                        files={"audio_file": (filename, audio, mime_type)},
                        data=data,
                    )
                reject_provider_error("Prisma", response)
                payload = response.json()
                transcript = payload.get("transcript")
                if not isinstance(transcript, str):
                    raise GnaniProviderError("Prisma response did not include a transcript.")
                detected = payload.get("detected_language_code")
                confidence = payload.get("confidence")
                if not isinstance(confidence, (float, int)) or isinstance(confidence, bool):
                    confidence = None
                return STTResult(transcript, detected if isinstance(detected, str) else language,
                                 float(confidence) if confidence is not None else None)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt + 1 == RETRIES:
                    break
            except httpx.RequestError as exc:
                last_error = exc
                if attempt + 1 == RETRIES:
                    break
        raise unavailable_error("Prisma", last_error) from last_error


class TimbreTTS:
    def __init__(self, api_key: str, model: str = "timbre-v2.5",
                 endpoint: str = "https://api.vachana.ai/api/v1/tts/inference",
                 voice: str = "", client_factory=None):
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint
        self.voice = voice.strip()
        self.client_factory = client_factory

    async def synthesize(self, text: str, language: str) -> bytes:
        mapping = voice_mapping(language)
        if not mapping or not mapping["tts"]:
            raise GnaniProviderError("Timbre language is not configured for this locale.")
        locale = next(locale for locale, entry in LANGUAGE_VOICE_MAP.items() if entry is mapping)
        # A single override is accepted, but verify that voice against the selected locale.
        selected_voice = self.voice or mapping["voice"]
        if selected_voice != mapping["voice"]:
            raise GnaniProviderError("Configured Timbre voice is not confirmed for this language.")
        payload = {
            "text": text[:4000], "voice": selected_voice, "model": self.model,
            "language": locale,
            "audio_config": {"encoding": "linear_pcm", "container": "wav",
                             "num_channels": 1, "sample_rate": 24000, "sample_width": 2},
        }
        last_error: Exception | None = None
        for attempt in range(RETRIES):
            try:
                async with (self.client_factory or httpx.AsyncClient)(timeout=REQUEST_TIMEOUT) as client:
                    response = await client.post(
                        self.endpoint, headers={"X-API-Key-ID": self.api_key}, json=payload)
                reject_provider_error("Timbre", response)
                if not response.content:
                    raise GnaniProviderError("Timbre returned empty audio.")
                # The documented REST response is raw binary audio. It does not return base64.
                if "json" in response.headers.get("content-type", "").lower():
                    raise GnaniProviderError("Timbre returned an unexpected JSON body instead of audio.")
                return response.content
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt + 1 == RETRIES:
                    break
            except httpx.RequestError as exc:
                last_error = exc
                if attempt + 1 == RETRIES:
                    break
        raise unavailable_error("Timbre", last_error) from last_error
