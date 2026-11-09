from io import BytesIO
import wave

from .base import STTResult


class FakeSTT:
    """Returns a fixed transcript so the call flow can be tested without speech APIs."""

    def __init__(self, transcript: str = "I own land in Tamil Nadu", confidence: float = 1.0):
        self.transcript = transcript
        self.confidence = confidence

    def transcribe(self, audio: bytes, language: str, **metadata: str) -> STTResult:
        return STTResult(self.transcript, language, self.confidence)


class FakeTTS:
    """Returns a short valid silent WAV clip for playback-path tests."""

    def __init__(self, sample_rate: int = 24000, duration_ms: int = 180):
        self.sample_rate = sample_rate
        self.duration_ms = duration_ms

    def synthesize(self, text: str, language: str) -> bytes:
        buffer = BytesIO()
        frames = b"\x00\x00" * (self.sample_rate * self.duration_ms // 1000)
        with wave.open(buffer, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(self.sample_rate)
            audio.writeframes(frames)
        return buffer.getvalue()
