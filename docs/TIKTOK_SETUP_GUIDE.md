# 🎵 TikTok Developer Platform Setup Guide for Playmaker (`@playmaker.best`)

This comprehensive setup guide walks through configuring the **TikTok Content Posting API (v2)** to enable automated publishing and draft generation for **Playmaker** (`@playmaker.best`).

---

## 📋 Table of Contents
1. [Architecture & Protocol Overview](#1-architecture--protocol-overview)
2. [Prerequisites & Brand Assets](#2-prerequisites--brand-assets)
3. [TikTok Developer Portal Walkthrough](#3-tiktok-developer-portal-walkthrough)
4. [Sandbox vs. Production Audit](#4-sandbox-vs-production-audit)
5. [OAuth 2.0 Authorization & Token Generation](#5-oauth-20-authorization--token-generation)
6. [Automated Verification & Pipeline Testing](#6-automated-verification--pipeline-testing)
7. [Secrets Management & GitHub Actions Sync](#7-secrets-management--github-actions-sync)
8. [Troubleshooting & Common Pitfalls](#8-troubleshooting--common-pitfalls)

---

## 1. Architecture & Protocol Overview

TikTok uses the **Content Posting API v2** hosted on `https://open.tiktokapis.com/v2`. Automation integrates with TikTok through a standard OAuth 2.0 Authorization Code Grant.

```
┌─────────────────┐       1. Auth URL in Browser       ┌──────────────────────┐
│ Developer / User│ ─────────────────────────────────> │   TikTok Auth Server │
│ (@playmaker.best)│ <───────────────────────────────── │ (Login & Scope Grant)│
└────────┬────────┘      2. Redirect w/ Auth Code      └──────────────────────┘
         │
         │ 3. Run exchange script with Code
         ▼
┌──────────────────────────────┐    4. POST /v2/oauth/token/   ┌──────────────────────┐
│ exchange_tiktok_token.py     │ ────────────────────────────> │  TikTok API Endpoint │
│ (Stores private config)      │ <──────────────────────────── │ (Tokens + Open ID)   │
└────────┬─────────────────────┘    5. Access & Refresh Token  └──────────────────────┘
         │
         ▼
┌──────────────────────────────┐    6. Video Init & Upload     ┌──────────────────────┐
│ tiktok_uploader.py           │ ────────────────────────────> │ TikTok Video Servers │
│ (Daily Shorts Automation)    │                               │ (Feed or Inbox Draft)│
└──────────────────────────────┘                               └──────────────────────┘
```

### Core API Endpoints

| Purpose | HTTP Method & URL | Description |
|---|---|---|
| **OAuth Authorization** | `GET https://www.tiktok.com/v2/auth/authorize/` | User logs in and approves scopes |
| **Token Exchange** | `POST https://open.tiktokapis.com/v2/oauth/token/` | Exchanges auth code for tokens (`grant_type=authorization_code`) |
| **Token Refresh** | `POST https://open.tiktokapis.com/v2/oauth/token/` | Refreshes expired access token (`grant_type=refresh_token`) |
| **Creator Info** | `POST https://open.tiktokapis.com/v2/post/publish/creator_info/query/` | Checks creator verification, privacy limits, sound permissions |
| **Direct Post Init** | `POST https://open.tiktokapis.com/v2/post/publish/video/init/` | Initiates direct public publishing to the creator's feed |
| **Creator Inbox Init** | `POST https://open.tiktokapis.com/v2/post/publish/inbox/video/init/` | Sends video to creator inbox as a draft with a push notification |
| **Publish Status** | `POST https://open.tiktokapis.com/v2/post/publish/status/fetch/` | Polls upload and processing status (`PUBLISH_COMPLETE`) |
| **User Profile Info** | `GET https://open.tiktokapis.com/v2/user/info/` | Retrieves account username, avatar, and unique `open_id` |

### Token Lifetimes & Rotation

- **Access Token**: Valid for **24 hours** (`86,400` seconds). Used in the `Authorization: Bearer <TOKEN>` header.
- **Refresh Token**: Valid for **365 days** (`31,536,000` seconds).
- **Auto-Refresh Mechanism**: `scripts/tiktok_uploader.py` and `scripts/exchange_tiktok_token.py` inspect token expiration timestamps. Whenever an access token is within 1 hour of expiration, the script automatically issues a `refresh_token` request to obtain a fresh access token without human intervention.

---

## 2. Prerequisites & Brand Assets

Before creating the app on TikTok, have the following assets and links ready:

| Requirement | Value / Location | Notes |
|---|---|---|
| **TikTok Account** | `@playmaker.best` | Mobile app logged in on your phone |
| **Official Website** | `https://playmaker.best` | Live production website |
| **Privacy Policy** | `https://playmaker.best/privacy.html` | Deployed and publicly accessible |
| **Terms of Service** | `https://playmaker.best/terms.html` | Deployed and publicly accessible |
| **App Icon** | `assets/logo.png` or `assets/playmaker_logo.png` | `1024x1024` PNG or JPG |
| **Redirect URI (Local)** | `http://localhost:8080/callback` | For local token exchange server |
| **Redirect URI (Web)** | `https://playmaker.best/` | Optional fallback redirect |

---

## 3. TikTok Developer Portal Walkthrough

Follow these steps on the TikTok Developer Portal to create and configure the app.

### Step 3.1: Create Developer Account
1. Navigate to [developers.tiktok.com](https://developers.tiktok.com/).
2. Click **Log In** or **Register**.
3. Log in using your developer credentials or sign in directly with the `@playmaker.best` TikTok account.
4. Complete any required phone/email verification steps.

### Step 3.2: Create a New App
1. Go to the **Manage Apps** dashboard ([developers.tiktok.com/app](https://developers.tiktok.com/app)).
2. Click **Create an App**.
3. Fill in the basic application information:
   - **App Name**: `Playmaker`
   - **App Icon**: Upload `assets/logo.png` (or `assets/playmaker_logo.png`, `1024x1024` px).
   - **App Category**: `Sports` or `Gaming` / `Entertainment`.
   - **App Description**:
     > *Playmaker is an autonomous daily football puzzles, trivia, and transfer statistics platform that publishes daily educational football challenges and highlights to TikTok.*
   - **Terms of Service URL**: `https://playmaker.best/terms.html`
   - **Privacy Policy URL**: `https://playmaker.best/privacy.html`
   - **Website URL**: `https://playmaker.best`
4. Click **Create**.

### Step 3.3: Add Required Products & Kits
In your app's dashboard navigation menu under **Products** / **Add Products**:

1. **Add "TikTok Login Kit"** (or Login):
   - Enables OAuth 2.0 authentication and identity resolution.
   - Required for obtaining authorization codes and user identification.
2. **Add "Content Posting API"** (previously *Share to TikTok* / *Video Kit*):
   - Enables server-to-server video uploading and publishing.
   - Provides both **Direct Post** (`video.publish`) and **Creator Inbox** (`video.upload`) functionality.

### Step 3.4: Configure OAuth & Redirect Domains
Under your app's **Login Kit** settings:

1. **Redirect URI / Callback URL**:
   Add the following redirect URIs:
   - `http://localhost:8080/callback` *(Primary - used by local exchange script)*
   - `https://playmaker.best/` *(Secondary / Web production callback)*
2. Save your changes.

### Step 3.5: Request Scopes & Permissions
In the **Permissions** tab for Login Kit and Content Posting API, toggle or request the following scopes:

- [x] `user.info.basic`: Read basic user profile info (avatar, nickname, open_id).
- [x] `video.publish`: Direct publishing of videos to user profile (public feed).
- [x] `video.upload`: Upload video drafts directly to the creator's inbox on mobile.

> [!NOTE]
> In **Development Mode (Sandbox)**, all three scopes can be tested immediately with registered test accounts without waiting for TikTok's commercial audit review!

### Step 3.6: Retrieve Client Key & Client Secret
Under **App Details** or **Basic Info**:
1. Locate **Client Key** (equivalent to `client_id`).
2. Locate **Client Secret** (click show/copy).
3. Keep these secure! You will enter them into `private/tiktok_config.json`.

---

## 4. Sandbox vs. Production Audit

TikTok provides two operating tiers: **Development / Sandbox Mode** and **Production (Audited) Mode**.

### 🧪 Development / Sandbox Mode (Start Here)

You **do not need to wait for TikTok audit approval** to begin testing and publishing videos for `@playmaker.best`.

1. Go to **App Dashboard** -> **App Settings** or **Test Accounts** / **Sandbox Users**.
2. Click **Add Test Account** or **Add Developer Account**.
3. Enter the TikTok username: `playmaker.best`.
4. A notification or QR code request will appear on the TikTok mobile app for `@playmaker.best`. Accept the invitation.
5. Once accepted, `@playmaker.best` is authorized to use the app in Development mode.

#### Mode Differences: Direct Post vs. Creator Inbox (Draft)

| Feature | Direct Post (`video.publish`) | Creator Inbox / Draft (`video.upload`) |
|---|---|---|
| **What happens** | Video posts immediately to public profile | Video is uploaded to creator's mobile inbox as a draft |
| **Creator action** | None (100% automated) | User receives a push notification, taps into TikTok app, reviews, and taps **Post** |
| **Sound / Music** | Commercial library or uploaded audio track | Native trending TikTok sounds can be picked in-app |
| **Audit Status** | Stricter audit requirements | Lower barrier; standard development mode default |

> [!TIP]
> The automation pipeline supports **both** modes:
> - If `video.publish` is approved: runs 100% headless automated posting.
> - If in Development mode or pending audit: uploads to **Creator Inbox**, sending a notification to your phone so you can tap **Post** in 1 second!

### 🏢 Production App Audit (When Ready for Full Public Direct Post)

When you are ready to remove test account limits and enable fully automated headless `video.publish` for any account:

1. **Submission Video / Screencast**:
   - Record a 60–90 second screen recording of the workflow:
     1. Showing the Playmaker website (`https://playmaker.best`).
     2. Showing the OAuth authorization consent screen with `playmaker.best`.
     3. Showing the terminal executing the upload command.
     4. Showing the resulting video published on the TikTok app.
2. **Demo URL / Test Instructions**:
   - Provide clear instructions explaining that Playmaker compiles daily educational football statistics and puzzles.
3. **Data Usage Justification**:
   - `user.info.basic`: To confirm the identity of `@playmaker.best`.
   - `video.publish` & `video.upload`: To publish daily football shorts generated by the Playmaker engine.
4. **Legal Compliance**:
   - Ensure `https://playmaker.best/privacy.html` and `https://playmaker.best/terms.html` load properly (already live and compliant).

---

## 5. OAuth 2.0 Authorization & Token Generation

### Step 5.1: Create Local Configuration File

Create the file `private/tiktok_config.json` with your developer credentials:

```json
{
  "client_key": "YOUR_TIKTOK_CLIENT_KEY",
  "client_secret": "YOUR_TIKTOK_CLIENT_SECRET",
  "redirect_uri": "http://localhost:8080/callback",
  "access_token": "",
  "refresh_token": "",
  "open_id": "",
  "expires_at": 0,
  "refresh_expires_at": 0,
  "account_username": "playmaker.best"
}
```

### Step 5.2: Run the Token Exchange Helper

Run the exchange script:

```bash
python3 scripts/exchange_tiktok_token.py
```

The script will:
1. Construct the authorization URL with the correct scopes (`user.info.basic,video.publish,video.upload`).
2. Start a temporary local listener on `http://localhost:8080/callback`.
3. Print the URL for you to open in your browser:
   ```text
   https://www.tiktok.com/v2/auth/authorize/?client_key=YOUR_KEY&scope=user.info.basic,video.publish,video.upload&response_type=code&redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fcallback&state=playmaker_oauth
   ```
4. In your browser:
   - Ensure you are logged in as `@playmaker.best`.
   - Click **Authorize**.
5. The browser will redirect to `http://localhost:8080/callback?code=...`.
6. The script will automatically intercept the `code`, make a POST request to `https://open.tiktokapis.com/v2/oauth/token/`, and save the `access_token`, `refresh_token`, and `open_id` to `private/tiktok_config.json`.

*(Manual fallback: If running on a headless server without browser auto-redirect, the script also accepts pasting the redirected URL or authorization code directly into the terminal prompt).*

---

## 6. Automated Verification & Pipeline Testing

Once `private/tiktok_config.json` is populated, verify connectivity and test the upload pipeline.

### Step 6.1: Verify Connection & Scopes

Run the verification health check:

```bash
python3 scripts/tiktok_uploader.py --verify
```

Expected output:
```text
============================================================
⚽ Playmaker TikTok Connection Verification
============================================================
🔍 Checking credentials in private/tiktok_config.json...
✅ Client credentials loaded.
🔄 Validating Access Token...
  ✅ Token active (expires in 23 hours).
📡 Querying TikTok Creator Info for @playmaker.best...
  ✅ Connected User Open ID: 7392819201928301
  ✅ Account Username: @playmaker.best
  ✅ Scopes Authorized: user.info.basic, video.upload, video.publish
  ✅ Privacy Settings: Public posting allowed
  ✅ Duet & Stitch: Allowed
🎉 Verification successful! TikTok uploader is ready to post.
============================================================
```

### Step 6.2: Test Dry-Run in the Shorts Automation Pipeline

Test the end-to-end shorts generator with TikTok in `--dry-run` mode to verify metadata, video paths, and upload flags without posting:

```bash
python3 scripts/upload_daily_shorts.py --game player_chain --dry-run
```

### Step 6.3: Perform a Real Test Upload

To upload today's short directly to TikTok (or as an inbox draft):

```bash
# Upload specific game with force flag
python3 scripts/upload_daily_shorts.py --game player_chain --force
```

Or invoke the TikTok uploader script directly on any rendered MP4:

```bash
python3 scripts/tiktok_uploader.py \
  --video output/shorts/2026-10-13_player_chain.mp4 \
  --title "Can you link these players? ⚽ Link in bio to play! #football #trivia #quiz" \
  --privacy PUBLIC_TO_EVERYONE
```

For draft / inbox mode:
```bash
python3 scripts/tiktok_uploader.py \
  --video output/shorts/2026-10-13_player_chain.mp4 \
  --mode inbox
```

---

## 7. Secrets Management & GitHub Actions Sync

To enable headless cloud execution via GitHub Actions or remote cron jobs without checking API secrets into git:

1. **Verify `.gitignore`**:
   Ensure `private/tiktok_config.json` is ignored by Git (already covered by `private/*` in `.gitignore`).

2. **Sync Secrets to GitHub**:
   Run the repository secret synchronizer:
   ```bash
   python3 scripts/sync_secrets_to_github.py
   ```
   This automatically reads `private/tiktok_config.json` and updates the `TIKTOK_CONFIG_JSON` secret in your GitHub repository via the `gh` CLI.

---

## 8. Troubleshooting & Common Pitfalls

| Issue | Cause | Solution |
|---|---|---|
| **`redirect_uri_mismatch` (Error 10007)** | The URL passed in the request doesn't match the developer portal | Ensure `http://localhost:8080/callback` matches character-for-character with trailing slashes in the TikTok Login Kit settings. |
| **`scope_not_authorized`** | Requested scope isn't added to the app | Go to your App Dashboard -> **Permissions**, enable `user.info.basic`, `video.publish`, and `video.upload`. |
| **`unaudited_client_can_only_post_to_sandbox_users`** | App is in Development mode and target account wasn't invited | Add `@playmaker.best` under **App Settings** -> **Test Accounts** and accept the invite in the TikTok app. |
| **`access_token_expired`** | Token reached its 24-hour limit | The uploader script refreshes this automatically using `refresh_token`. If refresh token expired (after 1 year), rerun `python3 scripts/exchange_tiktok_token.py`. |
| **Video rejected or failed processing** | Incompatible video encoding or dimensions | TikTok requires **MP4 / H.264** with AAC audio, recommended **1080x1920 (9:16)** vertical ratio, minimum 3 seconds, maximum 10 minutes. The Playmaker render pipeline outputs compliant formats automatically. |
| **`reach_max_post_limit`** | TikTok daily posting limit reached | TikTok limits new or unverified developer accounts to 5–10 posts per day. The Playmaker daily schedule publishes 1–2 high-quality clips per day, well within bounds. |

---

## 🏁 Summary Checklist

- [ ] Registered developer account on [developers.tiktok.com](https://developers.tiktok.com/).
- [ ] Created app named **Playmaker** with `assets/logo.png`.
- [ ] Added **TikTok Login Kit** and **Content Posting API**.
- [ ] Configured redirect URI: `http://localhost:8080/callback`.
- [ ] Added `@playmaker.best` to **Test Accounts** (Sandbox).
- [ ] Created `private/tiktok_config.json` with `client_key` and `client_secret`.
- [ ] Executed `python3 scripts/exchange_tiktok_token.py` and authorized account.
- [ ] Ran `python3 scripts/tiktok_uploader.py --verify` and verified green status.
- [ ] Tested upload pipeline with `python3 scripts/upload_daily_shorts.py --dry-run`.
