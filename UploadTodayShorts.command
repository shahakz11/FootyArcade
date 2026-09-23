#!/bin/bash
# ==============================================================================
# UploadTodayShorts.command
# Double-clickable macOS launcher: Renders & schedules today's Shorts & Reels
# ==============================================================================

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
[ -f "$HOME/.zshrc" ] && source "$HOME/.zshrc" > /dev/null 2>&1

echo "=========================================================="
echo "    ⚽  PLAYMAKER — DAILY SHORTS & REELS LIVE PIPELINE"
echo "=========================================================="
echo "1. Checks YouTube Channel & Instagram Business Account"
echo "2. Renders 9:16 vertical videos with high-energy audio"
echo "3. Uploads LIVE IMMEDIATELY (no queue delays / no sample pool starvation)"
echo "   • Midday: Top Transfers"
echo "   • Evening: Transfer Destination"
echo "=========================================================="
echo ""

# 1. Verify YouTube authentication / channel
echo "🔍 Checking YouTube authentication..."
python3 scripts/youtube_uploader.py --channel
YT_STATUS=$?

if [ $YT_STATUS -ne 0 ]; then
    echo "⚠️ Setup required: Browser will open once for YouTube authentication."
fi

echo ""

# 2. Verify Instagram authentication
echo "🔍 Checking Instagram authentication..."
python3 scripts/instagram_uploader.py --check
IG_STATUS=$?

if [ $IG_STATUS -ne 0 ]; then
    echo "⚠️ Instagram check failed. Please check private/instagram_config.json."
fi

# 3. Auto-sync valid tokens to GitHub Secrets
python3 scripts/sync_secrets_to_github.py > /dev/null 2>&1

echo ""
read -p "Press [Enter] to start batch render & upload (or Ctrl+C to cancel)..."
echo ""

python3 scripts/upload_daily_shorts.py

echo ""
echo "Finished! Press any key to close this window..."
read -n 1 -s -r
