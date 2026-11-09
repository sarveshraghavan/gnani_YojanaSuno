#!/usr/bin/env bash
set -euo pipefail

# HF_TOKEN must already be set in this shell/secret manager. It is never saved here.
: "${HF_TOKEN:?Set HF_TOKEN in your shell after accepting the Hugging Face model conditions}"
exec vllm serve gnani/gnani-evon-v3.3-30B-A3B \
  --served-model-name model \
  --max-model-len 8192 \
  --port "${EVON_PORT:-8001}" \
  --trust-remote-code \
  --reasoning-parser nano_v3
