#!/usr/bin/env python3
"""
Google Search Console Auditor for Playmaker / FootyArcade.
Connects using the service account credentials and extracts:
- Sites / Properties list
- Sitemap status and errors
- Search Analytics (Clicks, Impressions, CTR, Position)
- Index inspection
"""

import os
import sys
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

POSSIBLE_KEY_PATHS = [
    os.path.expanduser("~/.config/gcloud/footyarcade-gsc-sa.json"),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "private", "footyarcade-gsc-sa.json"),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "private", "service_account.json"),
]

def find_credentials():
    for p in POSSIBLE_KEY_PATHS:
        if os.path.exists(p):
            try:
                with open(p) as f:
                    d = json.load(f)
                    email = d.get("client_email", "")
                    if "footyarcade" in email or "serviceaccount" in email:
                        return p, d
            except Exception:
                continue
    return None, None

def run_gsc_audit():
    key_path, key_data = find_credentials()
    if not key_path:
        print("ERROR: No service account key file found for FootyArcade.")
        print("Please save your service account JSON key to:")
        print(f"  {POSSIBLE_KEY_PATHS[0]}")
        print("or")
        print(f"  {POSSIBLE_KEY_PATHS[1]}")
        sys.exit(1)

    print(f"Using service account key: {key_path}")
    print(f"Service account email: {key_data.get('client_email')}")
    print(f"Project ID: {key_data.get('project_id')}\n")

    scopes = ["https://www.googleapis.com/auth/webmasters.readonly"]
    creds = service_account.Credentials.from_service_account_file(key_path, scopes=scopes)
    service = build("searchconsole", "v1", credentials=creds)

    print("Fetching GSC site properties...")
    try:
        sites_res = service.sites().list().execute()
        site_entries = sites_res.get("siteEntry", [])
        if not site_entries:
            print("WARNING: The service account has no sites in Google Search Console.")
            print(f"Make sure you added '{key_data.get('client_email')}' in Search Console Settings -> Users and permissions.")
            return

        print(f"Found {len(site_entries)} site(s) in GSC:")
        for s in site_entries:
            print(f" - {s.get('siteUrl')} (Permission: {s.get('permissionLevel')})")

        # Audit each site
        for s in site_entries:
            site_url = s.get("siteUrl")
            print(f"\n=======================================================")
            print(f"Auditing Property: {site_url}")
            print(f"=======================================================")

            # 1. Sitemaps
            print("\n--- Sitemaps Status ---")
            try:
                sitemaps_res = service.sitemaps().list(siteUrl=site_url).execute()
                sitemaps = sitemaps_res.get("sitemap", [])
                if not sitemaps:
                    print("  No sitemaps submitted in GSC for this property.")
                for sm in sitemaps:
                    print(f"  Path: {sm.get('path')}")
                    print(f"  Last Downloaded: {sm.get('lastDownloaded')}")
                    print(f"  Status: {sm.get('isPending') and 'Pending' or 'Processed'}")
                    print(f"  Errors: {sm.get('errors', 0)}, Warnings: {sm.get('warnings', 0)}")
                    for contents in sm.get("contents", []):
                        print(f"    Type: {contents.get('type')}, Submitted: {contents.get('submitted')}, Indexed: {contents.get('indexed')}")
            except Exception as e:
                print(f"  Error fetching sitemaps: {e}")

            # 2. Search Analytics (Last 28 Days)
            print("\n--- Search Performance (Last 28 Days) ---")
            try:
                request = {
                    "startDate": "2026-09-28",
                    "endDate": "2026-10-25",
                    "dimensions": ["date"],
                    "rowLimit": 30
                }
                res = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
                rows = res.get("rows", [])
                total_clicks = sum(r.get("clicks", 0) for r in rows)
                total_impressions = sum(r.get("impressions", 0) for r in rows)
                avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
                print(f"  Total Clicks: {total_clicks}")
                print(f"  Total Impressions: {total_impressions}")
                print(f"  Avg CTR: {avg_ctr:.2f}%")

                # Top Queries
                q_req = {
                    "startDate": "2026-09-28",
                    "endDate": "2026-10-25",
                    "dimensions": ["query"],
                    "rowLimit": 10
                }
                q_res = service.searchanalytics().query(siteUrl=site_url, body=q_req).execute()
                print("\n  Top 10 Queries:")
                for r in q_res.get("rows", []):
                    print(f"   - {r['keys'][0]}: {r.get('clicks', 0)} clicks, {r.get('impressions', 0)} imp, pos {r.get('position', 0):.1f}")

                # Top Pages
                p_req = {
                    "startDate": "2026-09-28",
                    "endDate": "2026-10-25",
                    "dimensions": ["page"],
                    "rowLimit": 10
                }
                p_res = service.searchanalytics().query(siteUrl=site_url, body=p_req).execute()
                print("\n  Top 10 Pages:")
                for r in p_res.get("rows", []):
                    print(f"   - {r['keys'][0]}: {r.get('clicks', 0)} clicks, {r.get('impressions', 0)} imp")

            except Exception as e:
                print(f"  Error querying search analytics: {e}")

    except Exception as e:
        print(f"GSC API Error: {e}")

if __name__ == "__main__":
    run_gsc_audit()
