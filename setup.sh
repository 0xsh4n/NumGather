#!/usr/bin/env bash
set -euo pipefail

echo "[*] Installing NumGather 2.0 dependencies..."
pip3 install -r requirements.txt

echo
echo "[*] Done. Examples:"
echo "    python3 NumGather.py +919876543210"
echo "    python3 NumGather.py +14155552671 --ollama"
echo "    python3 NumGather.py --list-models"
echo
echo "[*] Optional — Ollama (local LLM reasoning):"
echo "    https://ollama.com  →  install, then:"
echo "    ollama pull llama3.2"
echo "    # or a reasoning model: ollama pull deepseek-r1"
echo

if [[ "${1:-}" == "--run" ]]; then
  python3 NumGather.py
fi
