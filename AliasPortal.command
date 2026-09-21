#!/bin/bash
# ==============================================================================
# AliasPortal.command
# Double-clickable macOS launcher for Playmaker Team & Player Aliases Maker Portal
# ==============================================================================

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Source environment to ensure python3 is found
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
[ -f "$HOME/.zshrc" ] && source "$HOME/.zshrc" > /dev/null 2>&1

PORT=5050

# Check if port 5050 is occupied, if so try 5055
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    PORT=5055
fi

echo "=========================================================="
echo "    ⚽  Starting Playmaker Aliases & Dropdown Portal..."
echo "=========================================================="
echo "🌐 Portal URL: http://localhost:$PORT"
echo "🛠  Config:     data/aliases_config.json"
echo ""
echo "💡 Press Ctrl+C in this terminal window to stop the portal."
echo "=========================================================="

# Check Flask dependency
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Installing required dependency 'flask'..."
    pip3 install flask
fi

# Automatically open the browser after a brief delay
(sleep 1.2 && open "http://localhost:$PORT") &

PORT=$PORT python3 scripts/alias_portal.py
