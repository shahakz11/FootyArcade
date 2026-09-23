#!/usr/bin/env python3
"""
Syncs local YouTube & Instagram API secrets and tokens to GitHub Repository Secrets
so that GitHub Actions workflows (Daily Shorts & Reels Auto-Publisher) always stay authenticated.
"""

import os
import sys
import json
import base64
import subprocess
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIVATE_DIR = os.path.join(BASE_DIR, "private")

def get_git_credentials():
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        return token

    try:
        res = subprocess.run(
            ['git', 'credential', 'fill'],
            input=b'protocol=https\nhost=github.com\n',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        for line in res.stdout.decode().splitlines():
            if line.startswith('password='):
                return line.split('=', 1)[1]
    except Exception:
        pass
    return None

def sync_secrets(owner="shahakz11", repo="FootyArcade"):
    try:
        import nacl.encoding
        import nacl.public
    except ImportError:
        print("⚠️ pynacl is not installed. Run: pip install pynacl")
        return False

    token = get_git_credentials()
    if not token:
        print("⚠️ Could not retrieve GitHub credentials to sync secrets.")
        return False

    # 1. Fetch repo public key for GitHub Secrets
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key",
            headers={
                "User-Agent": "Mozilla/5.0",
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json"
            }
        )
        with urllib.request.urlopen(req) as resp:
            pk_info = json.loads(resp.read().decode())
    except Exception as e:
        print(f"⚠️ Failed to retrieve GitHub Actions secret public key: {e}")
        return False

    key_id = pk_info["key_id"]
    public_key = nacl.public.PublicKey(pk_info["key"].encode("utf-8"), nacl.encoding.Base64Encoder)
    sealed_box = nacl.public.SealedBox(public_key)

    def set_github_secret(secret_name, secret_value):
        encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
        encrypted_b64 = base64.b64encode(encrypted).decode("utf-8")
        
        payload = {
            "encrypted_value": encrypted_b64,
            "key_id": key_id
        }
        
        put_req = urllib.request.Request(
            f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{secret_name}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json"
            },
            method="PUT"
        )
        with urllib.request.urlopen(put_req) as resp:
            if resp.status in (201, 204):
                print(f"  ✅ Updated secret '{secret_name}' in GitHub Actions.")
                return True
            else:
                print(f"  ⚠️ Secret '{secret_name}' update returned status {resp.status}")
                return False

    print("🔄 Syncing local credentials to GitHub Actions secrets...")
    
    # Sync YOUTUBE_TOKEN_JSON
    json_path = os.path.join(PRIVATE_DIR, "youtube_token.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            set_github_secret("YOUTUBE_TOKEN_JSON", f.read())

    # Sync YOUTUBE_TOKEN_BASE64
    pickle_path = os.path.join(PRIVATE_DIR, "youtube_token.pickle")
    if os.path.exists(pickle_path):
        with open(pickle_path, "rb") as f:
            set_github_secret("YOUTUBE_TOKEN_BASE64", base64.b64encode(f.read()).decode("utf-8"))

    # Sync INSTAGRAM_CONFIG if present
    ig_path = os.path.join(PRIVATE_DIR, "instagram_config.json")
    if os.path.exists(ig_path):
        with open(ig_path, "r", encoding="utf-8") as f:
            set_github_secret("INSTAGRAM_CONFIG", f.read())

    print("✨ Sync completed successfully!")
    return True

if __name__ == "__main__":
    sync_secrets()
