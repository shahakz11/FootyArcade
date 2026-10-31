#!/usr/bin/env python3
"""
scripts/deploy_gas.py — Automated Google Apps Script Clasp Deployment
=====================================================================
Automates pushing and redeploying `google-apps-script.js` to Google Apps Script
via clasp, updating the production Web App deployment:
  Deployment ID: AKfycbxEG3jA0QduSlh3ZmMR-98lTK1i4AbO-FgmFpymlJTof_8DZpZdmODSto0Q4NTyX7_7OA
  Script ID:     1spPqr-OJaBXN_Mf8wUsep5u-acjvt_eUTIe-bptdNZvGsN9e29Xd0cq7
  Spreadsheet:   1ZNJ57i7kVUYrdW4q4S3lRe4NqYUM7-lL4RQtSzX0_8Q ("Footy Feedback")

Usage:
  python3 scripts/deploy_gas.py
  python3 scripts/deploy_gas.py --description "Updated VAR logic"
  python3 scripts/deploy_gas.py --dry-run
"""

import sys
import os
import shutil
import subprocess
import argparse
import urllib.request
import json
from datetime import datetime, timezone

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAS_DIR = os.path.join(ROOT_DIR, "gas")
SRC_JS = os.path.join(ROOT_DIR, "google-apps-script.js")
DEST_JS = os.path.join(GAS_DIR, "Code.js")

DEPLOYMENT_ID = "AKfycbxEG3jA0QduSlh3ZmMR-98lTK1i4AbO-FgmFpymlJTof_8DZpZdmODSto0Q4NTyX7_7OA"
WEB_APP_URL = f"https://script.google.com/macros/s/{DEPLOYMENT_ID}/exec"


def main():
    parser = argparse.ArgumentParser(description="Deploy Playmaker Apps Script via clasp")
    parser.add_argument("-d", "--description", default="", help="Deployment description")
    parser.add_argument("--dry-run", action="store_true", help="Validate without pushing or deploying")
    args = parser.parse_args()

    print("🚀 [GAS Clasp Deployer] Preparing deployment...")

    if not os.path.exists(SRC_JS):
        print(f"❌ Error: Source file not found: {SRC_JS}")
        sys.exit(1)

    os.makedirs(GAS_DIR, exist_ok=True)

    # Sync google-apps-script.js to gas/Code.js
    print(f"📋 Syncing {os.path.basename(SRC_JS)} -> gas/Code.js...")
    shutil.copy2(SRC_JS, DEST_JS)

    clasp_json = os.path.join(GAS_DIR, ".clasp.json")
    if not os.path.exists(clasp_json):
        print("❌ Error: gas/.clasp.json missing!")
        sys.exit(1)

    appsscript_json = os.path.join(GAS_DIR, "appsscript.json")
    if not os.path.exists(appsscript_json):
        print("❌ Error: gas/appsscript.json missing!")
        sys.exit(1)

    if args.dry_run:
        print("✅ [Dry Run] gas/Code.js synchronized, clasp configs verified. Skipping remote push/deploy.")
        sys.exit(0)

    # 1. Clasp Push
    print("📤 Running clasp push...")
    push_cmd = ["npx", "@google/clasp", "push", "-f"]
    push_res = subprocess.run(push_cmd, cwd=GAS_DIR, capture_output=True, text=True)
    if push_res.returncode != 0:
        print(f"❌ clasp push failed:\n{push_res.stderr or push_res.stdout}")
        sys.exit(push_res.returncode)
    print(push_res.stdout.strip())

    # 2. Clasp Deploy to fixed deployment ID
    desc = args.description.strip() or f"Automated deployment: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    print(f"📦 Redeploying deployment {DEPLOYMENT_ID} with description: '{desc}'...")
    deploy_cmd = ["npx", "@google/clasp", "deploy", "-i", DEPLOYMENT_ID, "-d", desc]
    deploy_res = subprocess.run(deploy_cmd, cwd=GAS_DIR, capture_output=True, text=True)
    if deploy_res.returncode != 0:
        print(f"❌ clasp deploy failed:\n{deploy_res.stderr or deploy_res.stdout}")
        sys.exit(deploy_res.returncode)
    print(deploy_res.stdout.strip())

    # 3. Health check
    print(f"🔍 Verifying live Web App health at {WEB_APP_URL}...")
    try:
        req = urllib.request.Request(WEB_APP_URL, headers={"User-Agent": "PlaymakerDeployVerifier/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="ignore")
            if status == 200 and ("FootyArcade" in body or "functionNames" in body):
                print(f"✅ Live Web App health check verified (HTTP {status})!")
            else:
                print(f"⚠️ Web App responded with HTTP {status}, body preview: {body[:100]}")
    except Exception as e:
        print(f"⚠️ Health check ping error (non-fatal): {e}")

    print("🎉 Google Apps Script deployed successfully via clasp!\n")


if __name__ == "__main__":
    main()
