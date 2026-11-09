"""Local demo readiness checks. Secrets are inspected only through Settings."""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LANGUAGES = ("hi", "ta", "te", "en")
LOCALES = {"hi": "hi-IN", "ta": "ta-IN", "te": "te-IN", "en": "en-IN"}
DEPENDENCIES = ("fastapi", "uvicorn", "multipart", "yaml", "dotenv", "httpx", "pydantic_settings", "pytest")


class Checks:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def report(self, status: str, label: str, detail: str = "") -> None:
        detail = detail.replace("\r", " ").replace("\n", " · ")
        print(f"{status:<4} {label}" + (f" — {detail}" if detail else ""))
        if status == "FAIL": self.failures.append(label + (f": {detail}" if detail else ""))
        if status == "WARN": self.warnings.append(label + (f": {detail}" if detail else ""))


def is_cloud_path(path: str | Path) -> bool:
    lowered = str(path).casefold().replace("\\", "/")
    return any(part in lowered for part in ("/onedrive/", "/dropbox/", "/icloud drive/", "/icloud/", "clouddocs", "icloud drive"))


def translation_issues(root: Path = ROOT) -> list[str]:
    html = (root / "frontend/index.html").read_text(encoding="utf-8")
    js = (root / "frontend/app.js").read_text(encoding="utf-8")
    found = set(re.findall(r'<option\s+value="([a-z]{2})-IN"', html))
    errors = []
    if found != set(LANGUAGES): errors.append(f"language picker has {sorted(found)}, expected {list(LANGUAGES)}")
    match = re.search(r"const labelsByLanguage\s*=\s*\{(.*?)\n\};", js, re.S)
    if not match:
        errors.append("frontend language label table was not found")
    else:
        blocks = re.findall(r"\b(hi|ta|te|en):\s*\{([^{}]*)\}", match.group(1))
        maps = {lang: set(re.findall(r"([A-Za-z_]+)\s*:", body)) for lang, body in blocks}
        if set(maps) != set(LANGUAGES): errors.append(f"frontend labels missing languages: {sorted(set(LANGUAGES)-set(maps))}")
        elif any(keys != maps["en"] for keys in maps.values()): errors.append("frontend language label keys do not match English")
    return errors


def port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: sock.bind((host, port)); return True
        except OSError: return False


def run_local_mock_voice_smoke() -> tuple[bool, str]:
    """Exercise each locale through the real FastAPI voice route with fake providers."""
    import httpx
    from backend.app.voice.base import STTResult
    from backend.app.voice.fakes import FakeTTS
    import backend.app.main as main

    class LocaleSTT:
        def __init__(self, language: str): self.language = language
        def transcribe(self, audio: bytes, language: str, **kwargs):
            return STTResult("I own land in Tamil Nadu", self.language, 1.0)

    original = main.get_voice_providers
    times = {}
    try:
        async def check(language: str):
            main.get_voice_providers = lambda: (LocaleSTT(language), FakeTTS())
            started = time.perf_counter()
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://localhost") as client:
                response = await client.post("/api/voice", files={"audio": ("demo.wav", b"mock audio", "audio/wav")},
                    data={"language": language, "known_slots": "{}"})
            times[language] = (time.perf_counter() - started) * 1000
            body = response.json()
            return response.status_code == 200 and bool(body.get("reply")) and bool(body.get("stage"))
        async def all_languages():
            return [await check(LOCALES[lang]) for lang in LANGUAGES]
        outcomes = asyncio.run(all_languages())
        return all(outcomes), ", ".join(f"{lang} {times.get(LOCALES[lang],0):.0f} ms" for lang in LANGUAGES)
    except Exception as exc:
        return False, type(exc).__name__
    finally:
        main.get_voice_providers = original


