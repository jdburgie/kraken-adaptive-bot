#!/usr/bin/env bash
set -euo pipefail
# Local dev runner — activates venv if present, then starts the bot
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
python -m bots.main
