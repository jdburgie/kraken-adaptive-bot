#!/usr/bin/env bash
set -euo pipefail

# Detect user
if [ -f /etc/os-release ]; then
    . /etc/os-release
    [ "${ID:-}" = "amzn" ] && BOT_USER="ec2-user" || BOT_USER="ubuntu"
else
    BOT_USER="ec2-user"
fi

INSTALL_DIR="/home/$BOT_USER/kraken-adaptive-bot"
BRANCH="claude/adaptive-bot"
SERVICE="crypto-bot"

echo "Pulling latest from $BRANCH..."
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
echo "Live logs: sudo journalctl -u $SERVICE -f"
