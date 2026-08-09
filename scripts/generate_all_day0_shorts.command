#!/bin/bash

# Navigate to project directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/.." || exit 1

echo "======================================================="
echo "🎬 PLAYMAKER DAILY VIDEO GENERATOR (DAY 0)"
echo "======================================================="
echo ""

# 1. Health check local HTTP server on port 8080
check_server() {
    curl -s -o /null -w "%{http_code}" http://localhost:8080/games/top_transfers.html 2>/dev/null
}

HTTP_CODE=$(check_server)

if [ "$HTTP_CODE" != "200" ]; then
    echo "🌐 Starting clean local web server on port 8080..."
    # If port 8080 has a zombie or broken listener, free it up
    PORT_PID=$(lsof -t -i :8080 2>/dev/null)
    if [ -n "$PORT_PID" ]; then
        echo "🧹 Clearing stale server process (PID $PORT_PID)..."
        kill -9 $PORT_PID 2>/dev/null || true
        sleep 1
    fi
    # Start fresh server
    python3 -m http.server 8080 > /dev/null 2>&1 &
    sleep 2
else
    echo "🌐 Web server is healthy and responding on port 8080."
fi

# 2. Re-compile daily game puzzles for today (Day 0)
echo "⚙️  Compiling today's game puzzles..."
python3 fetch_daily.py

echo ""
echo "📹 Generating video shorts for all active games..."
echo "-------------------------------------------------------"

# 3. Generate videos for all active games for Day 0
python3 record_real_ui_short.py --game top_transfers --day 0
python3 record_real_ui_short.py --game transfer_destination --day 0
python3 record_real_ui_short.py --game top_scorers --day 0
python3 record_real_ui_short.py --game club_connect --day 0

echo ""
echo "======================================================="
echo "✨ ALL TODAY (DAY 0) VIDEOS GENERATED SUCCESSFULLY!"
echo "======================================================="
echo ""

# Keep window open briefly if clicked in Finder
read -t 5 -p "Press enter to exit..." || true
