# Playmaker — Game Ruleset & Development Workflow

> **This is the source of truth** for building new games and maintaining existing ones.
> Any UX/UI deviation from this document must be discussed and approved before shipping.

---

## 0. Resolved Design Decisions

These were discussed and locked in on 2026-07-10.

| Topic | Decision |
|---|---|
| Back-in-time depth | **7 days** (configurable per game via `maxBackDays`) |
| Hints | **Free** — no life penalty. Future monetization: watch-an-ad or subscription to unlock extra hints |
| Add Life button | **Keep as-is** — free for now. Future: watch-an-ad mechanic |
| Streak scope | **Per-game** only. No global cross-game streak |
| Share format | **Standardized emoji grid** (Wordle-style) across all games — clean and recognizable |
| SEO / publishing | All templates must include proper `<meta>` tags, OG tags, and Twitter card tags. The site is intended for public indexing on Google |
| footy-ui.js loading | Loaded as a static `<script src="../games/footy-ui.js">` tag — works on any static host (GitHub Pages, Firebase Hosting, Netlify, etc.) |
| Game note/disclaimer | Every game has a `note` field in `games.json` — e.g. "Data updated to July 2026" or "Doesn't include dual nationalities". Injected at compile time as `GAME_NOTE` and shown as an info bar |

---

## 1. Design Token Contract

Every game template **MUST** use the following Tailwind color tokens verbatim.
Only the `accent` and `primary-container` tokens may differ per game.

| Token | Value | Notes |
|---|---|---|
| `background` | `#0e0e0e` | ✋ Never change |
| `surface` | `#131313` | ✋ Never change |
| `surface-container-low` | `#1c1b1b` | ✋ Never change |
| `surface-container` | `#201f1f` | ✋ Never change |
| `surface-container-high` | `#2a2a2a` | ✋ Never change |
| `surface-container-highest` | `#353534` | ✋ Never change |
| `on-background` | `#e5e2e1` | ✋ Never change |
| `on-surface-variant` | `#a3a3a3` | ✋ Never change |
| `error` | `#ff4d4d` | ✋ Never change |
| `accent` | game-specific hex | ✅ Set per-game in `games.json` → `accentHex` |
| `primary-container` | same as accent | ✅ Set per-game |

The accent hex **must also** be set as a CSS custom property so shared components work:
```html
<style>
  :root { --fa-accent-rgb: R,G,B; --fa-accent-glow: rgba(R,G,B,0.25); }
</style>
```

### Typography (always the same)
| Role | Font |
|---|---|
| Headlines | Anton |
| Titles / UI labels | Space Grotesk |
| Body / data | Archivo Narrow |
| Monospace (badges, stats) | system monospace via Tailwind `font-mono` |

---

## 2. Required HTML Element IDs

Every game page **MUST** contain these element IDs. The `footy-ui.js` library and
`fetch_daily.py` compiler rely on them.

| ID | Element | Purpose |
|---|---|---|
| `puzzle-badge` | `<span>` | Displays "PUZZLE #N" or "PUZZLE #N — PAST" |
| `fa-lives-bar` | `<section>` | Contains lives counter + give-up button |
| `lives-counter` | `<span>` | Numeric lives display |
| `fa-heart-icon` | `<span>` | Material icon for heart animation |
| `give-up-btn` | `<button>` | Triggers give-up confirmation |
| `fa-guess-panel` | `<section>` | Wrapper hidden after game ends |
| `guess-input` | `<input>` | The guess text field |
| `autocomplete-list` | `<div>` | Dropdown container |
| `submit-btn` | `<button>` | Submits the guess |
| `error-message` | `<div>` | "Please select from dropdown" |
| `wrong-guesses-section` | `<section>` | Hidden until first wrong guess |
| `wrong-guesses-container` | `<div>` | Badge container for wrong guesses |
| `result-modal` | `<div>` | End-game modal overlay |
| `modal-icon` | `<span>` | Material icon (trophy / dangerous) |
| `modal-title` | `<h3>` | Win/loss headline |
| `modal-message` | `<p>` | Descriptive outcome message |
| `modal-score` | `<span>` | e.g. "7/10" |
| `modal-streak` | `<span>` | Current streak |
| `modal-best` | `<span>` | Best streak ever |
| `back-in-time-container` | `<div>` | Back-in-time links (in modal) |
| `bit-wrapper` | `<div>` | Parent of back-in-time section (hidden until game ends) |
| `modal-share-btn` | `<button>` | Triggers share |
| `modal-close-btn` | `<button>` | Closes modal (top-right X) |
| `modal-close-btn2` | `<button>` | Closes modal (bottom button) |
| `daily-game-data` | `<script>` | Injected by compiler — do not hard-code |

