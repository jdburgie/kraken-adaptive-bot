#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/../.venv/bin/python"
cd "$SCRIPT_DIR/.."
"$VENV" -m bots.backtest "$@"
