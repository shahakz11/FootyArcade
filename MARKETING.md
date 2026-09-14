# 📢 Playmaker — Brand Identity & Marketing Kit

This document provides the official marketing asset specifications, download locations, and deployment guidelines for **Playmaker** (`https://playmaker.best`).

---

## 🎨 Brand Design Tokens

| Token | Hex | Role | Usage |
|---|---|---|---|
| **Pitch Neon** | `#39FF14` | Primary Accent / Call to Action | Buttons, glows, score accents, highlights |
| **Pitch Black** | `#0E0E0E` | Canvas Background | Root page body, letterbox margins |
| **Deep Charcoal** | `#131313` | Surface Containers | Cards, panels, modal backdrops |
| **Text Crisp** | `#E5E2E1` | Primary Text | Headlines, active labels |
| **Muted Slate** | `#A3A3A3` | Supporting Text | Subtitles, helper text, timestamps |

### Typography
- **Headlines**: `Anton` (Uppercase, Italic styling for high-intensity sports action)
- **Titles & UI Labels**: `Space Grotesk` (Modern, technical HUD feel)
- **Body & Data**: `Archivo Narrow` (High density, readable tabular data)

---

## 🖼️ Asset Catalog & Specifications

### 1. Social Sharing & WhatsApp Preview Banner
- **File**: `assets/social_share.png`
- **Dimensions**: `1200 x 630 px` (Standard 1.91:1 OpenGraph ratio)
- **File Size**: `~147 KB` (< 300 KB limit enforced for instant WhatsApp card rendering)
- **Usage**: Used in `og:image` and `twitter:image` across all game templates and `index.html`.

### 2. High-Resolution Banner Ad (16:9)
- **File**: `assets/marketing/banner_ad_16_9.png`
- **Dimensions**: `1376 x 768 px`
- **Usage**: Display advertising, web promo banners, landscape campaign headers.

### 3. Square Social Card (1:1)
- **Files**: `assets/marketing/social_card_1_1.png`, `assets/social_share_square.png`
- **Dimensions**: `1024 x 1024 px`
- **Usage**: Instagram posts, X/Twitter feed cards, Discord rich embeds, avatars.

### 4. Email Header Banner (16:9)
- **File**: `assets/marketing/email_header_banner.png`
- **Dimensions**: `1376 x 768 px`
- **Usage**: Newsletter banners, transactional email headers, marketing emails.

### 5. Brand Logos & Icons
- **Refined Logo**: `assets/logo.png`, `assets/playmaker_logo.png` (`1024 x 1024 px`)
- **Favicon (Master)**: `assets/favicon.png` (`512 x 512 px`)
- **PWA Icons**: `assets/favicon-192.png` (`192 x 192 px`), `assets/favicon-32.png` (`32 x 32 px`)
- **Favicon Multi-Resolution**: `favicon.ico` (`16x16`, `32x32`, `48x48`)
- **Apple Touch Icon**: `assets/apple-touch-icon.png` (`180 x 180 px`)

---

## 🛠️ Automated Asset Sync Script

To re-sync or regenerate optimized assets from the Stitch Google Cloud CDN at any time:
```bash
python3 scripts/sync_stitch_marketing_assets.py
```

To recompile all daily game HTML files with updated metadata:
```bash
python3 fetch_daily.py
```

---

## 🌐 Marketing Showcase Page

Visit `marketing.html` or open in your browser:
```bash
open marketing.html
```
The page provides a complete visual showcase of the brand identity, feature game modes, and direct one-click downloads for all marketing assets.
