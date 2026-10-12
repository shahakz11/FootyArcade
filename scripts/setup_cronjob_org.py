#!/usr/bin/env python3
"""
scripts/setup_cronjob_org.py

Automated configuration tool for cron-job.org.
Sets up all Playmaker daily automated cloud cron jobs:
1. 10:00 AM Local (07:00 UTC): Career Flight Map Short & Reel
2. 01:30 PM Local (10:30 UTC): Midday H2H Comparison Carousel
3. 08:00 PM Local (17:00 UTC): Evening UGC Short / Reel
4. 03:00 AM Local (00:00 UTC): Daily Firebase Deployment
5. Hourly at :30: Social Media Auto-Reply Bot
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.sync_secrets_to_github import get_git_credentials

GITHUB_OWNER = "shahakz11"
GITHUB_REPO = "FootyArcade"

JOB_SPECS = [
    {
        "title": "⚽ Playmaker 1: Morning Career Flight Short & Reel",
        "description": "Publishes 3D Career Flight Short (n-2 transfer destination) to YouTube Shorts & Instagram Reels",
        "workflow": "daily_shorts_reels.yml",
        "body": {"ref": "main", "inputs": {"mode": "career_flight"}},
        "cron_display": "Every day at 10:00 AM Local (07:00 UTC)",
        "utc_hour": 7,
        "utc_minute": 0,
        "schedule": {
            "timezone": "UTC",
            "hours": [7],
            "minutes": [0],
            "mdays": [-1],
            "months": [-1],
            "wdays": [-1]
        }
    },
    {
        "title": "⚽ Playmaker 2: Evening UGC Short & Reel",
        "description": "Publishes daily Player Chain / Passport FC video short to YouTube & Instagram",
        "workflow": "daily_shorts_reels.yml",
        "body": {"ref": "main", "inputs": {"mode": "short"}},
        "cron_display": "Every day at 8:00 PM Local (17:00 UTC)",
        "utc_hour": 17,
        "utc_minute": 0,
        "schedule": {
            "timezone": "UTC",
            "hours": [17],
            "minutes": [0],
            "mdays": [-1],
            "months": [-1],
            "wdays": [-1]
        }
    },
    {
        "title": "⚽ Playmaker 3: Midnight Firebase Deploy",
        "description": "Compiles daily puzzles and deploys Playmaker web app to Firebase Hosting",
        "workflow": "deploy.yml",
        "body": {"ref": "main"},
        "cron_display": "Every day at 3:00 AM Local (00:00 UTC)",
        "utc_hour": 0,
        "utc_minute": 0,
        "schedule": {
            "timezone": "UTC",
            "hours": [0],
            "minutes": [0],
            "mdays": [-1],
            "months": [-1],
            "wdays": [-1]
        }
    },
    {
        "title": "⚽ Playmaker 4: Social Media Auto-Reply Bot",
        "description": "Replies to comments and trivia guesses across YouTube and Instagram",
        "workflow": "auto_reply_comments.yml",
        "body": {"ref": "main"},
        "cron_display": "Every 2 hours at minute :30",
        "utc_hour": -1,
        "utc_minute": 30,
        "schedule": {
            "timezone": "UTC",
            "hours": [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23],
            "minutes": [30],
            "mdays": [-1],
            "months": [-1],
            "wdays": [-1]
        }
    }
]

def print_manual_setup(github_token):
    print("\n" + "=" * 78)
    print("      📋 CRON-JOB.ORG MANUAL SETUP GUIDE FOR PLAYMAKER JOBS")
    print("=" * 78)
    print("Create these jobs at https://console.cron-job.org/jobs/create\n")

    for i, spec in enumerate(JOB_SPECS, 1):
        dispatch_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/{spec['workflow']}/dispatches"
        body_json = json.dumps(spec["body"])

        print(f"[{i}] {spec['title']}")
        print(f"    • Description:  {spec['description']}")
        print(f"    • Schedule:     {spec['cron_display']}")
        print(f"    • URL:          {dispatch_url}")
        print(f"    • Method:       POST")
        print(f"    • Request Body: {body_json}")
        print(f"    • Headers:")
        print(f"        Authorization: Bearer {github_token[:8]}... (GitHub PAT)")
        print(f"        Accept:        application/vnd.github+json")
        print(f"        Content-Type:  application/json")
        print(f"        User-Agent:    Playmaker-Cron")
        print("-" * 78)

def deploy_via_cronjob_api(api_key, github_token):
    import time

    print("\n" + "=" * 78)
    print("      🚀 MANAGING JOBS IN CRON-JOB.ORG VIA REST API")
    print("=" * 78)

    # 1. Fetch existing jobs to avoid duplicates and delete obsolete ones
    existing_jobs = {}
    try:
        req = urllib.request.Request(
            "https://api.cron-job.org/jobs",
            headers={"Authorization": f"Bearer {api_key}", "User-Agent": "Playmaker-Setup"}
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            for j in data.get("jobs", []):
                title = j.get("title", "")
                jid = j.get("jobId")
                existing_jobs[title] = jid
                # Check for obsolete H2H carousel jobs
                if "H2H" in title or "Carousel" in title or "Midday" in title:
                    print(f"  🗑️ Removing obsolete job: '{title}' (ID: {jid})...")
                    del_req = urllib.request.Request(
                        f"https://api.cron-job.org/jobs/{jid}",
                        headers={"Authorization": f"Bearer {api_key}", "User-Agent": "Playmaker-Setup"},
                        method="DELETE"
                    )
                    try:
                        urllib.request.urlopen(del_req)
                        print(f"     ✅ Deleted '{title}'.")
                    except Exception as e:
                        print(f"     ⚠️ Could not delete: {e}")
                    time.sleep(2.0)
    except Exception as e:
        print(f"  ⚠️ Could not fetch existing jobs: {e}")

    # 2. Create missing jobs with rate-limit protection
    for spec in JOB_SPECS:
        title = spec["title"]

        # Check if already exists (matching start of title)
        already_id = None
        for etitle, ejid in existing_jobs.items():
            if ("Morning" in title and "Morning" in etitle) or ("Evening" in title and "Evening" in etitle) or ("Firebase" in title and "Firebase" in etitle) or ("Auto-Reply" in title and "Auto-Reply" in etitle):
                already_id = ejid
                break

        if already_id:
            print(f"  ℹ️ '{title}' already exists (Job ID: {already_id}). Skipping creation.")
            continue

        dispatch_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/{spec['workflow']}/dispatches"
        body_json = json.dumps(spec["body"])

        job_payload = {
            "job": {
                "title": title,
                "url": dispatch_url,
                "enabled": True,
                "saveResponses": True,
                "schedule": spec["schedule"],
                "requestMethod": 1,  # 1 = POST
                "extendedData": {
                    "headers": {
                        "Authorization": f"Bearer {github_token}",
                        "Accept": "application/vnd.github+json",
                        "Content-Type": "application/json",
                        "User-Agent": "Playmaker-Cron"
                    },
                    "body": body_json
                }
            }
        }

        # Attempt creation with retries for rate limit (HTTP 429)
        max_attempts = 4
        for attempt in range(max_attempts):
            req = urllib.request.Request(
                "https://api.cron-job.org/jobs",
                data=json.dumps(job_payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Playmaker-Setup"
                },
                method="PUT"
            )
            try:
                with urllib.request.urlopen(req) as resp:
                    data = json.loads(resp.read().decode())
                    job_id = data.get("jobId", "OK")
                    print(f"  ✅ Created '{title}' (Job ID: {job_id})")
                    time.sleep(2.5)  # Rate limit safety pause
                    break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait_time = (attempt + 1) * 3.5
                    print(f"  ⏳ Rate limit hit for '{title}'. Pausing for {wait_time:.1f}s before retry...")
                    time.sleep(wait_time)
                else:
                    err_msg = e.read().decode()
                    print(f"  ❌ Error creating '{title}': HTTP {e.code} - {err_msg}")
                    break
            except Exception as e:
                print(f"  ❌ Error creating '{title}': {e}")
                break

    print("\n✨ All active Playmaker jobs are synchronized in cron-job.org!")

def main():
    parser = argparse.ArgumentParser(description="Setup cron-job.org schedules for Playmaker")
    parser.add_argument("--api-key", type=str, default="", help="cron-job.org API Key (from console.cron-job.org/settings/api)")
    parser.add_argument("--github-token", type=str, default="", help="GitHub Personal Access Token (defaults to local credential)")
    args = parser.parse_args()

    gh_token = args.github_token or get_git_credentials()
    if not gh_token:
        print("❌ Could not find a GitHub Personal Access Token. Please provide --github-token <TOKEN>.")
        sys.exit(1)

    cron_api_key = args.api_key or os.getenv("CRONJOB_API_KEY", "")

    if cron_api_key:
        deploy_via_cronjob_api(cron_api_key, gh_token)
    else:
        print_manual_setup(gh_token)
        print("\n💡 Tip: To automatically deploy all 5 jobs in 1 second via API, run:")
        print(f"    python3 scripts/setup_cronjob_org.py --api-key <YOUR_CRONJOB_API_KEY>\n")

if __name__ == "__main__":
    main()
