#!/bin/bash

# Navigate to project directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/.." || exit 1

echo "======================================================="
echo "🎬 PLAYMAKER DAILY VIDEO GENERATOR (DAY 0)"
echo "======================================================="
echo ""

# 1. Ensure local HTTP server is running on port 8080
if ! lsof -i :8080 > /dev/null; then
    echo "🌐 Starting local web server on port 8080..."
    python3 -m http.server 8080 > /dev/null 2>&1 &
    SERVER_PID=$!
    sleep 2
else
    echo "🌐 Web server is already running on port 8080."
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
