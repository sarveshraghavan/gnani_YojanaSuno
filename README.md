# YojanaSuno

Voice first guide to a small set of Indian farm schemes. The prototype keeps scheme decisions in versioned data and Python rules; speech and language models can only transcribe, extract fields, and explain the deterministic result.

See the one-page [YojanaSuno solution pitch](docs/solution_pitch.md).

## Run locally

1. Use Python 3.11 or newer.
2. `python -m venv .venv` then activate it.
3. `pip install -r requirements.txt`
4. Copy `backend/.env.example` to `backend/.env`. Both mock providers are enabled by default. Never place API keys in source, examples, or Git; use a rotated key from a local secret manager/environment when switching providers on.
5. `uvicorn backend.app.main:app --reload` and open http://127.0.0.1:8000.

Opening `frontend/index.html` directly from disk will load its relative CSS and JavaScript, but scheme checks and voice APIs need the FastAPI server running at `http://127.0.0.1:8000`.

## Running the demo locally

For a one-laptop demo, start from the repository folder with `run_demo.bat` on Windows or `./run_demo.sh` on macOS/Linux. Both default to `mock`; use `run_demo.bat live` / `./run_demo.sh live` only after the local Gnani settings pass the live voice check. The launcher creates `.venv` and installs the exact versions in `requirements-demo.txt` when needed, selects a free port in the 8765–8794 range, waits for `/api/health`, runs quick preflight checks, and opens the browser at `http://localhost:<port>`. Mode overrides apply to the launched process and do not edit `.env`. Press Ctrl+C to stop, or use `stop_demo.bat` / `./stop_demo.sh` to release the recorded port from another terminal.

For a full readiness check including offline tests, run `python scripts/preflight.py --base-url http://localhost:<port> --port <port>` after the launcher starts. For the quicker check used by the launcher, add `--quick`. Quick mode checks health, the served frontend, translation keys, and mock voice API turns in all four languages; full mode also runs the offline suite. Live mode checks the Gnani host and performs the round-trip check for Hindi, Tamil, Telugu, and English. See the [pre-demo checklist](docs/predemo_checklist.md) and [paste-ready demo sentences](docs/demo_sentences.md).

The microphone records a short clip, converts it to WAV in the browser, and sends it to `POST /api/voice`; that endpoint runs STT, the dialogue/rules flow, and TTS. In mock mode, STT returns a canned phrase and TTS returns silent WAV audio. Never enter Aadhaar or bank account numbers.

## Model roles

- **Prisma**: speech audio to transcript (`prisma-v3.0`, Hindi/Tamil/Telugu hints).
- **Evon**: optional structured slot extraction through a self-hosted OpenAI-compatible endpoint (`EVON_BASE_URL`, `EVON_API_KEY`, `EVON_MODEL`). It does not decide eligibility. With mock mode on, a conservative local extractor handles common demo phrases.
- **Rules engine**: evaluates the YAML registry and returns eligible, not eligible, or needs more information.
- **Timbre**: turns the final response into a playable WAV when Gnani credentials are configured.

## Important demo limitation

The included scheme cards are **illustrative demo rules**, not official eligibility advice. Real scheme rules, state notifications, seasons, and application windows must be reviewed against their official sources before public use. Every response is labeled accordingly and includes the official scheme portal for follow-up. The prototype does not collect Aadhaar numbers or submit applications.

## Configuration

Copy `backend/.env.example` to `backend/.env`; the latter is ignored by Git. API keys are read by the backend only and are never sent to the browser. `GNANI_API_KEY` is the API key ID used by the Vachana API. `USE_MOCK_VOICE=false` enables Prisma/Timbre only when that key is set. `USE_MOCK_LLM=false` enables Evon only when `EVON_BASE_URL` is set. Provider startup logs report only the active provider names, never credentials.

## Layout

- `backend/app/main.py`: API routes and model adapters
- `backend/app/eligibility/`: validated scheme models and deterministic rules
- `backend/schemes/`: editable scheme cards
- `frontend/`: single-page voice and text UI

## Eligibility engine

Run the engine tests from `backend/` with `pytest -q`. The standalone rules endpoint needs no voice or model keys:

```http
POST /api/check
Content-Type: application/json

{"slots":{"owns_land":true,"is_institutional_holder":false,"pays_income_tax":false},"language":"en-IN"}
```

It returns one versioned result per scheme with `eligible`, `not_eligible`, or `need_more_info`, along with missing slots, failed conditions, sources, next steps, and a `not_checked` list. When more information is needed, it also returns one `next_slot` and localized `next_question`. The browser sends a session ID so known slots carry across turns; session memory is temporary and kept in the running server process.

A positive result is only a preliminary screen. PM-KISAN's full exclusions and land record rules, PMFBY notifications, and PM-KUSUM state/component requirements need official confirmation. Hindi, Tamil, and Telugu question phrasing is a draft and should be checked by native speakers before a farmer-facing demo.

Additional scheme proposals are kept out of the active registry under `backend/schemes/drafts/` until reviewed and approved. Current proposals cover KCC, PM-Kisan Maandhan, and PMKSY Per Drop More Crop; they are unverified screens, not eligibility decisions. The landing page labels the broader scheme chips as a prototype preview.

The dialogue asks for confirmation before returning eligibility results. Saying no leads to a detail selector and re-asks only that slot. In-memory sessions expire after 30 minutes. Raw transcripts are redacted for long digit runs before extraction and are not stored in the session; only an allowlist of farm slots is retained. Land size is not collected because none of the current demo rules use it.

