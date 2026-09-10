#!/bin/bash
# ==============================================================================
# UploadTodayShorts.command
# Double-clickable macOS launcher: Renders & schedules all of today's Shorts
# ==============================================================================

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
[ -f "$HOME/.zshrc" ] && source "$HOME/.zshrc" > /dev/null 2>&1

echo "=========================================================="
echo "    ⚽  PLAYMAKER — DAILY SHORTS AUTOMATED BATCH"
echo "=========================================================="
echo "1. Checks authenticated YouTube Channel"
echo "2. Renders 9:16 Shorts with audio for all 5 games"
echo "3. Publishes #1 immediately, and schedules #2..#5 with 1-hr gaps"
echo "=========================================================="
echo ""

# First verify authentication / channel
python3 scripts/youtube_uploader.py --channel
AUTH_STATUS=$?

if [ $AUTH_STATUS -ne 0 ]; then
    echo "⚠️ Setup required: Browser will open once for YouTube authentication."
fi

echo ""
read -p "Press [Enter] to start batch render & upload (or Ctrl+C to cancel)..."
echo ""

python3 scripts/upload_daily_shorts.py

echo ""
echo "Finished! Press any key to close this window..."
read -n 1 -s -r
