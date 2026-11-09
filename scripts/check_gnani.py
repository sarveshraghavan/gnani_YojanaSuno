"""Live Prisma/Timbre round-trip smoke check. Not an accuracy benchmark."""
from __future__ import annotations

import asyncio
import difflib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import settings  # noqa: E402
from backend.app.voice.gnani import LANGUAGE_VOICE_MAP, PrismaSTT, TimbreTTS, voice_mapping  # noqa: E402

SENTENCES = {
    "hi-IN": ["मेरे खेत में धान की फसल है।", "मेरे पास दो एकड़ जमीन है।", "मेरे खेत में कुएँ का पानी है।"],
    "ta-IN": ["என் வயலில் நெல் பயிர் செய்கிறேன்.", "என்னிடம் இரண்டு ஏக்கர் நிலம் உள்ளது.", "என் வயலில் கிணற்று நீர் உள்ளது."],
    "te-IN": ["నా పొలంలో వరి పంట పండిస్తున్నాను.", "నా దగ్గర రెండు ఎకరాల భూమి ఉంది.", "నా పొలానికి బావి నీరు ఉంది."],
    "en-IN": ["I grow rice on my farm.", "I own two acres of land.", "My farm uses well water."],
}

def similarity(a: str, b: str) -> str:
    a = " ".join(a.casefold().split())
    b = " ".join(b.casefold().split())
    return f"{difflib.SequenceMatcher(None, a, b).ratio():.0%}"

async def run() -> int:
    print("Round-trip smoke test only; similarity is not an accuracy measure.\n")
    print("| Language | Voice | TTS | TTS ms | STT | STT ms | Similarity | Error |\n|---|---|---:|---:|---:|---:|---:|---|")
    if settings.use_mock_voice or not settings.gnani_api_key:
        print("Real providers are disabled or not configured. Set USE_MOCK_VOICE=false and configure the local key through backend settings.")
        return 2
    stt = PrismaSTT(settings.gnani_api_key, settings.prisma_model, settings.gnani_stt_url)
    tts = TimbreTTS(settings.gnani_api_key, settings.timbre_model, settings.gnani_tts_url)
    audio_dir = ROOT / "tmp_audio"
    audio_dir.mkdir(exist_ok=True)
    failed = False
    for lang, sentences in SENTENCES.items():
        mapping = voice_mapping(lang)
        if not mapping or lang not in LANGUAGE_VOICE_MAP:
            for _ in sentences:
                print(f"| {lang} | — | unsupported | — | unsupported | — | — | language/voice pair unconfirmed |")
            failed = True
            continue
        for i, original in enumerate(sentences, 1):
            tts_ms = stt_ms = None
            transcript = ""
            error = ""
            try:
                start = time.perf_counter(); audio = await tts.synthesize(original, lang)
                tts_ms = (time.perf_counter() - start) * 1000
                (audio_dir / f"{lang.split('-')[0]}_{i}.wav").write_bytes(audio)
            except Exception as exc:
                error = f"TTS: {type(exc).__name__}"
                failed = True
            if not error:
                try:
                    start = time.perf_counter(); result = await stt.transcribe(audio, lang, filename=f"{lang.split('-')[0]}_{i}.wav", mime_type="audio/wav")
                    stt_ms = (time.perf_counter() - start) * 1000; transcript = result.transcript
                except Exception as exc:
                    error = f"STT: {type(exc).__name__}"; failed = True
            tts_display = f"{tts_ms:.0f}" if tts_ms is not None else "—"
            stt_display = f"{stt_ms:.0f}" if stt_ms is not None else "—"
            print(f"| {lang} | {mapping['voice']} | {'ok' if tts_ms is not None else 'failed'} | {tts_display} | {'ok' if stt_ms is not None else 'failed'} | {stt_display} | {similarity(original, transcript) if transcript else '—'} | {error or '—'} |")
    return int(failed)

if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
