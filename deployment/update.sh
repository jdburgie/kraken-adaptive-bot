#!/usr/bin/env bash
# Deploy latest code from claude/adaptive-bot and restart the bot.
# Run from the EC2 instance: ./deployment/update.sh
set -euo pipefail

INSTALL_DIR="/home/ubuntu/kraken-adaptive-bot"
BRANCH="claude/adaptive-bot"
SERVICE="crypto-bot"

echo "Pulling latest code..."
cd "$INSTALL_DIR"
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"

echo "Updating dependencies..."
.venv/bin/pip install -r requirements.txt -q

echo "Restarting service..."
sudo systemctl restart "$SERVICE"
sleep 2
sudo systemctl status "$SERVICE" --no-pager

echo ""
echo "Done. Watch logs with:"
echo "  sudo journalctl -u $SERVICE -f"