`backend/app/voice/` defines STT/TTS provider interfaces, fake STT with a canned transcript, fake TTS with a valid silent WAV, and async Prisma/Timbre adapters. The fake end-to-end flow runs in the test suite without Gnani credentials. The TTS voice defaults are documented locale-specific Timbre voices. `GNANI_TTS_VOICE` can override them; confirm that an override supports the selected language before using it. The suggested `sia` voice is not in Gnani's current v2.5 voice catalog, so it is not used by default.

## Live provider checks and reviewed translations

`python scripts/check_gnani.py` runs a live TTS→STT round-trip for three fixed phrases in each configured language and saves audio only under the ignored `tmp_audio/` directory. Similarity is a smoke signal, not an accuracy score. Add real recordings named `hi_1.wav`, `ta_1.wav`, `te_1.wav`, or `en_1.wav` to the ignored `samples/` folder and run `python scripts/transcribe_samples.py` for manual noisy-audio checks. Both scripts require `USE_MOCK_VOICE=false` and local configuration; they never print credentials.

Run `python scripts/export_review.py` to create CSV review sheets for fixture utterances and user-facing questions, disclosures, fallback messages, and landing-page text. Have a native speaker fill `reviewed_by` in the fixture notes, `review_date` is added on import, and put reviewed corrections in the correction column. `python scripts/import_review.py` prints a unified diff before it writes reviewed changes. Exported CSVs are ignored by Git; commit reviewed fixture changes and `backend/app/dialogue/review_strings.json` only after checking the diff. Eval reports separate reviewed and synthetic case counts.

## Scheme review, health, and checks

All scheme cards are currently unverified. See [the rule-by-rule source review](docs/scheme_verification.md); every API result and UI card carries an “Unverified draft” badge until a human confirms the current rules. `GET /api/health` reports app version, active provider names, and scheme versions without credentials. `/api/voice` logs only STT, dialogue, and TTS timing values.

Run `python eval/run_eval.py --extractor mock`, `--extractor evon`, or `--extractor both`; the last compares per-language extraction and lists disagreements in `eval/report.md`. Unreachable Evon falls back to the local mock extractor. Read [the demo walkthrough and limitations](docs/demo_script.md) before presenting the prototype. Evon serving notes are in [docs/evon.md](docs/evon.md).

## Testing languages

`backend/tests/language_cases.yaml` contains synthetic Hindi, Tamil, Telugu, and English scenarios. From `backend/`, run `pytest -q` for the offline text and API levels; live cases are tagged `live` and are skipped unless `USE_MOCK_VOICE=false` and the local settings expose a key. To opt into only live audio checks, run `pytest -q -m live`; they synthesize each safe fixture phrase, transcribe it back, and record round-trip similarity as a smoke signal, not an accuracy measure. Aadhaar-like fixture text is deliberately excluded from external calls. Add cases under the relevant language in the YAML with expected/forbidden slots, dialogue action, and `reviewed_by` metadata. A terminal table summarizes language × scenario outcomes. `eval/report.md` includes per-language fixture pass rates and reviewed-versus-synthetic counts; synthetic fixture scores are not field accuracy.

For consented recordings, see the [field-test protocol](docs/field_test_protocol.md) and [field_tests.csv template](field_tests.csv). Add `real_recording=true` in a row's notes only for real recordings, then run `python scripts/score_field_tests.py`; without tagged recordings, the report explicitly makes no field accuracy claim. Audio examples in `samples/` and live smoke audio in `tmp_audio/` remain ignored.

## Source archive

The [source registry](docs/sources/sources.json) lists official URLs. No source PDFs have been downloaded into the repository; document records and hashes stay empty until you place an official file in `docs/sources/`. Each rule's `source_ref` identifies a checked section where one was confirmed. Empty references remain explicit and do not mark a scheme verified.

## Secret scanning

Install pre-commit and run `pre-commit install` once; `.pre-commit-config.yaml` runs Gitleaks before commits. You can also run `pre-commit run --all-files`. A scan is a safeguard, not a substitute for keeping `.env` ignored and never pasting keys into chats or source files. If a key was exposed, rotate it at the provider.

# Voice configuration

Voice processing defaults to local mock providers. Prisma REST and Timbre REST use the documented `X-API-Key-ID` header and Vachana endpoint URLs. Keep `USE_MOCK_VOICE=true` until you've rotated the exposed credential and entered it through a local secret mechanism. STT audio is limited to 30 seconds. The documented TTS response is raw binary audio, not a base64 JSON object.

## Running Evon

Evon is optional and never determines eligibility. To run it locally, review and accept any model access conditions on [the Hugging Face model page](https://huggingface.co/gnani/gnani-evon-v3.3-30B-A3B), create an `HF_TOKEN` in your shell or secret manager (never commit it), then serve the model on Linux with a compatible GPU. The model card lists NVIDIA A100/H100-class GPUs and vLLM 0.12+; this model is not practical on a typical laptop.

Example using the model's vLLM flags with a shorter context for this prototype:

```bash
vllm serve gnani/gnani-evon-v3.3-30B-A3B \
  --served-model-name model \
  --max-model-len 8192 \
  --port 8000 \
  --trust-remote-code
```

Set `USE_MOCK_LLM=false`, `EVON_BASE_URL=http://localhost:8000/v1`, and `EVON_MODEL=model`. Set `EVON_API_KEY` only if your endpoint requires it. The extractor sends plain JSON extraction requests without tool calling and validates every returned slot before the rules engine sees it.

## Evaluation

Run the 124 synthetic extraction fixtures and 9 deterministic eligibility cases from the repository root:

```bash
python eval/run_eval.py
```

It prints extraction accuracy per language and eligibility accuracy for all schemes, then writes `eval/report.md`. This small fixture score is a smoke check, not a representative field accuracy claim.
