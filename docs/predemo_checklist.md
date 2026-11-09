# YojanaSuno pre-demo checklist

## T–24 hours

- Keep `requirements-demo.txt` and the virtual environment stable. Avoid dependency, OS, and browser updates before the demo.
- Record a short backup video of a successful mock-mode walkthrough and keep it locally available.
- Practice a cold start from a closed terminal using `run_demo.bat` on Windows or `./run_demo.sh` on macOS/Linux.
- Run `python scripts/preflight.py --base-url http://localhost:<port> --port <port>` after the app is started; review every `WARN` and `FAIL`.
- If you plan to use live voice, run `run_demo.bat live` / `./run_demo.sh live` once and verify the Gnani round trip in all four languages. Keep mock mode as the fallback.

## T–10 minutes

- Start with `run_demo.bat` (Windows) or `./run_demo.sh` (macOS/Linux). Use `mock` for the most reliable run.
- Run `python scripts/preflight.py --quick --base-url http://localhost:<port> --port <port>` using the port printed by the launcher.
- Confirm microphone permission for `localhost` in Chrome or Edge, then test once. Confirm speaker volume and the audio output device.
- Close unrelated tabs, `.env` files, provider dashboards, and terminals that might expose sensitive configuration.
- Keep a phone hotspot ready in case the venue network fails. Mock mode does not need internet for voice processing.

## If something fails

| Problem | Action |
|---|---|
| Microphone is not working | Paste a pre-typed sentence from [demo_sentences.md](demo_sentences.md) into the text box. |
| Live API is failing | Stop the live run and restart with `run_demo.bat mock` or `./run_demo.sh mock`. |
| Port is busy | Run `stop_demo.bat` / `./stop_demo.sh`, then start again; the launcher also chooses a free fallback port. |
| Browser blocks microphone | Check the site permission for `localhost` in Chrome/Edge and reload the page. |
| Backend does not become healthy | Run `python scripts/preflight.py` and use the mock launcher; show the backup video if the laptop remains unavailable. |

**Say when switching to mock:** “The live voice service is having trouble, so I’m switching to the offline demo mode. The scheme check and next-step guidance are still available.”
