#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# EC2 setup script for kraken-adaptive-bot
# Supports: Amazon Linux 2023 (ec2-user) and Ubuntu 22/24 (ubuntu)
#
# Run once on a fresh instance:
#   chmod +x setup_ec2.sh && ./setup_ec2.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO="https://github.com/jdburgie/kraken-adaptive-bot.git"
BRANCH="claude/adaptive-bot"
SERVICE_NAME="crypto-bot"

# ── Detect distro and set user ────────────────────────────────────────────────
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO="${ID:-unknown}"
else
    DISTRO="unknown"
fi

if [ "$DISTRO" = "amzn" ]; then
    BOT_USER="ec2-user"
    PKG_MGR="dnf"
else
    BOT_USER="ubuntu"
    PKG_MGR="apt-get"
fi

INSTALL_DIR="/home/$BOT_USER/kraken-adaptive-bot"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Kraken Adaptive Bot — EC2 Setup"
echo "  Distro : $DISTRO  |  User: $BOT_USER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. System dependencies ────────────────────────────────────────────────────
echo ""
echo "[1/6] Installing system packages..."
if [ "$PKG_MGR" = "dnf" ]; then
    sudo dnf update -y -q
    sudo dnf install -y -q python3 python3-pip git
else
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3 python3-pip python3-venv git
fi
echo "  Done."

# ── 2. Clone / update repo ────────────────────────────────────────────────────
echo ""
echo "[2/6] Cloning repo (branch: $BRANCH)..."
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "  Repo exists — pulling latest..."
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
    chmod 600 "$INSTALL_DIR/.env"
    echo "  Created .env — you must edit it before starting the bot."
else
    echo "  .env already exists — not overwritten."
fi

# ── 5. Systemd service ────────────────────────────────────────────────────────
echo ""
echo "[5/6] Installing systemd service..."

# Rewrite service file with correct user and paths for this instance
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << UNIT
[Unit]
Description=Kraken Adaptive Crypto Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$BOT_USER
Group=$BOT_USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/.venv/bin/python -m bots.main
Restart=on-failure
RestartSec=30
StartLimitIntervalSec=300
StartLimitBurst=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=crypto-bot

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
echo "  Service installed and enabled."

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
echo "  Done."

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  1. Add your Kraken API keys:"
echo "     nano $INSTALL_DIR/.env"
echo ""
echo "  2. Run backtest (no API keys needed):"
echo "     cd $INSTALL_DIR && ./scripts/run_backtest.sh"
echo ""
echo "  3. Start in dry run (default — no real orders):"
echo "     sudo systemctl start $SERVICE_NAME"
echo "     sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "  4. Go live — edit .env, set DRY_RUN=false, restart:"
echo "     sudo systemctl restart $SERVICE_NAME"
echo ""
echo "  Useful commands:"
echo "    sudo systemctl status $SERVICE_NAME"
echo "    sudo systemctl stop   $SERVICE_NAME"
echo "    sudo journalctl -u $SERVICE_NAME -f"
echo "    sudo journalctl -u $SERVICE_NAME --since '1 hour ago'"