---

## 3. Required Game Constants (inline JS)

At the top of every game's `<script>` block:

```js
const GAME_ID       = 'your_game_id';   // must match games.json "id"
const ACCENT_HEX    = '#rrggbb';        // must match games.json "accentHex"
const INITIAL_LIVES = N;               // must match games.json "initialLives"
```

These injected constants **MUST** also be expected from the compiler:

```js
// Provided by fetch_daily.py at compile time:
const DAILY_XYZ_GAME  = { ... };   // main game data object
const PUZZLE_NUMBER   = N;
const IS_BACK_IN_TIME = false;
const MAX_BACK_DAYS   = 7;
```

---

## 4. FootyUI Component Usage

All games use these shared components from `footy-ui.js`. Import order matters:
```html
<link rel="stylesheet" href="../games/footy-ui.css"/>
<!-- ... game HTML ... -->
<script src="../games/footy-ui.js"></script>
<script>/* game-specific logic */</script>
```

### 4.1 FootyDropdown
```js
const dropdown = new FootyUI.FootyDropdown({
    inputId:    'guess-input',
    listId:     'autocomplete-list',
    data:       myDataArray,
    labelFn:    item => item.name,       // text shown in dropdown + fills input
    badgeFn:    item => item.badge,      // optional right-side badge (e.g. nationality)
    filterFn:   (item, q) => item.name.toLowerCase().includes(q),
    maxResults: 7,
});
// After user submits, call:
dropdown.clearSelection();   // resets selected item state
dropdown.reset();            // also clears the input value
```

### 4.2 FootyLives
```js
const livesCtrl = new FootyUI.FootyLives({
    counterId: 'lives-counter',
    heartId:   'fa-heart-icon',
    initial:   INITIAL_LIVES,
    onDead:    () => endGame(false),   // auto-called when lives hit 0
});
livesCtrl.lose();    // deduct 1 life
livesCtrl.add();     // add 1 life
livesCtrl.get();     // current value
livesCtrl.isDead();  // boolean
```

### 4.3 FootyWrongGuesses
```js
const wrongGuesses = new FootyUI.FootyWrongGuesses(
    'wrong-guesses-section',
    'wrong-guesses-container'
);
wrongGuesses.add('Arsenal');   // adds badge; deduplicates automatically
wrongGuesses.clear();
```

### 4.4 FootyModal
```js
const modal = new FootyUI.FootyModal({
    modalId:               'result-modal',
    iconId:                'modal-icon',
    titleId:               'modal-title',
    messageId:             'modal-message',
    scoreId:               'modal-score',
    streakId:              'modal-streak',
    extraInfoId:           'modal-player-name',   // optional
    backInTimeContainerId: 'back-in-time-container',
});
modal.show({
    won:       true/false,
    title:     'CAREER SOLVED!',
    message:   'Brilliant! ...',
    score:     7,
    maxScore:  10,
    streak:    3,
    extraText: 'Ronaldo',              // optional; shown in extraInfoId element
    backInTimeLinks: bitLinks,         // array from FootyUI.buildBackInTimeLinks()
});
modal.hide();
```

### 4.5 FootyStorage
```js
const storage = new FootyUI.FootyStorage(GAME_ID);
storage.hasPlayedToday();                            // → boolean
storage.hasPlayedPuzzle(puzzleNum);                  // → boolean
const stats = storage.recordResult(
    puzzleNum, won, score, maxScore, isBackInTime    // isBackInTime skips played/won/streak
);
stats.streak;        // current streak
stats.bestStreak;    // all-time best
```

