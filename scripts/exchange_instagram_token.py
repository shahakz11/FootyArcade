#!/usr/bin/env python3
"""
scripts/exchange_instagram_token.py

Exchanges a short-lived Meta User Access Token for a Long-Lived / Permanent Page Access Token.
Updates private/instagram_config.json and automatically syncs it to GitHub Actions Repository Secrets.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

PRIVATE_DIR = os.path.join(BASE_DIR, "private")
CONFIG_FILE = os.path.join(PRIVATE_DIR, "instagram_config.json")

def exchange_and_save_token(input_token):
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ Configuration file not found at {CONFIG_FILE}")
        return False

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    app_id = config.get("app_id")
    app_secret = config.get("app_secret")
    page_id = config.get("page_id")

    if not app_id or not app_secret:
        print("❌ app_id or app_secret missing from private/instagram_config.json")
        return False

    input_token = input_token.strip()
    print("🔄 Step 1: Exchanging token for a 60-Day Long-Lived User Token...")

    exchange_url = (
        f"https://graph.facebook.com/v21.0/oauth/access_token?"
        f"grant_type=fb_exchange_token&"
        f"client_id={app_id}&"
        f"client_secret={app_secret}&"
        f"fb_exchange_token={input_token}"
    )

    try:
        req = urllib.request.Request(exchange_url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            long_lived_user_token = data.get("access_token")
            expires_in = data.get("expires_in", 0)
            print(f"  ✅ Received Long-Lived User Token (expires in ~{expires_in // 86400} days).")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"  ⚠️ Could not exchange token via oauth endpoint (HTTP {e.code}): {err_body}")
        print("  ℹ️ Will attempt to use the provided token directly.")
        long_lived_user_token = input_token
    except Exception as e:
        print(f"  ⚠️ Exchange error: {e}")
        long_lived_user_token = input_token

    print(f"\n🔄 Step 2: Extracting Permanent Page Access Token for Page ID {page_id}...")
    page_url = f"https://graph.facebook.com/v21.0/{page_id}?fields=access_token,name,instagram_business_account{{id,username}}&access_token={long_lived_user_token}"
    
    final_token = long_lived_user_token
    ig_user_id = config.get("ig_user_id")

    try:
        req = urllib.request.Request(page_url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            p_data = json.loads(resp.read().decode("utf-8"))
            page_token = p_data.get("access_token")
            ig_account = p_data.get("instagram_business_account", {})
            if page_token:
                final_token = page_token
                print(f"  ✅ Extracted Page Access Token for Page '{p_data.get('name')}' (Never expires).")
            if ig_account:
                ig_user_id = ig_account.get("id", ig_user_id)
                print(f"  ✅ Connected to Instagram Business Account: @{ig_account.get('username')} (ID: {ig_user_id})")
    except Exception as e:
        print(f"  ⚠️ Could not fetch Page token: {e}. Using Long-Lived User token.")

    # Update config file
    config["access_token"] = final_token
    if ig_user_id:
        config["ig_user_id"] = ig_user_id

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print(f"\n💾 Saved active token to {CONFIG_FILE}")

    # Step 3: Automatically sync to GitHub Secrets
    print("\n🔄 Step 3: Syncing updated token to GitHub Actions Secrets...")
    try:
        from scripts.sync_secrets_to_github import sync_secrets
        sync_secrets()
    except Exception as e:
        print(f"⚠️ Could not auto-sync to GitHub Secrets: {e}")

    print("\n✨ Setup complete! You can now run:")
    print("  python3 scripts/auto_reply_comments.py")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        token_arg = sys.argv[1]
    else:
        token_arg = input("Paste your Meta Graph API User Token: ").strip()
    
    if token_arg:
        exchange_and_save_token(token_arg)
    else:
        print("❌ No token provided.")
