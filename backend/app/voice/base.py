from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class STTResult:
    transcript: str
    language: str
    confidence: float | None = None


class STTProvider(Protocol):
    def transcribe(self, audio: bytes, language: str, **metadata: str) -> STTResult: ...


class TTSProvider(Protocol):
    def synthesize(self, text: str, language: str) -> bytes: ...
