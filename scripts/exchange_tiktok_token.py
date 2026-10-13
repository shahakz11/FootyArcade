#!/usr/bin/env python3
"""
scripts/exchange_tiktok_token.py

Interactive helper CLI to guide TikTok OAuth 2.0 Authorization Code exchange.
1. Generates the authorization URL to grant permissions (video.upload, video.publish, user.info.basic).
2. Prompts the user or accepts the authorization `code` via CLI argument.
3. Exchanges authorization code for long-lived access_token and refresh_token.
4. Saves tokens directly into private/tiktok_config.json.
5. Verifies the connection and prints the connected TikTok creator profile.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

PRIVATE_DIR = os.path.join(BASE_DIR, "private")
CONFIG_FILE = os.path.join(PRIVATE_DIR, "tiktok_config.json")

DEFAULT_SCOPES = "user.info.basic,video.upload,video.publish"

def load_or_init_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(config):
    os.makedirs(PRIVATE_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

def generate_auth_url(client_key, redirect_uri, scopes=DEFAULT_SCOPES, state="playmaker_oauth_state"):
    """
    Constructs the TikTok OAuth v2 authorization URL.
    https://www.tiktok.com/v2/auth/authorize/
    """
    params = {
        "client_key": client_key,
        "scope": scopes,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state
    }
    return f"https://www.tiktok.com/v2/auth/authorize/?{urllib.parse.urlencode(params)}"

def exchange_code_for_tokens(client_key, client_secret, code, redirect_uri):
    """
    Exchanges authorization code for access_token and refresh_token.
    POST https://open.tiktokapis.com/v2/oauth/token/
    grant_type=authorization_code
    """
    url = "https://open.tiktokapis.com/v2/oauth/token/"
    payload = urllib.parse.urlencode({
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code.strip(),
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        raise RuntimeError(f"TikTok token exchange HTTP error ({e.code}): {err_msg}")
    except Exception as e:
        raise RuntimeError(f"TikTok token exchange request failed: {e}")

    token_data = data.get("data", data)
    access_token = token_data.get("access_token")
    if not access_token:
        err_desc = data.get("error_description", data.get("message", json.dumps(data)))
        raise RuntimeError(f"Failed to receive access token: {err_desc}")

    now_ts = int(time.time())
    expires_in = token_data.get("expires_in", 86400)
    refresh_expires_in = token_data.get("refresh_expires_in", 31536000)

    result = {
        "client_key": client_key,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "access_token": access_token,
        "refresh_token": token_data.get("refresh_token", ""),
        "open_id": token_data.get("open_id", ""),
        "expires_at": now_ts + int(expires_in),
        "refresh_expires_at": now_ts + int(refresh_expires_in)
    }

    return result

def main():
    parser = argparse.ArgumentParser(description="Exchange TikTok OAuth Authorization Code for Access & Refresh Tokens")
    parser.add_argument("--code", type=str, help="TikTok authorization code from redirect URL")
    parser.add_argument("--client-key", type=str, help="TikTok App Client Key")
    parser.add_argument("--client-secret", type=str, help="TikTok App Client Secret")
    parser.add_argument("--redirect-uri", type=str, help="Redirect URI configured in TikTok Developer Portal")

    args = parser.parse_args()
    config = load_or_init_config()

    client_key = args.client_key or config.get("client_key")
    client_secret = args.client_secret or config.get("client_secret")
    redirect_uri = args.redirect_uri or config.get("redirect_uri", "https://playmaker.best/")

    if not client_key:
        client_key = input("Enter TikTok Client Key: ").strip()
    if not client_secret:
        client_secret = input("Enter TikTok Client Secret: ").strip()

    if not client_key or not client_secret:
        print("❌ client_key and client_secret are required!")
        sys.exit(1)

    code = args.code
    if not code:
        auth_url = generate_auth_url(client_key, redirect_uri)
        print("\n" + "=" * 70)
        print("              🔗 TIKTOK OAUTH AUTHORIZATION STEP")
        print("=" * 70)
        print("1. Open the following URL in your web browser to authorize Playmaker:")
        print(f"\n{auth_url}\n")
        print(f"2. After approving, you will be redirected to: {redirect_uri}?code=XXXX&scopes=...")
        print("3. Copy the 'code' query parameter from the browser URL bar.")
        print("-" * 70)
        try:
            code = input("Paste the 'code' parameter here: ").strip()
        except EOFError:
            print("\n❌ No code provided in non-interactive environment.")
            sys.exit(1)

    if not code:
        print("❌ No authorization code provided.")
        sys.exit(1)

    print("\n🔄 Exchanging authorization code for access and refresh tokens...")
    try:
        updated_config = exchange_code_for_tokens(client_key, client_secret, code, redirect_uri)
        # Merge with existing config
        config.update(updated_config)
        save_config(config)
        print(f"✅ Saved tokens to {CONFIG_FILE}")

        # Verification step
        print("\n🔍 Verifying TikTok creator profile...")
        from scripts.tiktok_uploader import check_connection
        profile = check_connection(silent=False)
        print(f"🎉 Fully authenticated with TikTok account @{profile.get('username')}!")

    except Exception as e:
        print(f"❌ Token exchange failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