### 4.6 FootyShare
```js
FootyUI.share({
    gameName:     'Top Transfers',
    puzzleNum,
    score, maxScore,
    lives:        livesCtrl.get(),
    initialLives: INITIAL_LIVES,
    won,
    url:          window.location.href
});
```
Produces emoji grid + score + URL → copies to clipboard with toast.

### 4.7 Back-in-time links
```js
const bitLinks = isBackInTime
    ? []
    : FootyUI.buildBackInTimeLinks(GAME_ID, maxBackDays, storage);
// Pass to modal.show() as backInTimeLinks
```

---

## 5. localStorage Schema

Each game writes to key `footy_v2_{gameId}`.

```jsonc
{
  "played":         15,          // total games completed (excludes back-in-time)
  "won":            12,
  "streak":         4,           // current winning streak
  "bestStreak":     7,
  "lastPlayedDate": "2026-07-09",
  "lastPuzzleNum":  42,
  "history": {
    "42":     { "won": true,  "score": 8, "maxScore": 10, "date": "2026-07-09" },
    "41":     { "won": false, "score": 3, "maxScore": 10, "date": "2026-07-08" },
    "bit_40": { "won": true,  "score": 7, "maxScore": 10, "date": "2026-07-08" }
  }
}
```

> **`bit_` prefix** marks back-in-time results — they are stored in history but do NOT
> affect `played`, `won`, or `streak` counts.

---

## 6. games.json Schema

```jsonc
{
  "id":           "my_new_game",                // unique, lowercase, underscores
  "name":         "My New Game",               // display name
  "description":  "One sentence description.", // shown on lobby card
  "link":         "games/my_new_game.html",    // compiled output path (today)
  "icon":         "sports_soccer",             // material-symbols icon name
  "accentHex":    "#ff6b35",                   // game accent color hex
  "initialLives": 5,                           // starting lives
  "maxBackDays":  7,                           // how many past files to compile
  "templateFile": "my_new_game_template.html", // in templates/
  "dataVariable": "DAILY_MY_NEW_GAME",         // JS const name injected by compiler
  "storageKey":   "footy_v2_my_new_game",      // localStorage key (auto-derived, FYI)
  "note":         "Data updated to July 2026.", // shown as info bar in the game
  "status":       "active"                     // "active" or "coming_soon"
}
```

---

## 7. Checklist — Adding a New Game

Follow these steps **in order** to add a new game to Playmaker.

### Step 1 — Plan
- [ ] Define the game mechanic in one sentence
- [ ] Decide: what does the user guess? (player, club, year, fee?)
- [ ] Decide: accent color (pick one not already used)
- [ ] Decide: initial lives count
- [ ] Decide: what CSV data file drives this game?

### Step 2 — Data Pipeline
- [ ] Add a new CSV generation function in `build_transfer_datasets.py`
- [ ] Run it to generate `daily_{game_id}_games.csv`
- [ ] Verify the CSV has a `game_day` column (1..180)

### Step 3 — Register in `games.json`
- [ ] Add a full entry following the schema in §6 above

### Step 4 — Create Template
- [ ] Copy `templates/transfer_destination_template.html` as a starting point
- [ ] Update game title, description, accent hex, initial lives constant
- [ ] Update CSS `:root { --fa-accent-rgb: ... }` to match accent hex
- [ ] Keep **all required element IDs** from §2
- [ ] Load `../games/footy-ui.css` and `../games/footy-ui.js`
- [ ] Initialize all FootyUI components following §4
- [ ] Implement `submitGuess()`, `endGame(won)`, `doShare()` following existing patterns

### Step 5 — Register Loader in `fetch_daily.py`
- [ ] Add a `load_{game_id}(puzzle_num)` function returning `(game_data, extra)`
- [ ] Add it to the `GAME_LOADERS` dict
- [ ] Add data variable name to `GAME_DATA_VAR` dict
- [ ] Add strip patterns to `STRIP_PATTERNS` dict

