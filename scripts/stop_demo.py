"""Stop the server started by scripts/demo.py and release its local port."""
from __future__ import annotations
import json, os, signal, socket, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/".demo_session.json"

def main() -> int:
    if not MANIFEST.exists():
        print("No YojanaSuno demo session is recorded.")
        return 0
    try:
        data=json.loads(MANIFEST.read_text(encoding="utf-8"));pid=int(data["pid"]);launcher_pid=int(data.get("launcher_pid",0));port=int(data["port"])
    except Exception:
        print("Demo session file is invalid; remove .demo_session.json after checking no demo server is running.")
        return 1
    try:
        if os.name=="nt":
            target = launcher_pid or pid
            subprocess.run(["taskkill","/PID",str(target),"/T","/F"],capture_output=True,timeout=8)
        else:
            os.kill(pid,signal.SIGTERM)
            if launcher_pid and launcher_pid != os.getpid(): os.kill(launcher_pid,signal.SIGTERM)
    except (ProcessLookupError, OSError, subprocess.TimeoutExpired): pass
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1",port))!=0: break
        time.sleep(.2)
    else:
        print(f"Could not confirm port {port} was released; stop the recorded process manually.")
        return 1
    MANIFEST.unlink(missing_ok=True)
    print(f"YojanaSuno stopped; port {port} is free.")
    return 0

if __name__=="__main__":raise SystemExit(main())
