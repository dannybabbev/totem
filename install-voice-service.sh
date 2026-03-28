#!/usr/bin/env bash
# install-voice-service.sh - Install totem-voice as a systemd user service
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/totem-voice.service"

echo "Installing totem-voice systemd user service..."

mkdir -p "$SERVICE_DIR"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Totem Voice Assistant
After=totem-daemon.service

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
EnvironmentFile=-$SCRIPT_DIR/.env
ExecStart=$SCRIPT_DIR/env/bin/python $SCRIPT_DIR/voice.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

echo "  Created $SERVICE_FILE"

systemctl --user daemon-reload
echo "  Reloaded systemd user daemon."

systemctl --user enable totem-voice.service
echo "  Enabled totem-voice service (auto-starts on boot)."

systemctl --user start totem-voice.service
echo "  Started totem-voice service."

echo ""
echo "Install complete. The voice assistant is now running."
echo "Run 'systemctl --user status totem-voice.service' to verify."
echo "Run 'journalctl --user -u totem-voice.service -f' to see logs."
