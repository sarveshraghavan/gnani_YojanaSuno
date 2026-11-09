"""Supervise a local YojanaSuno server for a laptop demo."""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MANIFEST = ROOT / ".demo_session.json"


def free_port(start: int = 8765, end: int = 8795) -> int | None:
    for port in range(start, end):
        with socket.socket() as sock:
            try: sock.bind(("127.0.0.1", port)); return port
            except OSError: continue
    return None


def health_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url + "/api/health", timeout=1.5) as response:
            import json
            payload = json.loads(response.read().decode("utf-8"))
            return response.status == 200 and payload.get("status") == "ok"
    except Exception:
        return False


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", nargs="?", choices=("mock", "live"), default="mock")
    parser.add_argument("--no-browser", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    # These are child-process overrides only. Never edit or copy backend/.env.
    os.environ["USE_MOCK_VOICE"] = "true" if args.mode == "mock" else "false"
    if args.mode == "mock": os.environ["USE_MOCK_LLM"] = "true"

    from backend.app.config import settings
    if args.mode == "live":
        if not settings.gnani_api_key:
            print("Live mode not started: Gnani API key is not set in local settings.")
            return 2
        print("Checking Gnani live voice for Hindi, Tamil, Telugu, and English…")
        result = subprocess.run([sys.executable, str(ROOT / "scripts/check_gnani.py")], cwd=ROOT,
            text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=240)
        if result.stdout: print(result.stdout, end="")
        if result.stderr: print(result.stderr, end="", file=sys.stderr)
        if result.returncode:
            print("Live mode not started: Gnani check failed. Fix the provider setup or start with mock mode.")
            return 2

    port = free_port()
    if port is None:
        print("Could not find a free demo port between 8765 and 8794. Run stop_demo or free a port.")
        return 2
    url = f"http://localhost:{port}"
    child_env = os.environ.copy()
    command = [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(port)]
    process = subprocess.Popen(command, cwd=ROOT, env=child_env, stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    MANIFEST.write_text(json.dumps({"pid": process.pid, "launcher_pid": os.getpid(), "port": port, "url": url, "mode": args.mode}), encoding="utf-8")
    try:
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline and process.poll() is None:
            if health_ok(url): break
            time.sleep(.25)
        else:
            print("Backend did not become healthy. Check Python dependencies and try again.")
            return 1

        print(f"\nYojanaSuno local demo · mode: {args.mode} · port: {port}")
        print(f"Open: {url}\nPress Ctrl+C to stop.\n")
        preflight = [sys.executable, str(ROOT / "scripts/preflight.py"), "--quick", "--mode", args.mode,
                     "--port", str(port), "--base-url", url]
        if args.mode == "live": preflight.append("--live-roundtrip-done")
        result = subprocess.run(preflight, cwd=ROOT, env=child_env)
        if result.returncode:
            print("Demo not opened because preflight failed.")
            return 1
        if not args.no_browser: webbrowser.open(url)
        while process.poll() is None: time.sleep(.5)
        return process.returncode or 0
    except KeyboardInterrupt:
        print("\nStopping YojanaSuno…")
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        MANIFEST.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
