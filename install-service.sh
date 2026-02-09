#!/usr/bin/env bash
# install-service.sh - Install totem-daemon as a systemd user service
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/totem-daemon.service"

echo "Installing totem-daemon systemd user service..."

mkdir -p "$SERVICE_DIR"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Totem Hardware Daemon
After=default.target

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/env/bin/python $SCRIPT_DIR/totem_daemon.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF

echo "  Created $SERVICE_FILE"

systemctl --user daemon-reload
echo "  Reloaded systemd user daemon."

systemctl --user enable totem-daemon.service
echo "  Enabled totem-daemon service (auto-starts on boot)."

systemctl --user start totem-daemon.service
echo "  Started totem-daemon service."

echo ""
echo "Install complete. The daemon is now running."
echo "Run 'systemctl --user status totem-daemon.service' to verify."
