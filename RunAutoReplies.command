#!/bin/bash
cd "$(dirname "$0")"
echo "🤖 Starting Playmaker Multi-Platform Auto-Reply Engine (YouTube & Instagram)..."
python3 scripts/auto_reply_comments.py
echo ""
read -p "Press Enter to exit..."
