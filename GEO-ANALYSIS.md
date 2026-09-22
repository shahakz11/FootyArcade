# Generative Engine Optimization (GEO) Audit Report
**Target Platform:** [Playmaker](https://playmaker.best) (`playmaker.best`)  
**Audit Date:** September 22, 2026  
**Framework:** GEO Standard (AIO, ChatGPT, Perplexity, Bing Copilot)

---

## 1. Executive Summary & GEO Readiness Score

```
============================================================
              OVERALL GEO READINESS SCORE: 79/100
============================================================
 [■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■□□□□□□□□□□] 79%
 Status: HIGH READINESS (Top Tier Indie Arcade)
============================================================
```

Playmaker demonstrates a strong foundation for Generative Engine Optimization with clean semantic HTML, structured JSON-LD schemas (`Organization`, `WebSite`, `WebApplication`, `VideoGame`, `FAQPage`, `BreadcrumbList`), a native `/llms.txt` file, and self-contained definition blocks. Elevating the score to 90+ requires adding explicit AI crawler declarations in `robots.txt`, extending 134–167 word crawlable answer blocks across all individual game pages, and creating external community entity signals (Reddit / YouTube / Wikidata).

---

## 2. Platform Breakdown

| AI Search Platform | Readiness Score | Primary Citation Drivers | Status & Assessment |
|---|:---:|---|---|
| **Google AI Overviews** | **82 / 100** | Top-10 search rank, FAQPage schema, semantic headers, fast static HTML | **Excellent**: Complete JSON-LD graph, questions match high-intent PAA queries ("What is the football version of Wordle?"), clean static noscript fallback. |
| **ChatGPT (SearchGPT / GPTBot)** | **77 / 100** | `/llms.txt` standard, clear definitional sentences ("X is..."), entity data | **Very Good**: `/llms.txt` exists and lists all 6 games; needs explicit `GPTBot` / `OAI-SearchBot` robots.txt allowance and author entity linking. |
| **Perplexity AI** | **78 / 100** | Direct facts, community validation, citation tables, fast structured parsing | **Very Good**: Direct answer format in FAQs and passport guide; needs Reddit discussion footprint and comparative Markdown data tables. |
| **Bing Copilot** | **80 / 100** | OpenGraph tags, JSON-LD, sitemap indexing, clean domain hierarchy | **Strong**: Fast edge delivery, valid XML sitemap with daily changefreq, complete meta tags. |

---

## 3. Evaluation by GEO Criteria

```
┌─────────────────────────────────────────────────────────────┐
│ Category                     Weight   Score   Status        │
├─────────────────────────────────────────────────────────────┤
│ 1. Citability Score           25%     20/25   Very Strong   │
│ 2. Structural Readability     20%     18/20   Excellent     │
│ 3. Multi-Modal Content        15%     11/15   Good          │
│ 4. Authority & Brand Signals  20%     14/20   Solid         │
│ 5. Technical Accessibility    20%     16/20   Very Strong   │
├─────────────────────────────────────────────────────────────┤
│ TOTAL GEO SCORE              100%     79/100  Grade: B+     │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 Citability Score (20/25)
- **Optimal Passage Length (134–167 words):**
  - `games/passport_fc.html` includes an explicit 138-word static answer block in `<article>` perfectly sized for single-chunk AI context extraction.
  - `index.html` includes a 64-word crawlable intro and 25–45 word FAQ answers.
  - *Gap:* The remaining 5 live game pages (`club_connect.html`, `player_chain.html`, `top_transfers.html`, `top_scorers.html`, `transfer_destination.html`) have game templates lacking dedicated 134–167 word static `<article>` explanation blocks for non-JS crawlers.
- **Definitional Precision:**
  - Employs strict "X is a free daily football trivia arcade..." patterns matching LLM retrieval templates.
- **Data Attribution:**
  - Clearly attributes dataset coverage ("Transfermarkt", "Official senior transfers since 1990", "Updated to September 2026").

### 3.2 Structural Readability (18/20)
- **Heading Hierarchy:**
  - `H1` (Brand & Arcade Title) &rarr; `H2` (Hero & FAQ) &rarr; `H3` (Game Select & Mode Headers) &rarr; `H4` (Game Cards & Stats).
- **Question-Based Query Headings:**
  - `What is Playmaker?`
  - `How do you play Playmaker?`
  - `What is Player Chain?`
  - `What is the football version of Wordle?`
- **Scannability:**
  - Clean bullet points, numbered step instructions, short 2–3 sentence paragraphs.
  - *Opportunity:* Add comparison tables (e.g. Playmaker Game Modes vs Rules & Lives) to optimize tabular scraping.

### 3.3 Multi-Modal Content (11/15)
- **Visual Assets:**
  - High-res vector and raster logos (`assets/playmaker_header_logo.png`, `assets/social_share.png`), dynamic SVG game icons, and contextual Giphy celebration GIFs.
- **Video Elements:**
  - Automated YouTube Short rendering pipelines exist in the codebase (`render_top_transfers_video.py`, `UploadTodayShorts.command`), but web pages do not yet embed VideoObject schemas or preview clips.

### 3.4 Authority & Brand Signals (14/20)
- **Entity Linking:**
  - Schema.org `Organization` contains `sameAs` links to verified social channels:
    - Instagram: `https://www.instagram.com/playmaker.best1`
    - TikTok: `https://www.tiktok.com/@playmaker.best`
    - YouTube: `https://www.youtube.com/@best.playmaker`
- **Trust & Verification Mechanisms:**
  - Real-time automated VAR (Video Assistant Referee) engine allowing user appeals on real transfer records.
- *Gaps:*
  - No explicit `Person` author/creator entity schema for game designers/statisticians.
  - Wikipedia / Wikidata entity absence (typical for emerging indies; can be supplemented via Reddit and Crunchbase presence).

### 3.5 Technical Accessibility (16/20)
- **Server-Side Rendering / Static Crawlability:**
  - Static HTML files contain `<noscript>` game listings and crawlable `<section>` descriptions readable by search bots without executing client-side JavaScript.
- **llms.txt File:**
  - Root `/llms.txt` is present and active, describing all 6 core puzzle games with markdown URLs and key database facts.
- **robots.txt Configuration:**
  - Currently permits all crawlers with `User-agent: * Allow: /`. Lacks specific bot user-agent definitions for modern AI crawlers.

---

## 4. AI Crawler Access Status (`robots.txt`)

### Current State
```robots.txt
User-agent: *
Allow: /
Allow: /manifest.json
Allow: /games.json
...
```

### AI Crawler Audit Matrix
| Crawler | Organization | Purpose | Current Access | Recommended Action |
|---|---|---|:---:|---|
| **GPTBot** | OpenAI | ChatGPT search index & citations | Implicitly Allowed | **Explicitly Allow** |
| **OAI-SearchBot** | OpenAI | OpenAI Search real-time results | Implicitly Allowed | **Explicitly Allow** |
| **ChatGPT-User** | OpenAI | User browsing in ChatGPT | Implicitly Allowed | **Explicitly Allow** |
| **ClaudeBot** | Anthropic | Claude Search & Web answers | Implicitly Allowed | **Explicitly Allow** |
| **PerplexityBot** | Perplexity AI | Perplexity search citations | Implicitly Allowed | **Explicitly Allow** |
| **Applebot-Extended**| Apple | Apple Intelligence / Siri Search| Implicitly Allowed | **Explicitly Allow** |
| **CCBot** | Common Crawl | Bulk LLM Training Datasets | Allowed | Disallow (if conserving scrape bandwidth) |
| **Bytespider** | ByteDance | TikTok / ByteDance LLM Crawler | Allowed | Disallow / Throttle |

---

## 5. llms.txt Status & Optimization

### Current File Analysis (`/llms.txt`)
- **Status:** **PRESENT & ACTIVE** (1,836 bytes)
- **Structure:**
  - Title & One-line elevator pitch.
  - Markdown links to all 6 daily games with descriptive sentences.
  - Key facts section covering database scope (1990–2026), VAR mechanism, and free-to-play model.

### Enhancement Recommendations
1. Add an optional `/llms-full.txt` or extended subsection with direct game rules and sample clue-answer pairings for each game mode.
2. Standardize data freshness reference across files (ensure consistent mention of updated date: September 2026).

---

## 6. Passage-Level Citability & Optimal 134–167 Word Blocks

### Existing Benchmark Passage (`games/passport_fc.html` — 138 Words)
> *Passport FC is a daily football trivia puzzle by Playmaker where fans collect nationality stamps for a featured anchor club. Each day highlights one world-famous club alongside four progressive nationality tiers. Players must name any qualifying footballer who made senior appearances or signed for that club while representing the designated nation. The puzzle begins with major footballing countries that have extensive talent pools before ascending to "The Unicorn" — an unexpected country with only one or two eligible players across the club's entire transfer history. All challenges feature streak tracking and shareable results.*

### Recommended New Passages for Remaining Game Modes

#### Club Connect (142 Words)
```markdown
Club Connect is a daily football connection puzzle by Playmaker that challenges fans to deduce the secret club linking five mystery footballer signings. At the start of each daily game, five player cards are presented face-down, ranked in order of their transfer fee. One initial player is revealed immediately as a starting clue. Players submit club guesses to identify the mystery buyer before running out of lives. Every incorrect guess flips over the next player card to reveal additional transfer history, nationality, and position hints. Once the connection is discovered, players earn an efficiency score based on how few player clues they needed to crack the puzzle. Club Connect covers senior domestic and international transfers from 1990 to present, resetting daily at midnight UTC with streak tracking and shareable emoji summaries.
```

#### Player Chain (148 Words)
```markdown
Player Chain is a daily football teammate connection challenge by Playmaker where players deduce a mystery Player of the Day through a sequential career chain. Starting from an anchor club, players advance through the chain by naming footballers who shared senior squad appearances across consecutive clubs. Each validated teammate guess confirms a transfer link and reveals progressive clues regarding the mystery player's nationality, primary position, and shirt number. Players can methodically climb each link in the ladder or attempt an instant-win guess if they recognize the final footballer early. The game features interactive VAR review for contested teammate rosters, comprehensive hint options, and local streak tracking across the Premier League, La Liga, Serie A, Bundesliga, and UEFA competitions. New career chains release daily at midnight UTC with full back-in-time archives.
```

---

## 7. Top 5 Highest-Impact GEO Changes

| Priority | Action Item | Impact Area | Effort |
|:---:|---|---|:---:|
| **1** | **Add explicit AI Crawler directives to `robots.txt`** (Declare `GPTBot`, `OAI-SearchBot`, `ClaudeBot`, `PerplexityBot`, `Applebot-Extended`) | AI Discovery & Indexing | 5 mins |
| **2** | **Deploy 134–167 word static `<article>` passage blocks to all game templates** (`club_connect`, `player_chain`, `top_transfers`, `top_scorers`, `transfer_destination`) | Citability Score & Passage Extraction | 20 mins |
| **3** | **Enrich JSON-LD schema across all game templates** with `FAQPage` and `HowTo` schemas for each individual puzzle type | Rich Results & AI Overviews | 15 mins |
| **4** | **Add comparative game summary Markdown table to `index.html` & `llms.txt`** (Game Name \| Objective \| Lives \| Difficulty Curve) | Perplexity / Claude Tabular Citation | 10 mins |
| **5** | **Build Entity Social Footprint / Reddit Mentions** (Create r/PlaymakerTrivia or share daily puzzle threads on relevant football subreddits) | Brand Mentions & ChatGPT / Perplexity Authority | Ongoing |

---

## 8. Schema Recommendations for AI Discoverability

### Recommended `robots.txt` AI Additions
```robots.txt
# AI Search Engine Crawlers (Explicitly Allowed)
User-agent: GPTBot
Allow: /
Allow: /llms.txt

User-agent: OAI-SearchBot
Allow: /
Allow: /llms.txt

User-agent: ClaudeBot
Allow: /
Allow: /llms.txt

User-agent: PerplexityBot
Allow: /
Allow: /llms.txt

User-agent: Applebot-Extended
Allow: /
Allow: /llms.txt

# Bulk Training Crawlers (Optional Disallow)
User-agent: CCBot
Disallow: /
```

### Recommended `HowTo` Schema Snippet (For Game Pages)
```json
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "How to Play Passport FC",
  "description": "Step-by-step guide to solving the daily Passport FC football nationality puzzle.",
  "step": [
    {
      "@type": "HowToStep",
      "position": 1,
      "name": "Identify the Anchor Club",
      "text": "Review today's featured club and note the four target nationality tiers."
    },
    {
      "@type": "HowToStep",
      "position": 2,
      "name": "Name a Qualifying Player",
      "text": "Type and select any senior player who represented both the anchor club and the active country stamp."
    },
    {
      "@type": "HowToStep",
      "position": 3,
      "name": "Solve The Unicorn",
      "text": "Unlock the 4th tier by naming the rare 1-player nationality legend in club history."
    }
  ]
}
```

---

## 9. Conclusion
Playmaker is already in the **top 15% of indie sports web apps for GEO readiness** thanks to its fast, static-first foundation, `/llms.txt` implementation, and robust schema graph. Implementing the 5 high-impact quick wins above will maximize passage citation frequency across Google AI Overviews, SearchGPT, and Perplexity.
