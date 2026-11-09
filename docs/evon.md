# Optional Evon self-hosting

The model repository is [`gnani/gnani-evon-v3.3-30B-A3B`](https://huggingface.co/gnani/gnani-evon-v3.3-30B-A3B); the card's short quick-start alias does not change the canonical repository. Accept any Hugging Face access conditions first. Serving it requires Linux, vLLM 0.12+, and an A100/H100-class GPU with suitable memory. It is not intended for an ordinary laptop.

Set `HF_TOKEN` in the shell or a secret manager, then run `bash scripts/serve_evon.sh`. The script reads the token from the process environment and never writes it. It serves on port 8001 by default. Configure `EVON_BASE_URL=http://localhost:8001/v1`, `EVON_MODEL=model`, and `USE_MOCK_LLM=false` locally. Evon extracts fields only; deterministic Python rules remain responsible for screening.

Run `python scripts/check_evon.py` to check Hindi, Tamil, Telugu, and English extraction. It prints only extracted farm slots and latency. If the endpoint is unreachable, the app retains its conservative local fallback. Evon is optional and not required to run the tests or demo.
