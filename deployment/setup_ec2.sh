#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# EC2 setup script for kraken-adaptive-bot
# Run once on a fresh Ubuntu 22.04/24.04 instance:
#
#   chmod +x setup_ec2.sh && ./setup_ec2.sh
#
# After it finishes:
#   1. Edit /home/ubuntu/kraken-adaptive-bot/.env  (add your Kraken API keys)
#   2. sudo systemctl start crypto-bot
#   3. sudo journalctl -u crypto-bot -f            (watch the logs)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO="https://github.com/jdburgie/kraken-adaptive-bot.git"
BRANCH="claude/adaptive-bot"
INSTALL_DIR="/home/ubuntu/kraken-adaptive-bot"
SERVICE_NAME="crypto-bot"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Kraken Adaptive Bot — EC2 Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. System dependencies ────────────────────────────────────────────────────
echo ""
echo "[1/6] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv git

# ── 2. Clone / update repo ────────────────────────────────────────────────────
echo ""
echo "[2/6] Cloning repo (branch: $BRANCH)..."
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "  Repo already exists — pulling latest..."
    cd "$INSTALL_DIR"
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
else
    git clone --branch "$BRANCH" "$REPO" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ── 3. Python virtual environment ─────────────────────────────────────────────
echo ""
echo "[3/6] Creating virtual environment..."
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
echo "  Dependencies installed."

# ── 4. .env file ──────────────────────────────────────────────────────────────
echo ""
echo "[4/6] Setting up .env..."
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    chmod 600 "$INSTALL_DIR/.env"   # owner-only read
    echo "  Created .env from .env.example"
    echo ""
    echo "  ┌─────────────────────────────────────────────────┐"
    echo "  │  ACTION REQUIRED: edit your .env file           │"
    echo "  │  nano $INSTALL_DIR/.env  │"
    echo "  │  Set: KRAKEN_API_KEY, KRAKEN_API_SECRET         │"
    echo "  │  Set: DRY_RUN=false  when ready to go live      │"
    echo "  └─────────────────────────────────────────────────┘"
else
    echo "  .env already exists — skipping (not overwritten)."
fi

# ── 5. Systemd service ────────────────────────────────────────────────────────
echo ""
echo "[5/6] Installing systemd service..."
sudo cp "$INSTALL_DIR/deployment/crypto-bot.service" "/etc/systemd/system/$SERVICE_NAME.service"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
echo "  Service installed and enabled (will start on boot)."

# ── 6. Logrotate ──────────────────────────────────────────────────────────────
echo ""
echo "[6/6] Configuring log rotation..."
sudo tee /etc/logrotate.d/crypto-bot > /dev/null << 'LOGROTATE'
/var/log/crypto-bot.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
}
LOGROTATE
echo "  Logrotate configured."

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Next steps:"
echo ""
echo "  1. Add your Kraken API keys:"
echo "     nano $INSTALL_DIR/.env"
echo ""
echo "  2. Run backtest first (uses public data, no keys needed):"
echo "     cd $INSTALL_DIR"
echo "     .venv/bin/python -m bots.backtest"
echo ""
echo "  3. Start the bot in DRY RUN mode (default — no real orders):"
echo "     sudo systemctl start $SERVICE_NAME"
echo "     sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "  4. When satisfied, set DRY_RUN=false in .env and restart:"
echo "     sudo systemctl restart $SERVICE_NAME"
echo ""
echo "  Useful commands:"
echo "    sudo systemctl status $SERVICE_NAME    # is it running?"
echo "    sudo systemctl stop $SERVICE_NAME      # stop the bot"
echo "    sudo journalctl -u $SERVICE_NAME -f    # live logs"
echo "    sudo journalctl -u $SERVICE_NAME --since '1 hour ago'"
