#!/usr/bin/env python3
"""
Purge old Firebase Hosting versions to free storage quota.
Usage:
    python scripts/cleanup_hosting.py --keep 2
"""
import sys
import os
import json
import subprocess
import urllib.request
import urllib.error

PROJECT_ID = "footyarcade"
SITE_ID = "footyarcade"

def get_access_token():
    # 1. Try gcloud
    for gcloud_path in ["gcloud", "/opt/homebrew/bin/gcloud", "/usr/local/bin/gcloud", os.path.expanduser("~/Downloads/google-cloud-sdk/bin/gcloud")]:
        try:
            out = subprocess.check_output([gcloud_path, "auth", "print-access-token"], stderr=subprocess.DEVNULL).decode().strip()
            if out:
                return out
        except Exception:
            continue

    # 2. Try firebase login token
    try:
        cfg = os.path.expanduser("~/.config/configstore/firebase-tools.json")
        if os.path.exists(cfg):
            with open(cfg) as f:
                d = json.load(f)
                token = d.get("tokens", {}).get("access_token")
                if token:
                    return token
    except Exception:
        pass

    return None

def main():
    keep_count = 2
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        keep_count = int(sys.argv[1])

    token = get_access_token()
    if not token:
        print("❌ Could not obtain Google/Firebase access token.")
        print("Run one of these commands first to authenticate:")
        print("  gcloud auth login")
        print("  OR: gcloud auth application-default login")
        print("  OR: npx firebase login")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print(f"🔍 Fetching versions for site '{SITE_ID}'...")
    url = f"https://firebasehosting.googleapis.com/v1beta1/sites/{SITE_ID}/versions?pageSize=100"
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"❌ API Error ({e.code}): {e.read().decode()}")
        sys.exit(1)

    versions = data.get("versions", [])
    print(f"📦 Found {len(versions)} versions total.")

    if len(versions) <= keep_count:
        print(f"✅ Nothing to delete (versions <= {keep_count}).")
        return

    to_delete = versions[keep_count:]
    print(f"🗑️ Deleting {len(to_delete)} older versions (keeping latest {keep_count})...")

    deleted = 0
    for v in to_delete:
        v_name = v.get("name") # e.g. sites/footyarcade/versions/xyz
        del_url = f"https://firebasehosting.googleapis.com/v1beta1/{v_name}"
        del_req = urllib.request.Request(del_url, headers=headers, method="DELETE")
        try:
            with urllib.request.urlopen(del_req) as del_resp:
                deleted += 1
                print(f"  ✓ Deleted version {v_name.split('/')[-1]}")
        except urllib.error.HTTPError as err:
            print(f"  ✗ Failed to delete {v_name.split('/')[-1]}: {err.code}")

    print(f"\n🎉 Cleaned up {deleted} versions successfully!")

if __name__ == "__main__":
    main()
