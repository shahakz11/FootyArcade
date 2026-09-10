#!/bin/bash
# ==============================================================================
# StartServer.command
# Double-clickable macOS launcher to test Playmaker games locally in browser
# ==============================================================================

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Source environment to ensure python3 is found
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
[ -f "$HOME/.zshrc" ] && source "$HOME/.zshrc" > /dev/null 2>&1

PORT=8000

# Check if port 8000 is occupied, if so try 8080
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    PORT=8080
fi

echo "=========================================================="
echo "    ⚽  Starting Playmaker Local Web Server..."
echo "=========================================================="
echo "🌐 URL: http://localhost:$PORT"
echo "🎮 Games:"
echo "   - Top Transfers:        http://localhost:$PORT/games/top_transfers.html"
echo "   - Transfer Destination: http://localhost:$PORT/games/transfer_destination.html"
echo "   - Club Connect:         http://localhost:$PORT/games/club_connect.html"
echo "   - Player Chain:         http://localhost:$PORT/games/player_chain.html"
echo "   - Top Scorers:          http://localhost:$PORT/games/top_scorers.html"
echo ""
echo "💡 Press Ctrl+C in this terminal window to stop the server."
echo "=========================================================="

# Automatically open the browser after a brief delay
(sleep 1 && open "http://localhost:$PORT") &

python3 -m http.server $PORT