### Step 6 — Compile & Test
- [ ] Run: `python fetch_daily.py --game {game_id} --max-back-days 1`
- [ ] Verify: `games/{game_id}.html` and `games/{game_id}_d1.html` exist
- [ ] Open in browser: play through a complete game (win path)
- [ ] Open in browser: play through a complete game (loss path)
- [ ] Check: modal shows score, streak, best streak, back-in-time links
- [ ] Check: localStorage `footy_v2_{game_id}` is written correctly
- [ ] Check: share button copies correct text and emoji grid
- [ ] Open `index.html`: new game card appears with correct accent color
- [ ] Check: "Played today" badge shows after completing the game

### Step 7 — Polish
- [ ] Test on mobile (iOS Safari, Android Chrome) — verify no input zoom issues
- [ ] Verify `font-size: 16px` (or `text-base`) on the `<input>` to prevent iOS zoom
- [ ] Verify keyboard navigation in dropdown (↑ ↓ Enter Tab Escape)
- [ ] Verify give-up flow reveals all answers correctly
- [ ] Verify back-in-time files work independently (different puzzle #, different localStorage key suffix)

---

## 8. Mechanics Reference

### Guess Input
- User types in `#guess-input`
- Dropdown shows up to 7 matches from the data set
- Arrow keys navigate; Enter/Tab selects; Escape closes
- Only items selected from the dropdown are valid (prevents typos)
- Submitting an unrecognized value shows `#error-message`

### Lives
- Display: heart icon + `Lives: N` counter
- On wrong guess: `livesCtrl.lose()` → decrements → heart pulse animation
- At 0 lives: `onDead` callback fires → `endGame(false)`
- **Add Life button is kept** — free for now. Button ID: `add-life-btn`. Wire: `livesCtrl.add()`. *Future: watch-an-ad to earn a life*
- **No hint life-cost** (hints are free; hint button disappears after use)

### Hints (game-specific, optional)
- Individual item hints blur/unblur via `.hint-blur` / `.hint-revealed` CSS classes
- `revealHint(index)` is a game-specific function; not in footy-ui.js
- **Hints are free** — no life penalty. Button disappears after use per row
- *Future monetization: extra hint bundles, watch-an-ad, or premium subscription*

### Give Up
- Confirm dialog: "Are you sure?"
- On confirm: `endGame(false)` — reveals all answers, modal opens

### End Game Modal
- Win: `emoji_events` icon, accent color title, positive message
- Loss: `dangerous` icon, error color icon, neutral message
- Always shows: score `N/M`, current streak, best streak
- Back-in-time links (today's game only; not shown for back-in-time games)
- Share button: emoji grid + score + URL

### Share Format
```
⚽ Playmaker — Game Name #42
🟩🟩🟩⬛⬛
🟩🟩🟩🟩🟩
✅ 8/10 correct · ❤️ 3 lives used
🔗 https://...
```

### Back-in-Time
- Files: `games/{game_id}_d1.html` (yesterday), `_d2.html`, etc.
- Each file has `IS_BACK_IN_TIME = true` and `MAX_BACK_DAYS = N` injected
- Back-in-time games show "PUZZLE #N — PAST" in the header badge
- Results stored with `bit_` prefix in history; do NOT affect streak/played/won
- Back-in-time links shown in modal after completing today's game

---

## 9. File Structure

```
Football/
├── index.html                         ← lobby page
├── games.json                         ← game registry (source of truth)
├── fetch_daily.py                     ← build compiler
├── build_transfer_datasets.py         ← CSV data generator
├── GAME_RULESET.md                    ← this file
├── games/
│   ├── footy-ui.js                    ← shared component library ⭐
│   ├── footy-ui.css                   ← shared styles ⭐
│   ├── top_transfers.html             ← today's compiled game
│   ├── top_transfers_d1.html          ← yesterday's compiled game
│   ├── top_transfers_d2.html          ← 2 days ago
│   ├── transfer_destination.html
│   ├── transfer_destination_d1.html
│   └── ...
├── templates/
│   ├── top_transfers_template.html
│   ├── transfer_destination_template.html
│   └── {new_game}_template.html
├── all_players.json                   ← autocomplete data for player games
├── all_clubs.json                     ← autocomplete data for club games
├── daily_transfer_games.csv
├── daily_nationality_transfer_games.csv
└── daily_destination_games.csv
```

---

## 10. Planned Future Games

These games are stubs in `games.json` with `"status": "coming_soon"`. They appear on the
lobby as greyed-out teaser cards. They are skipped by `fetch_daily.py`.

### Top Scorers

- **Mechanic**: Guess the top scorers for a club, league, or national team (all-time or specific season)
- **Guess type**: Player name (same dropdown mechanic as Top Transfers)
- **Modes**: 
  - `club` — e.g., "Top scorers for Real Madrid all time"
  - `league` — e.g., "Top scorers in the Premier League 2022/23 season"
  - `country` — e.g., "All-time top scorers for Brazil"
- **Data needed**: Goals/stats CSV with `game_day`, `player_name`, `goals`, `club_or_league`, `season`
- **Accent color**: `#f59e0b` (amber)
- **Reveal order**: By rank (1st hardest, 10th easiest) — similar to Top Transfers table
- **Notes**: Decide whether to show goals count as a hint or reveal it upfront

### This & That

- **Mechanic**: Name all players that match **both** given statements simultaneously
  - Example A: "Played for Barcelona AND played for Argentina national team"
  - Example B: "Scored 50+ goals in the Premier League AND 50+ goals in La Liga"
  - Example C: "Won a Ballon d'Or AND played in the MLS"
- **Guess type**: Player name — same dropdown, no ranking, just a set of correct answers
- **Key difference from other games**: There is no single ordered list — the answer pool is a **set** of correct players
- **Win condition**: Find all N correct players (or give up)
- **Scoring**: Number found / total correct
- **Reveal**: At game end, show the full list of matching players
- **Data needed**: Relational query across clubs, goals, nationality, awards CSVs
- **Accent color**: `#a855f7` (purple)
- **UX consideration**: Must show total count (e.g. "There are 7 players") at game start
- **Component changes needed**: `FootyWrongGuesses` and `FootyModal` are already compatible. No new shared components needed.

---

## 11. SEO Checklist (for each new game template)

| Tag | Required value |
|---|---|
| `<title>` | `{Game Name} \| Playmaker` |
| `<meta name="description">` | 120–160 char summary of the game |
| `<meta property="og:title">` | Same as `<title>` |
| `<meta property="og:description">` | Same as description |
| `<meta property="og:type">` | `website` |
| `<meta name="twitter:card">` | `summary` |
| `<meta name="twitter:title">` | Same as `<title>` |
| `<meta name="twitter:description">` | Same as description |
| `<h1>` in header | Game name (visible in page header) |
| `<h2>` main heading | Descriptive (e.g. "Club Record Signings") |
| Structured hierarchy | h1 → h2 → h3 → h4 only |
| `aria-label` on back button | Yes: `"Back to game lobby"` |

> **Hosting note**: When the site is deployed (GitHub Pages, Firebase Hosting, Netlify, etc.),
> add a `sitemap.xml` listing all live game URLs and a `robots.txt` allowing all crawlers.
> The `footy-ui.js` / `.css` relative path (`../games/`) works on any static host.

---

## 12. Common Pitfalls

| Pitfall | Fix |
|---|---|
| iOS auto-zoom on input focus | Set `font-size: 16px` (or `text-base`) on `<input>` |
| Duplicate JS const error | `fetch_daily.py` strips old injections via regex before injecting new ones |
| Back-in-time affecting streak | Use `isBackInTime = true` → `storage.recordResult(..., true)` |
| Accent color not applying to dropdown | Ensure `:root { --fa-accent-rgb: R,G,B }` is set in `<style>` |
| Game card not showing on lobby | Add entry to `games.json` with correct `link` path |
| `footy-ui.js` loaded before DOM | Library uses `(function(global){...})(window)` — safe to load anywhere |
| Wrong guess allowed if not in list | Always validate against the data array before accepting |
