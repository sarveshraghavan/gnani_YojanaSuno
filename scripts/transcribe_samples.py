"""Transcribe manually supplied <lang>_<n>.wav recordings in samples/."""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import settings  # noqa: E402
from backend.app.voice.gnani import PrismaSTT  # noqa: E402

async def run() -> int:
    folder = ROOT / "samples"; folder.mkdir(exist_ok=True)
    files = sorted(folder.glob("*.wav"))
    files = [f for f in files if f.stem.split("_")[0] in {"hi", "ta", "te", "en"} and f.stem.split("_")[-1].isdigit()]
    if not files:
        print("No recordings found. Add files named hi_1.wav, ta_1.wav, te_1.wav, or en_1.wav."); return 0
    if settings.use_mock_voice or not settings.gnani_api_key:
        print("Real STT is disabled or not configured; enable it through backend settings."); return 2
    stt = PrismaSTT(settings.gnani_api_key, settings.prisma_model, settings.gnani_stt_url)
    for file in files:
        lang = {"hi":"hi-IN", "ta":"ta-IN", "te":"te-IN", "en":"en-IN"}[file.stem.split("_")[0]]
        try:
            result = await stt.transcribe(file.read_bytes(), lang, filename=file.name, mime_type="audio/wav")
            print(f"{file.name} [{result.language}]: {result.transcript}")
        except Exception as exc:
            print(f"{file.name}: transcription failed ({type(exc).__name__})")
    return 0

if __name__ == "__main__": raise SystemExit(asyncio.run(run()))