def live_provider_check(python: str = sys.executable) -> tuple[bool, str]:
    result = subprocess.run([python, str(ROOT / "scripts/check_gnani.py")], cwd=ROOT,
        text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=240)
    output = (result.stdout + result.stderr).strip()
    # The provider script emits only sanitized status/timing data. Show its
    # language table, but never show settings or environment values.
    if output: print(output)
    if result.returncode:
        return False, f"round-trip check exited {result.returncode}"
    lines = [line for line in output.splitlines() if line.startswith("|") and "---" not in line and "Language" not in line]
    supported = {lang: any(f"| {LOCALES[lang]} |" in line and "unsupported" not in line for line in lines) for lang in LANGUAGES}
    missing = [f"{LOCALES[lang]} unsupported/missing" for lang, ok in supported.items() if not ok]
    return not missing, ", ".join(missing) if missing else "hi, ta, te, en round trips completed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="skip the full offline test suite")
    parser.add_argument("--mode", choices=("mock", "live"), default="mock")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--base-url", default="")
    parser.add_argument("--live-roundtrip-done", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    checks = Checks()
    base_url = args.base_url.rstrip("/") or (f"http://localhost:{args.port}" if not args.quick else "")

    os.environ["USE_MOCK_VOICE"] = "true" if args.mode == "mock" else "false"
    if args.mode == "mock": os.environ["USE_MOCK_LLM"] = "true"
    try:
        from backend.app.config import settings
    except Exception as exc:
        settings = None
        checks.report("FAIL", "Configuration", type(exc).__name__)
    checks.report("PASS" if sys.version_info >= (3, 11) else "FAIL", "Python version",
        sys.version.split()[0] + (" (requires 3.11+)" if sys.version_info < (3,11) else ""))
    missing = [name for name in DEPENDENCIES if importlib.util.find_spec(name) is None]
    checks.report("FAIL" if missing else "PASS", "Demo dependencies", ", ".join(missing) if missing else "installed")
    checks.report("WARN" if is_cloud_path(ROOT) else "PASS", "Project location",
        "inside a synced cloud folder; sync may lock files and secrets should not be stored here" if is_cloud_path(ROOT) else str(ROOT))

    key_set = bool(settings and settings.gnani_api_key)
    checks.report("PASS" if key_set else ("WARN" if args.mode == "mock" else "FAIL"), "Gnani API key", "set" if key_set else "not set")
    checks.report("PASS", "Requested mode", args.mode)
    if settings:
        checks.report("PASS", "Provider settings", f"voice={'mock' if settings.use_mock_voice else 'live'}; LLM={'mock' if settings.use_mock_llm else 'live'}")

    if base_url:
        base = base_url
        parsed = urlparse(base)
        checks.report("PASS" if parsed.hostname in {"localhost", "127.0.0.1"} else "FAIL", "Local browser origin", parsed.hostname or "missing host")
        checks.report("PASS", "Port check", f"YojanaSuno is listening on {parsed.port or 80}")
        try:
            import httpx
            health = httpx.get(base + "/api/health", timeout=4)
            health.raise_for_status(); payload = health.json()
            okay = payload.get("status") == "ok" and bool(payload.get("version")) and bool(payload.get("schemes")) and "modes" in payload
            checks.report("PASS" if okay else "FAIL", "Backend health", f"v{payload.get('version')} · {len(payload.get('schemes',{}))} schemes · {payload.get('providers')} · modes={payload.get('modes')}")
            for path in ("/", "/app.js", "/style.css"):
                response = httpx.get(base + path, timeout=4)
                checks.report("PASS" if response.status_code == 200 else "FAIL", f"Frontend {path}", f"HTTP {response.status_code}")
        except Exception as exc:
            checks.report("FAIL", "Backend health / frontend", type(exc).__name__)
        issues = translation_issues()
        checks.report("FAIL" if issues else "PASS", "Frontend languages", "; ".join(issues) if issues else "hi, ta, te, en keys and picker present")
        okay, detail = run_local_mock_voice_smoke()
        checks.report("PASS" if okay else "FAIL", "Mock voice API smoke", detail)
    else:
        free = port_is_free("127.0.0.1", args.port)
        checks.report("PASS" if free else "WARN", "Port check", f"127.0.0.1:{args.port} is free" if free else f"{args.port} is occupied; demo launcher will choose a fallback")
        checks.report("WARN" if args.quick else "FAIL", "Backend health", "pass --base-url after the server is running" if args.quick else f"no server responded at http://localhost:{args.port}; start the demo and pass its URL")
        issues = translation_issues()
        checks.report("FAIL" if issues else "PASS", "Frontend languages", "; ".join(issues) if issues else "hi, ta, te, en keys and picker present")
        if not args.quick:
            okay, detail = run_local_mock_voice_smoke()
            checks.report("PASS" if okay else "FAIL", "Mock voice API smoke", detail)

    if args.mode == "live":
        if not key_set:
            checks.report("FAIL", "Live credentials", "Gnani key is not set")
        else:
            host = urlparse(settings.gnani_stt_url).hostname
            try:
                with socket.create_connection((host, 443), timeout=5): pass
                checks.report("PASS", "Gnani host reachability", host)
            except Exception as exc:
                checks.report("FAIL", "Gnani host reachability", f"{host or 'unknown host'} · {type(exc).__name__}")
            if args.live_roundtrip_done:
                checks.report("PASS", "Gnani language round trips", "completed before backend start")
            else:
                try: okay, detail = live_provider_check()
                except Exception as exc: okay, detail = False, type(exc).__name__
                checks.report("PASS" if okay else "FAIL", "Gnani round-trip (hi/ta/te/en)", detail)

    if not args.quick:
        env = os.environ.copy(); env["USE_MOCK_VOICE"] = "true"; env["USE_MOCK_LLM"] = "true"
        try:
            result = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT / "backend", env=env,
                text=True, capture_output=True, timeout=240)
            tail = "\n".join((result.stdout + result.stderr).strip().splitlines()[-3:])
            checks.report("PASS" if result.returncode == 0 else "FAIL", "Offline test suite", tail or f"exit {result.returncode}")
        except Exception as exc: checks.report("FAIL", "Offline test suite", type(exc).__name__)
    else:
        checks.report("WARN", "Offline test suite", "skipped by --quick")

    if checks.failures:
        print("NOT READY: " + "; ".join(checks.failures))
        return 1
    print("READY FOR DEMO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
