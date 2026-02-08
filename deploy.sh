#!/usr/bin/env bash
# deploy.sh - Copy skills and restart the Totem daemon service
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_SRC="$SCRIPT_DIR/skills/totem"
SKILL_DST="$HOME/.openclaw/skills/totem"

echo "Copying skill to $SKILL_DST ..."
mkdir -p "$SKILL_DST"
cp -r "$SKILL_SRC"/. "$SKILL_DST"
echo "  Done."

echo "Restarting totem-daemon service ..."
systemctl --user restart totem-daemon.service
echo "  Done."

echo "Deploy complete."
