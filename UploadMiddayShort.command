#!/bin/bash
# ==============================================================================
# UploadMiddayShort.command
# Double-clickable macOS launcher: Renders & immediately uploads Top Transfers
# ==============================================================================

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
[ -f "$HOME/.zshrc" ] && source "$HOME/.zshrc" > /dev/null 2>&1

echo "=========================================================="
echo "    ⚽  PLAYMAKER — MIDDAY SHORT UPLOAD (TOP TRANSFERS)"
echo "=========================================================="
echo "1. Checks YouTube Channel & Instagram Account"
echo "2. Renders 9:16 vertical video with commentary & SFX"
echo "3. Uploads LIVE IMMEDIATELY to YouTube Shorts & Instagram Reels"
echo "=========================================================="
echo ""

# 1. Verify YouTube authentication
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

echo ""
read -p "Press [Enter] to render & upload Top Transfers LIVE now (or Ctrl+C to cancel)..."
echo ""

python3 scripts/upload_daily_shorts.py --midday

echo ""
echo "Finished! Press any key to close this window..."
read -n 1 -s -r
