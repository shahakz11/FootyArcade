/**
 * footy-ui.js — Playmaker Shared Component Library
 *
 * Loaded by every game BEFORE the game-specific script.
 * Exposes a global `FootyUI` object with factory methods for all
 * shared game components: autocomplete dropdown, lives, hints,
 * end-game modal, share, localStorage storage, and back-in-time.
 *
 * Design decisions:
 *  - No external dependencies (vanilla JS only)
 *  - All components are opt-in; games call only what they need
 *  - Accent color injected via CSS custom property --fa-accent-rgb
 *    (set by each game template's inline <style>)
 */

(function (global) {
    'use strict';

    // ── Global Configuration ──────────────────────────────────
    const FEEDBACK_WEBHOOK_URL = 'https://script.google.com/macros/s/AKfycbxEG3jA0QduSlh3ZmMR-98lTK1i4AbO-FgmFpymlJTof_8DZpZdmODSto0Q4NTyX7_7OA/exec';

    // ── Canonical Domain & Route Enforcement ─────────────────
    if (typeof window !== 'undefined' && window.location) {
        const host = window.location.hostname;
        const path = window.location.pathname;

        // Redirect Firebase default subdomains to official domain
        if (host === 'footyarcade.web.app' || host === 'footyarcade.firebaseapp.com') {
            window.location.replace('https://playmaker.best' + path + window.location.search + window.location.hash);
            return;
        }

        // Redirect any direct template file access to homepage
        if (path.startsWith('/templates/') || path.includes('_template.html')) {
            window.location.replace('https://playmaker.best/');
            return;
        }
    }

    /**
     * Accent-insensitive normalization helper
     * e.g. "Ángel Di María" -> "angel di maria"
     */
    /**
     * Accent-insensitive & punctuation-normalized helper
     * e.g. "Ángel Di María" -> "angel di maria"
     * e.g. "Al-Nassr" -> "al nassr"
     */
    function normalizeStr(str) {
        if (!str) return '';
        return String(str)
            .replace(/[\u200b-\u200f\u202a-\u202e\ufeff]/g, '')
            .replace(/[ðÐ]/g, 'd')
            .replace(/[þÞ]/g, 'th')
            .replace(/[øØ]/g, 'o')
            .replace(/[łŁ]/g, 'l')
            .replace(/[đĐ]/g, 'd')
            .replace(/[æÆ]/g, 'ae')
            .replace(/[œŒ]/g, 'oe')
            .replace(/ß/g, 'ss')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .replace(/[-._']/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
    }

    /**
     * Common club aliases and equivalence mapping
     */
    const CLUB_ALIASES = {
        // England
        'man city': 'manchester city', 'manchester city': 'manchester city',
        'man utd': 'manchester united', 'man united': 'manchester united', 'manchester united': 'manchester united',
        'spurs': 'tottenham hotspur', 'tottenham': 'tottenham hotspur', 'tottenham hotspur': 'tottenham hotspur',
        'newcastle': 'newcastle united', 'newcastle united': 'newcastle united',
        'west ham': 'west ham united', 'west ham united': 'west ham united',
        'wolves': 'wolverhampton wanderers', 'wolverhampton': 'wolverhampton wanderers', 'wolverhampton wanderers': 'wolverhampton wanderers',
        'leicester': 'leicester city', 'leicester city': 'leicester city',
        'leeds': 'leeds united', 'leeds united': 'leeds united',
        'brighton': 'brighton and hove albion', 'brighton hove albion': 'brighton and hove albion', 'brighton and hove albion': 'brighton and hove albion',
        'aston villa': 'aston villa',

        // Spain
        'barca': 'barcelona', 'fc barcelona': 'barcelona', 'barcelona': 'barcelona',
        'real madrid': 'real madrid',
        'atletico': 'atletico madrid', 'atletico madrid': 'atletico madrid',
        'athletic bilbao': 'athletic bilbao', 'athletic club': 'athletic bilbao',
        'sevilla': 'sevilla', 'sevilla fc': 'sevilla',
        'real betis': 'real betis', 'betis': 'real betis',
        'real sociedad': 'real sociedad',
        'villarreal': 'villarreal', 'villarreal cf': 'villarreal',
        'valencia': 'valencia', 'valencia cf': 'valencia',
        'celta vigo': 'celta vigo', 'celta de vigo': 'celta vigo',
        'espanyol': 'espanyol', 'rcd espanyol': 'espanyol',
        'mallorca': 'mallorca', 'rcd mallorca': 'mallorca',

        // Germany
        'bayern munich': 'bayern munich', 'bayern munchen': 'bayern munich', 'fc bayern': 'bayern munich', 'fc bayern munchen': 'bayern munich',
        'dortmund': 'borussia dortmund', 'b dortmund': 'borussia dortmund', 'bor dortmund': 'borussia dortmund', 'borussia dortmund': 'borussia dortmund',
        'leverkusen': 'bayer leverkusen', 'b leverkusen': 'bayer leverkusen', 'bayer leverkusen': 'bayer leverkusen', 'bayer 04 leverkusen': 'bayer leverkusen',
        'leipzig': 'rb leipzig', 'rb leipzig': 'rb leipzig', 'rasenballsport leipzig': 'rb leipzig',
        'm gladbach': 'borussia monchengladbach', 'borussia m gladbach': 'borussia monchengladbach', 'borussia monchengladbach': 'borussia monchengladbach',
        'schalke': 'schalke 04', 'schalke 04': 'schalke 04', 'fc schalke 04': 'schalke 04',
        'hoffenheim': 'tsg hoffenheim', 'tsg hoffenheim': 'tsg hoffenheim', 'tsg 1899 hoffenheim': 'tsg hoffenheim',
        'mainz': 'mainz 05', 'mainz 05': 'mainz 05', '1 fsv mainz 05': 'mainz 05', 'fsv mainz 05': 'mainz 05',
        'frankfurt': 'eintracht frankfurt', 'eintracht frankfurt': 'eintracht frankfurt',
        'stuttgart': 'vfb stuttgart', 'vfb stuttgart': 'vfb stuttgart',
        'wolfsburg': 'vfl wolfsburg', 'vfl wolfsburg': 'vfl wolfsburg',
        'nuremberg': '1 fc nurnberg', 'nurnberg': '1 fc nurnberg', '1 fc nuremberg': '1 fc nurnberg',
        'koln': '1 fc koln', 'cologne': '1 fc koln', 'fc koln': '1 fc koln', '1 fc koln': '1 fc koln',

        // Italy
        'inter': 'inter milan', 'inter milan': 'inter milan', 'internazionale': 'inter milan', 'fc internazionale': 'inter milan',
        'ac milan': 'ac milan', 'milan': 'ac milan',
        'juventus': 'juventus', 'juve': 'juventus',
        'roma': 'as roma', 'as roma': 'as roma',
        'napoli': 'ssc napoli', 'ssc napoli': 'ssc napoli',
        'lazio': 'ss lazio', 'ss lazio': 'ss lazio',
        'atalanta': 'atalanta', 'atalanta bc': 'atalanta',
        'fiorentina': 'acf fiorentina', 'acf fiorentina': 'fiorentina',

        // France
        'psg': 'paris saint germain', 'paris sg': 'paris saint germain', 'paris saint germain': 'paris saint germain',
        'om': 'marseille', 'olympique marseille': 'marseille', 'olympique de marseille': 'marseille', 'marseille': 'marseille',
        'ol': 'lyon', 'olympique lyon': 'lyon', 'olympique lyonnais': 'lyon', 'lyon': 'lyon',
        'monaco': 'as monaco', 'as monaco': 'as monaco',
        'lille': 'lille osc', 'lille osc': 'lille osc', 'losc lille': 'lille osc',
        'rennes': 'stade rennais', 'stade rennais': 'stade rennais',

        // Others
        'sporting': 'sporting cp', 'sporting lisbon': 'sporting cp', 'sporting cp': 'sporting cp',
        'benfica': 'sl benfica', 'sl benfica': 'sl benfica',
        'porto': 'fc porto', 'fc porto': 'fc porto',
        'ajax': 'afc ajax', 'afc ajax': 'afc ajax',
        'psv': 'psv eindhoven', 'psv eindhoven': 'psv eindhoven',
        'feyenoord': 'feyenoord rotterdam', 'feyenoord rotterdam': 'feyenoord rotterdam',
        'salzburg': 'red bull salzburg', 'rb salzburg': 'red bull salzburg', 'red bull salzburg': 'red bull salzburg',
        'club brugge': 'club brugge', 'brugge': 'club brugge', 'bruges': 'club brugge',
        'lyngby': 'lyngby', 'lyngby bk': 'lyngby', 'lyngby boldklub': 'lyngby',
        'copenhagen': 'fc copenhagen', 'fc copenhagen': 'fc copenhagen',
    };

    function canonicalClub(str) {
        const norm = normalizeStr(str);
        if (!norm) return '';
        if (CLUB_ALIASES[norm]) return CLUB_ALIASES[norm];
        const stripped = norm
            .replace(/^(1\s+fc|1\s+fsv|fc|cf|ac|as|ss|sv|sc|sd|cd|ud|rc|rcd|fk|sk|bk|if|ifk|ogc|us|afc|ca|vfb|vfl|tsg|bsc|fsv)\s+/, '')
            .replace(/\s+(fc|cf|sc|bk|sv|ac|sd|ud|rc|united|city|hotspur|wanderers|albion|b|ii)$/, '')
            .trim();
        if (CLUB_ALIASES[stripped]) return CLUB_ALIASES[stripped];
        return stripped || norm;
    }

    function isClubMatch(guess, target) {
        if (!guess || !target) return false;
        const strG = typeof guess === 'object' && guess ? (guess.name || guess.Name || '') : String(guess);
        const strT = typeof target === 'object' && target ? (target.name || target.Name || '') : String(target);
        if (!strG || !strT) return false;
        const normG = normalizeStr(strG);
        const normT = normalizeStr(strT);
        if (normG === normT) return true;
        const canonG = canonicalClub(normG);
        const canonT = canonicalClub(normT);
        return Boolean(canonG && canonT && canonG === canonT);
    }

    function isPlayerMatch(guess, target) {
        if (!guess || !target) return false;
        const strG = typeof guess === 'object' ? (guess.Name || guess.name || guess.player_name || '') : String(guess);
        const strT = typeof target === 'object' ? (target.Name || target.name || target.player_name || '') : String(target);
        if (!strG || !strT) return false;
        const normG = normalizeStr(strG).replace(/\s+all$/, '');
        const normT = normalizeStr(strT).replace(/\s+all$/, '');
        return normG === normT;
    }

    // ────────────────────────────────────────────────────────
    // 1. FootyDropdown — Unified autocomplete component
    // ────────────────────────────────────────────────────────
    /**
     * @param {object} cfg
     * @param {string}   cfg.inputId       — ID of the text input
     * @param {string}   cfg.listId        — ID of the dropdown container
     * @param {Array}    cfg.data          — Array of items to search
     * @param {Function} cfg.labelFn       — (item) => string displayed in list
     * @param {Function} [cfg.badgeFn]     — (item) => string for right badge (optional)
     * @param {Function} [cfg.filterFn]    — (item, query) => boolean (optional)
     * @param {Function} cfg.onSelect      — (item) => void called on selection
     * @param {number}   [cfg.maxResults]  — Max dropdown rows (default 200)
     */
    function FootyDropdown(cfg) {
        const input = document.getElementById(cfg.inputId);
        const list = document.getElementById(cfg.listId);
        if (!input || !list) {
            console.warn('[FootyUI] FootyDropdown: element not found', cfg);
            return;
        }

        function getItemLabel(item) {
            if (cfg.labelFn) {
                try {
                    const res = cfg.labelFn(item);
                    if (typeof res === 'string' && res !== '[object Object]') return res;
                } catch (e) {}
            }
            if (item && typeof item === 'object') {
                return item.name || item.Name || item.player_name || item.club_name || '';
            }
            return String(item || '');
        }

        const maxResults = cfg.maxResults || 200;
        let activeIndex = -1;
        let currentItems = [];
        let selectedItem = null;

        function searchAndRank(data, query) {
            const normQ = normalizeStr(query);
            if (!normQ) return [];

            const results = [];
            for (let i = 0; i < data.length; i++) {
                const item = data[i];
                const rawLabel = getItemLabel(item);
                const normLabel = normalizeStr(rawLabel);

                let matches = normLabel.includes(normQ);
                let matchedAlias = null;
                let aliasTier = 99;

                // Check item aliases if present (item.Aliases, item.aliases, item.AltNames)
                const aliases = (item && typeof item === 'object' && (item.Aliases || item.aliases || item.AltNames || item.alt_names)) || [];
                if (Array.isArray(aliases)) {
                    for (let a of aliases) {
                        const normA = normalizeStr(a);
                        if (!normA) continue;
                        if (normA === normQ || normA.split(/\s+/).some(w => w === normQ)) {
                            matches = true;
                            matchedAlias = a;
                            aliasTier = Math.min(aliasTier, 1);
                        } else if (normA.startsWith(normQ) || normA.split(/\s+/).some(w => w.startsWith(normQ))) {
                            matches = true;
                            matchedAlias = a;
                            aliasTier = Math.min(aliasTier, 2);
                        } else if (normA.includes(normQ)) {
                            matches = true;
                            matchedAlias = a;
                            aliasTier = Math.min(aliasTier, 3);
                        }
                    }
                }

                if (!matches && cfg.filterFn) {
                    matches = cfg.filterFn(item, query);
                }

                if (!matches) continue;

                let tier = 4;
                const words = normLabel.split(/\s+/);
                if (normLabel === normQ || words.some(w => w === normQ)) {
                    tier = 1;
                } else if (normLabel.startsWith(normQ) || words.some(w => w.startsWith(normQ))) {
                    tier = 2;
                } else if (normLabel.includes(normQ)) {
                    tier = 3;
                } else if (matchedAlias) {
                    tier = aliasTier <= 2 ? 2 : 3;
                }

                let value = 0;
                if (typeof cfg.valueFn === 'function') {
                    value = Number(cfg.valueFn(item)) || 0;
                } else if (item && typeof item === 'object') {
                    value = Number(item.MarketValue || item.market_value || item.highest_market_value || item.value || 0) || 0;
                }

                results.push({
                    item,
                    tier,
                    value,
                    len: normLabel.length,
                    label: rawLabel,
                    matchedAlias
                });
            }

            results.sort((a, b) => {
                if (a.tier !== b.tier) return a.tier - b.tier;
                if (b.value !== a.value) return b.value - a.value;
                if (a.len !== b.len) return a.len - b.len;
                return a.label.localeCompare(b.label);
            });

            // Deduplicate identical items or spelling variations, while preserving distinct players (homonyms)
            const uniqueResults = [];
            const seenKeys = new Map();
            for (const r of results) {
                const norm = normalizeStr(r.label);
                let dedupeKey = norm;
                if (r.item && typeof r.item === 'object') {
                    const nat = normalizeStr(r.item.Nationality || r.item.country || r.item.country_of_citizenship || '');
                    const pos = normalizeStr(r.item.Position || r.item.position || '');
                    if (nat || pos) {
                        dedupeKey = `${norm}|${nat}|${pos}`;
                    } else if (r.item.id || r.item.player_id) {
                        dedupeKey = `${norm}|${r.item.id || r.item.player_id}`;
                    }
                }
                if (!seenKeys.has(dedupeKey)) {
                    seenKeys.set(dedupeKey, r);
                    uniqueResults.push(r);
                } else {
                    const existing = seenKeys.get(dedupeKey);
                    if (r.value > existing.value) {
                        const idx = uniqueResults.indexOf(existing);
                        if (idx !== -1) {
                            uniqueResults[idx] = r;
                            seenKeys.set(dedupeKey, r);
                        }
                    } else if (r.value === existing.value && /[^\x00-\x7F]/.test(r.label) && !/[^\x00-\x7F]/.test(existing.label)) {
                        // Prefer version with accents or special characters if equal value
                        const idx = uniqueResults.indexOf(existing);
                        if (idx !== -1) {
                            uniqueResults[idx] = r;
                            seenKeys.set(dedupeKey, r);
                        }
                    }
                }
            }

            return uniqueResults.map(r => {
                if (r.item && typeof r.item === 'object') {
                    r.item._matchedAlias = r.matchedAlias;
                }
                return r.item;
            });
        }

        function renderList(items) {
            list.innerHTML = '';
            activeIndex = -1;
            currentItems = items;

            if (!items.length) {
                list.classList.add('hidden');
                return;
            }

            items.forEach((item, idx) => {
                const row = document.createElement('div');
                row.className = 'fa-dropdown-row';
                row.id = `${cfg.listId}-row-${idx}`;

                const itemLabel = getItemLabel(item);
                const label = document.createElement('span');
                label.textContent = itemLabel;
                row.appendChild(label);

                if (item && item._matchedAlias && normalizeStr(item._matchedAlias) !== normalizeStr(itemLabel)) {
                    const aliasHint = document.createElement('span');
                    aliasHint.className = 'text-xs text-amber-400/80 ml-2 font-mono opacity-80';
                    aliasHint.textContent = `(${item._matchedAlias})`;
                    row.appendChild(aliasHint);
                }

                if (cfg.badgeFn) {
                    const badgeText = cfg.badgeFn(item);
                    const isAllAlias = item && (/\(all\)$/i.test(itemLabel) || (typeof item === 'object' && /\(all\)$/i.test(item.Name || item.name || '')));
                    if (badgeText && !isAllAlias) {
                        const badge = document.createElement('span');
                        badge.className = 'fa-row-badge';
                        badge.textContent = badgeText;
                        row.appendChild(badge);
                    }
                }

                row.addEventListener('click', () => select(item));
                list.appendChild(row);
            });


            list.classList.remove('hidden');
        }

        function highlight(idx) {
            currentItems.forEach((_, i) => {
                const row = document.getElementById(`${cfg.listId}-row-${i}`);
                if (!row) return;
                row.classList.toggle('fa-active', i === idx);
                if (i === idx) row.scrollIntoView({ block: 'nearest' });
            });
        }

        function select(item) {
            selectedItem = item;
            input.value = getItemLabel(item);
            list.classList.add('hidden');
            document.getElementById('error-message')?.classList.add('hidden');
            input.focus();
            if (cfg.onSelect) cfg.onSelect(item);
        }

        // Public method — call after programmatic value set to reset selection
        this.clearSelection = () => { selectedItem = null; };

        // Public method — returns the currently selected item (null if none)
        this.getSelected = () => selectedItem;

        // Public method — update dataset
        this.setData = (newData) => { cfg.data = newData; };

        // Public method — clear the input & selection
        this.reset = () => {
            input.value = '';
            selectedItem = null;
            list.classList.add('hidden');
        };

        // Debounce helper
        let debounceTimer = null;
        input.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            selectedItem = null; // typing invalidates a previous selection
            debounceTimer = setTimeout(() => {
                const q = input.value.trim();
                if (!q) { list.classList.add('hidden'); currentItems = []; return; }
                const matches = searchAndRank(cfg.data, q).slice(0, maxResults);
                renderList(matches);
            }, 60);
        });

        input.addEventListener('keydown', (e) => {
            if (list.classList.contains('hidden') || !currentItems.length) {
                // No dropdown open — Enter submits directly
                return;
            }
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                activeIndex = (activeIndex + 1) % currentItems.length;
                highlight(activeIndex);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                activeIndex = (activeIndex - 1 + currentItems.length) % currentItems.length;
                highlight(activeIndex);
            } else if (e.key === 'Enter' || e.key === 'Tab') {
                if (activeIndex >= 0) {
                    e.preventDefault();
                    select(currentItems[activeIndex]);
                } else if (currentItems.length > 0) {
                    e.preventDefault();
                    select(currentItems[0]);
                }
            } else if (e.key === 'Escape') {
                list.classList.add('hidden');
            }
        });

        // Public method — select highlighted item, or fall back to top result
        this.selectHighlightedOrTop = () => {
            if (!currentItems.length) return null;
            const item = activeIndex >= 0 ? currentItems[activeIndex] : currentItems[0];
            select(item);
            return item;
        };

        // Public method — resolve top matching item for a query string
        this.getTopMatch = (query) => {
            const q = (query || input.value || '').trim();
            if (!q) return null;
            const matches = searchAndRank(cfg.data, q);
            return matches.length > 0 ? matches[0] : null;
        };

        // Public method — get current matching items
        this.getCurrentItems = () => currentItems;

        document.addEventListener('click', (e) => {
            if (!input.contains(e.target) && !list.contains(e.target)) {
                list.classList.add('hidden');
            }
        });
    }


    // ────────────────────────────────────────────────────────
    // 2. FootyLives — Life counter with animation
    // ────────────────────────────────────────────────────────
    /**
     * @param {object} cfg
     * @param {string}   cfg.counterId  — ID of the <span> showing the number
     * @param {string}   cfg.heartId    — ID of the heart icon element (optional)
     * @param {number}   cfg.initial    — Starting lives
     * @param {Function} [cfg.onDead]   — Called when lives reach 0
     * @param {Function} [cfg.onChange] — Called whenever lives change (newVal)
     */
    function FootyLives(cfg, onDeadCb) {
        const options = (typeof cfg === 'number')
            ? { initial: cfg, counterId: 'lives-counter', heartId: 'fa-heart-icon', onDead: onDeadCb }
            : (cfg || {});
        let lives = options.initial !== undefined ? options.initial : 5;
        const counterEl = options.counterId ? document.getElementById(options.counterId) : document.getElementById('lives-counter');
        const heartEl = options.heartId ? document.getElementById(options.heartId) : null;

        function update() {
            if (counterEl) counterEl.textContent = lives;

            // Pulse animation on the heart
            const target = heartEl || counterEl?.closest('[data-fa-heart]');
            if (target) {
                target.classList.remove('fa-heart-pulse');
                // Force reflow to restart animation
                void target.offsetWidth;
                target.classList.add('fa-heart-pulse');
            }

            if (cfg.onChange) cfg.onChange(lives);
            if (lives <= 0 && cfg.onDead) cfg.onDead();
        }

        this.get = () => lives;
        this.set = (n) => { lives = n; update(); };
        this.add = (n = 1, reason = 'bonus', opts = {}) => {
            const before = lives;
            lives += n;
            update();
            trackEvent('extra_life', {
                lives: lives,
                extraDetails: `before: ${before} | after: ${lives} | added: ${n} | reason: ${reason}`
            });
            if (!opts?.silent && reason !== 'var' && reason !== 'var_overrule') {
                const isEs = (typeof FootyI18n !== 'undefined' && FootyI18n.getLang && FootyI18n.getLang() === 'es') ||
                             (typeof document !== 'undefined' && document.documentElement.lang === 'es') ||
                             (typeof location !== 'undefined' && location.pathname.includes('/es/'));
                const toastMsg = (typeof FootyI18n !== 'undefined' && FootyI18n.t)
                    ? FootyI18n.t('toast_life_added')
                    : (isEs ? '¡+1 Vida! ❤️' : '+1 Life! ❤️');
                toast(toastMsg, 'success');
            }
        };
        this.lose = (n = 1) => { lives = Math.max(0, lives - n); update(); };
        this.isDead = () => lives <= 0;

        // Render initial value
        if (counterEl) counterEl.textContent = lives;
    }


    // Shared Giphy GIF fetcher
    function fetchGiphyGif(query, callback) {
        if (!query) return callback(null);
        const apiKey = window.GIPHY_API_KEY || 'hAjBkiCSPhfKZhcg0knhPOGhVVEA6EUD';
        const url = `https://api.giphy.com/v1/gifs/search?api_key=${encodeURIComponent(apiKey)}&q=${encodeURIComponent(query)}&limit=10&rating=g`;

        fetch(url)
            .then(res => res.json())
            .then(data => {
                if (data && data.data && data.data.length > 0) {
                    const randomIndex = Math.floor(Math.random() * Math.min(data.data.length, 5));
                    const gifObj = data.data[randomIndex];
                    const gifUrl = gifObj.images?.downsized_medium?.url || gifObj.images?.fixed_height?.url || gifObj.images?.original?.url;
                    callback(gifUrl);
                } else {
                    callback(null);
                }
            })
            .catch(err => {
                console.warn('Giphy API fetch failed:', err);
                callback(null);
            });
    }

    // ────────────────────────────────────────────────────────
    // 3. FootyModal — End-game modal (success / failure)
    // ────────────────────────────────────────────────────────
    /**
     * @param {object} cfg
     * @param {string}   cfg.modalId        — Wrapper div ID (default "result-modal")
     * @param {string}   cfg.iconId         — material icon element ID
     * @param {string}   cfg.titleId        — h3 element ID
     * @param {string}   cfg.messageId      — p element ID
     * @param {string}   cfg.scoreId        — score span ID
     * @param {string}   cfg.streakId       — streak span ID
     * @param {string}   [cfg.extraInfoId]  — optional extra element (e.g. player name)
     * @param {string}   [cfg.backInTimeContainerId] — container for back-in-time links
     */
    function FootyModal(cfg) {
        const modal = document.getElementById(cfg.modalId || 'result-modal');
        let hasTrackedGameEnd = false;

        this.resetTracking = () => {
            hasTrackedGameEnd = false;
        };

        function buildGiphyQuery(opts) {
            const isPartial = opts.outcome === 'partial' || opts.isPartial;
            if (isPartial) {
                if (opts.partialQuery) return opts.partialQuery;
                if (opts.query) return opts.query;
                const targetName = (opts.targetName || '').trim();
                const playerName = (opts.playerName || opts.extraText || '').trim();
                const name = playerName || targetName;
                if (name) {
                    return `${name} football respect`;
                }
                return 'football applause';
            }

            if (!opts.won) {
                return 'soccer fail';
            }

            if (opts.query) return opts.query;

            const targetName = (opts.targetName || '').trim();
            const playerName = (opts.playerName || opts.extraText || '').trim();
            const type = opts.targetType || opts.mode || '';

            // Common national teams list for automatic national team query detection
            const NATIONAL_TEAMS = [
                'Italy', 'Brazil', 'France', 'Spain', 'Argentina', 'Germany', 'England', 
                'Portugal', 'Netherlands', 'Belgium', 'Croatia', 'Uruguay', 'Colombia', 
                'Senegal', 'Japan', 'Morocco', 'Nigeria', 'Cameroon', 'Ivory Coast',
                'Mexico', 'USA', 'United States', 'Wales', 'Scotland', 'Poland', 'Denmark',
                'Sweden', 'Switzerland', 'Austria', 'Norway', 'Algeria', 'Egypt', 'Ghana'
            ];

            const isNationalTeam = type === 'nationality' || type === 'national_team' || 
                (targetName && NATIONAL_TEAMS.some(team => team.toLowerCase() === targetName.toLowerCase()));

            if (isNationalTeam) {
                return `${targetName} football team`;
            }

            // If a player name (like the #1 player in a league or grid) is provided, use it
            if (playerName) {
                return playerName;
            }

            if (targetName) {
                return targetName;
            }

            return 'soccer celebration';
        }

        this.show = (opts) => {
            opts = opts || {};
            const outcome = opts.outcome || (opts.won ? 'win' : (opts.isPartial ? 'partial' : 'loss'));
            const isWin = outcome === 'win';
            const isPartial = outcome === 'partial';

            // Track game completion only when the game actively ends (not on page restore or modal re-open)
            const isRestore = Boolean(opts.isRestore || opts.restore || opts.track === false);
            if (!isRestore && !hasTrackedGameEnd) {
                hasTrackedGameEnd = true;
                trackEvent('game_end', {
                    won: opts.won,
                    outcome: outcome,
                    score: opts.score,
                    maxScore: opts.maxScore,
                    extraDetails: opts.title
                });
            }

            // opts: { won, outcome, isPartial, score, maxScore, streak, extraText, shareText, backInTimeLinks, playerName, targetName, targetType }
            const iconEl = document.getElementById(cfg.iconId || 'modal-icon');
            const titleEl = document.getElementById(cfg.titleId || 'modal-title');
            const msgEl = document.getElementById(cfg.messageId || 'modal-message');
            const scoreEl = (cfg.scoreId !== undefined && cfg.scoreId !== null)
                ? (cfg.scoreId ? document.getElementById(cfg.scoreId) : null)
                : document.getElementById('modal-score');
            const streakEl = document.getElementById(cfg.streakId || 'modal-streak');
            const modalCard = modal ? (modal.querySelector('.fa-modal-card') || modal.firstElementChild) : null;

            if (modalCard) {
                if (isPartial) {
                    modalCard.classList.add('is-partial');
                } else {
                    modalCard.classList.remove('is-partial');
                }
            }

            if (iconEl) {
                if (isWin) {
                    iconEl.textContent = 'emoji_events';
                    iconEl.className = 'material-symbols-outlined text-6xl text-accent';
                } else if (isPartial) {
                    iconEl.textContent = 'military_tech';
                    iconEl.className = 'material-symbols-outlined text-6xl text-amber-400';
                } else {
                    iconEl.textContent = 'dangerous';
                    iconEl.className = 'material-symbols-outlined text-6xl text-error';
                }
            }
            if (titleEl) {
                const defaultTitle = isWin
                    ? (typeof FootyI18n !== 'undefined' ? FootyI18n.t('outcome_win_title') : 'COMPLETED!')
                    : (isPartial
                        ? (typeof FootyI18n !== 'undefined' ? FootyI18n.t('outcome_partial_title') : 'GRITTY FINISH!')
                        : (typeof FootyI18n !== 'undefined' ? FootyI18n.t('outcome_loss_title') : 'GAME OVER'));
                titleEl.textContent = opts.title || defaultTitle;
                titleEl.className = `font-headline text-3xl sm:text-4xl uppercase italic tracking-wide ${isWin ? 'text-accent' : (isPartial ? 'text-amber-400' : 'text-error')}`;
            }
            if (msgEl) {
                const defaultMsg = isWin ? '' : (isPartial
                    ? (typeof FootyI18n !== 'undefined'
                        ? FootyI18n.t('outcome_partial_default_msg', { score: opts.score, maxScore: opts.maxScore })
                        : `You reached the final whistle! Score: ${opts.score}/${opts.maxScore}. Not a clean sheet, but a resilient shift.`)
                    : (typeof FootyI18n !== 'undefined' ? FootyI18n.t('outcome_loss_default_msg') : ''));
                msgEl.textContent = opts.message || defaultMsg;
            }
            if (scoreEl) {
                scoreEl.textContent = `${opts.score}/${opts.maxScore}`;
                if (isPartial) {
                    scoreEl.className = 'font-headline text-2xl sm:text-3xl text-amber-400';
                } else if (isWin) {
                    scoreEl.className = 'font-headline text-2xl sm:text-3xl text-correct';
                } else {
                    scoreEl.className = 'font-headline text-2xl sm:text-3xl text-on-surface-variant';
                }
            }
            if (streakEl) streakEl.textContent = opts.streak;

            if (cfg.extraInfoId && opts.extraText) {
                const el = document.getElementById(cfg.extraInfoId);
                if (el) el.textContent = opts.extraText;
            }

            // Giphy GIF integration
            let gifContainer = document.getElementById(cfg.gifContainerId || 'modal-gif-container');
            let gifEl = document.getElementById(cfg.gifId || 'modal-gif');

            if (!gifContainer && modal) {
                if (modalCard) {
                    gifContainer = document.createElement('div');
                    gifContainer.id = cfg.gifContainerId || 'modal-gif-container';
                    gifContainer.className = 'w-full max-h-48 sm:max-h-56 rounded-2xl overflow-hidden bg-black/60 border border-white/10 flex items-center justify-center relative my-2 sm:my-3 hidden';
                    gifEl = document.createElement('img');
                    gifEl.id = cfg.gifId || 'modal-gif';
                    gifEl.className = 'max-w-full max-h-48 sm:max-h-56 w-auto h-auto object-contain rounded-xl';
                    gifContainer.appendChild(gifEl);

                    const msgElParent = msgEl?.parentElement || titleEl?.parentElement;
                    if (msgElParent && msgElParent.nextSibling) {
                        modalCard.insertBefore(gifContainer, msgElParent.nextSibling);
                    } else {
                        modalCard.appendChild(gifContainer);
                    }
                }
            }

            if (gifContainer && gifEl) {
                gifContainer.classList.add('hidden');
                gifEl.src = '';
                // Ensure responsive non-crop classes if HTML already had fixed object-cover
                gifContainer.classList.remove('max-h-36');
                gifContainer.classList.add('max-h-48', 'sm:max-h-56');
                gifEl.classList.remove('object-cover', 'h-36', 'sm:h-44');
                gifEl.classList.add('object-contain', 'w-auto', 'h-auto', 'mx-auto', 'max-h-48', 'sm:max-h-56');

                const query = buildGiphyQuery(opts);

                fetchGiphyGif(query, (gifUrl) => {
                    if (gifUrl) {
                        gifEl.src = gifUrl;
                        gifContainer.classList.remove('hidden');
                    } else if (isPartial && query !== 'football applause') {
                        fetchGiphyGif('football applause', (fallbackUrl) => {
                            if (fallbackUrl) {
                                gifEl.src = fallbackUrl;
                                gifContainer.classList.remove('hidden');
                            }
                        });
                    } else if (opts.won && query !== 'soccer celebration') {
                        // Fallback search if specific GIF not found
                        fetchGiphyGif('soccer celebration', (fallbackUrl) => {
                            if (fallbackUrl) {
                                gifEl.src = fallbackUrl;
                                gifContainer.classList.remove('hidden');
                            }
                        });
                    }
                });
            }

            // Results Emoji Preview Container
            let emojiPreviewEl = document.getElementById('modal-emoji-preview');
            const emojiGrid = opts.customEmojiGrid || buildEmojiGrid(opts.score, opts.maxScore, opts.won, isPartial);

            if (!emojiPreviewEl && modal) {
                const bitWrapper = document.getElementById('bit-wrapper');
                emojiPreviewEl = document.createElement('div');
                emojiPreviewEl.id = 'modal-emoji-preview';
                emojiPreviewEl.className = 'w-full py-2 px-3 bg-black/40 border border-white/10 rounded-xl my-2 text-center font-mono text-sm sm:text-base tracking-widest leading-normal text-white select-all cursor-pointer hover:border-accent/40 transition-all';

                
                if (bitWrapper && bitWrapper.parentElement === modalCard) {
                    modalCard.insertBefore(emojiPreviewEl, bitWrapper);
                } else {
                    const actionGroup = modal.querySelector('#modal-share-btn')?.parentElement || modal.querySelector('.flex.gap-3.pt-1');
                    if (actionGroup) {
                        modalCard.insertBefore(emojiPreviewEl, actionGroup);
                    } else {
                        modalCard.appendChild(emojiPreviewEl);
                    }
                }
            }

            if (emojiPreviewEl) {
                const isEs = (typeof FootyI18n !== 'undefined' && FootyI18n.getLang() === 'es');
                const cardLabel = isEs ? 'Tu Tarjeta para Compartir' : 'Your Share Card';
                const cardTitle = isEs ? 'Clic para copiar resultado' : 'Click to copy result';
                emojiPreviewEl.innerHTML = `
                    <div class="text-[10px] uppercase font-mono tracking-widest text-on-surface-variant mb-0.5">${cardLabel}</div>
                    <div class="whitespace-pre-line font-medium">${emojiGrid}</div>
                `;
                emojiPreviewEl.title = cardTitle;
                emojiPreviewEl.onclick = () => share(opts);
            }

            // WhatsApp Share Button Integration
            let waBtn = document.getElementById('modal-whatsapp-btn');
            const shareBtn = document.getElementById('modal-share-btn');
            if (!waBtn && shareBtn && shareBtn.parentElement) {
                waBtn = document.createElement('button');
                waBtn.id = 'modal-whatsapp-btn';
                waBtn.className = 'flex-1 py-3 bg-[#25D366] text-black font-headline text-sm sm:text-base uppercase italic rounded-xl hover:brightness-110 active:scale-95 transition-all flex items-center justify-center gap-1.5 shadow-lg shadow-[#25D366]/20';
                waBtn.innerHTML = '<span class="material-symbols-outlined text-base">chat</span> WHATSAPP';
                shareBtn.parentElement.insertBefore(waBtn, shareBtn);
            }

            if (waBtn) {
                waBtn.onclick = (e) => {
                    e.preventDefault();
                    shareWhatsApp(opts);
                };
            }
            if (shareBtn) {
                shareBtn.onclick = (e) => {
                    e.preventDefault();
                    share(opts);
                };
            }

            // Back-in-time links
            if (cfg.backInTimeContainerId && opts.backInTimeLinks?.length) {
                const container = document.getElementById(cfg.backInTimeContainerId);
                if (container) {
                    container.innerHTML = '';
                    opts.backInTimeLinks.forEach(link => {
                        const a = document.createElement('a');
                        a.href = link.href;
                        a.className = 'fa-bit-link';
                        a.innerHTML = `<span class="material-symbols-outlined" style="font-size:14px">history</span>${link.label}`;
                        container.appendChild(a);
                    });
                    container.parentElement?.classList.remove('hidden');
                }
            }

            lastEndGameOpts = opts;
            modal?.classList.remove('hidden');
        };

        this.hide = () => modal?.classList.add('hidden');
    }

    let lastEndGameOpts = null;

    // ────────────────────────────────────────────────────────
    // 4. FootyShare — Standardised Game-Specific Share Cards
    // ────────────────────────────────────────────────────────
    /**
     * Constructs a clean canonical share URL with the given source parameter (e.g. utm_source=whatsapp or utm_source=share).
     * Automatically strips existing tracking parameters to prevent compounding.
     */
    function buildShareUrl(rawUrl, source) {
        let base = rawUrl;
        if (!base) {
            if (typeof window !== 'undefined' && window.location) {
                const host = window.location.hostname;
                const path = window.location.pathname;
                if (host === 'playmaker.best' || host === 'www.playmaker.best') {
                    base = window.location.href;
                } else if (path && path !== '/') {
                    base = 'https://playmaker.best' + (path.startsWith('/') ? path : '/' + path);
                } else {
                    base = window.location.href;
                }
            } else {
                base = 'https://playmaker.best/';
            }
        }
        try {
            const parsed = new URL(base, 'https://playmaker.best');
            parsed.searchParams.delete('utm_source');
            parsed.searchParams.delete('utm_medium');
            parsed.searchParams.delete('utm_campaign');
            parsed.searchParams.delete('ref');
            parsed.searchParams.delete('source');
            if (source) {
                parsed.searchParams.set('utm_source', source);
            }
            return parsed.toString();
        } catch (e) {
            const clean = (base || 'https://playmaker.best/').split('?')[0];
            return source ? `${clean}?utm_source=${encodeURIComponent(source)}` : clean;
        }
    }

    /**
     * Detects incoming traffic source from URL query parameters (utm_source, ref, source)
     * or session storage, or document.referrer.
     */
    function getUrlSource() {
        if (typeof window === 'undefined' || !window.location) return '';
        try {
            const params = new URLSearchParams(window.location.search);
            const source = params.get('utm_source') || params.get('ref') || params.get('source');
            if (source) {
                const cleanSource = source.trim().toLowerCase();
                try {
                    sessionStorage.setItem('fa_url_source', cleanSource);
                } catch (e) {}
                return cleanSource;
            }
            const stored = sessionStorage.getItem('fa_url_source');
            if (stored) return stored;

            // Fallback to document.referrer if available
            if (document.referrer) {
                const ref = document.referrer.toLowerCase();
                if (ref.includes('whatsapp') || ref.includes('wa.me')) {
                    try { sessionStorage.setItem('fa_url_source', 'whatsapp'); } catch (e) {}
                    return 'whatsapp';
                }
                if (ref.includes('twitter.com') || ref.includes('t.co') || ref.includes('x.com')) {
                    try { sessionStorage.setItem('fa_url_source', 'twitter'); } catch (e) {}
                    return 'twitter';
                }
                if (ref.includes('instagram.com')) {
                    try { sessionStorage.setItem('fa_url_source', 'instagram'); } catch (e) {}
                    return 'instagram';
                }
                if (ref.includes('facebook.com')) {
                    try { sessionStorage.setItem('fa_url_source', 'facebook'); } catch (e) {}
                    return 'facebook';
                }
                if (ref.includes('reddit.com')) {
                    try { sessionStorage.setItem('fa_url_source', 'reddit'); } catch (e) {}
                    return 'reddit';
                }
            }
        } catch (e) {}
        return '';
    }

    /**
     * Builds game-specific spoiler-free share text for any game.
     */
    function buildShareText(opts, source) {
        opts = opts || lastEndGameOpts || {};
        const meta = getActiveGameMetadata();
        const gameId = opts.gameId || meta.gameId;
        const puzzleNum = opts.puzzleNum !== undefined ? opts.puzzleNum : meta.puzzleNum;
        const score = opts.score !== undefined ? opts.score : 0;
        const maxScore = opts.maxScore !== undefined ? opts.maxScore : 10;
        const won = !!opts.won;
        const outcome = opts.outcome || (won ? 'win' : (opts.isPartial ? 'partial' : 'loss'));
        const isPartial = outcome === 'partial';
        const lives = opts.lives !== undefined ? opts.lives : 0;
        const initialLives = opts.initialLives !== undefined ? opts.initialLives : 5;
        const livesUsed = Math.max(0, initialLives - lives);
        const shareSource = source || opts.shareSource || opts.source || 'share';
        const url = buildShareUrl(opts.url, shareSource);

        const isEs = (typeof FootyI18n !== 'undefined' && FootyI18n.getLang() === 'es') ||
                     (typeof window !== 'undefined' && window.location && window.location.pathname.includes('/es/'));

        let titleLine = isEs
            ? `⚽ Playmaker: ${opts.gameName || (typeof FootyI18n !== 'undefined' ? FootyI18n.t('game_' + gameId) : 'Trivia de Fútbol')} #${puzzleNum}`
            : `⚽ Playmaker: ${opts.gameName || 'Daily Football Quiz'} #${puzzleNum}`;
        let subLine = '';
        let emojiGrid = opts.customEmojiGrid || '';
        let statusLine = '';
        const challengeLine = isEs
            ? (typeof FootyI18n !== 'undefined' ? FootyI18n.t('share_challenge') : '¿Puedes superar mi puntuación?')
            : 'Can you beat my score?';

        if (!emojiGrid) {
            emojiGrid = buildEmojiGrid(score, maxScore, won, isPartial);
        }

        switch (gameId) {
            case 'top_transfers': {
                titleLine = isEs ? `⚽ Playmaker: Top Fichajes #${puzzleNum}` : `⚽ Playmaker: Top Transfers #${puzzleNum}`;
                const target = opts.targetName || (typeof DAILY_TRANSFER_GAME !== 'undefined' ? DAILY_TRANSFER_GAME.name : (isEs ? 'Fichajes Récord' : 'Record Transfers'));
                subLine = isEs ? `🏛️ ${target}: Fichajes Récord` : `🏛️ ${target}: Record Transfers`;
                if (isEs) {
                    statusLine = won 
                        ? `🏆 ¡TODOS LOS ${maxScore} FICHAJES ENCONTRADOS! · ❤️ ${lives} vidas`
                        : (isPartial
                            ? `🎖️ ¡TABLERO COMPLETADO! · ${score}/${maxScore} fichajes encontrados · ❤️ ${lives} vidas`
                            : `🎯 ${score}/${maxScore} fichajes encontrados · ❤️ ${lives} vidas`);
                } else {
                    statusLine = won 
                        ? `🏆 ALL ${maxScore} TRANSFERS FOUND! · ❤️ ${lives} left`
                        : (isPartial
                            ? `🎖️ BOARD CLEARED! · ${score}/${maxScore} transfers found · ❤️ ${lives} left`
                            : `🎯 ${score}/${maxScore} transfers found · ❤️ ${lives} left`);
                }
                break;
            }
            case 'transfer_destination': {
                titleLine = isEs ? `⚽ Playmaker: Destino de Fichaje #${puzzleNum}` : `⚽ Playmaker: Transfer Destination #${puzzleNum}`;
                subLine = isEs ? `🧭 Trayectoria del Jugador (${maxScore} Fichajes)` : `🧭 Mystery Player Career Path (${maxScore} Transfers)`;
                if (isEs) {
                    statusLine = won
                        ? `🌟 ¡TRAYECTORIA COMPLETADA! · ❤️ ${lives} vidas`
                        : (isPartial
                            ? `🎖️ ¡TRAYECTORIA SUPERADA! · ${score}/${maxScore} clubes adivinados · ❤️ ${lives} vidas`
                            : `🎯 ${score}/${maxScore} clubes adivinados · ❤️ ${lives} vidas`);
                } else {
                    statusLine = won
                        ? `🌟 CAREER PATH COMPLETED! · ❤️ ${lives} left`
                        : (isPartial
                            ? `🎖️ CAREER SURVIVED! · ${score}/${maxScore} clubs guessed backwards · ❤️ ${lives} left`
                            : `🎯 ${score}/${maxScore} clubs guessed backwards · ❤️ ${lives} left`);
                }
                break;
            }
            case 'club_connect': {
                titleLine = isEs ? `⚽ Playmaker: Conexión de Clubes #${puzzleNum}` : `⚽ Playmaker: Club Connect #${puzzleNum}`;
                subLine = isEs ? `🔍 Conexión de Club Misterioso` : `🔍 Mystery Club Connection`;
                if (isEs) {
                    statusLine = won
                        ? `✨ ¡CONECTADO EN ${score} PISTA${score > 1 ? 'S' : ''}! · ❤️ ${lives} vidas`
                        : `❌ Conexión Fallida · 💔 Sin vidas`;
                } else {
                    statusLine = won
                        ? `✨ CONNECTED IN ${score} REVEAL${score > 1 ? 'S' : ''}! · ❤️ ${lives} left`
                        : `❌ Connection Missed · 💔 Out of lives`;
                }
                break;
            }
            case 'player_chain': {
                titleLine = isEs ? `⚽ Playmaker: Cadena de Jugadores #${puzzleNum}` : `⚽ Playmaker: Player Chain #${puzzleNum}`;
                subLine = isEs ? `🔗 Cadena de Compañeros (${maxScore} Pasos)` : `🔗 Teammate Chain (${maxScore} Steps)`;
                if (opts.didInstantWin) {
                    statusLine = isEs
                        ? `⭐️ ¡VICTORIA DIRECTA! · 🎯 ¡Conexión en 1 solo paso!`
                        : `⭐️ INSTANT WIN! · 🎯 1-step direct teammate connection!`;
                } else {
                    if (isEs) {
                        statusLine = won
                            ? `✅ ¡CADENA PERFECTA! · ❤️ ${lives} vidas`
                            : (isPartial
                                ? `🎖️ ¡CADENA SUPERADA! · ${score}/${maxScore} pasos resueltos · ❤️ ${lives} vidas`
                                : `🎯 ${score}/${maxScore} pasos resueltos · ❤️ ${lives} vidas`);
                    } else {
                        statusLine = won
                            ? `✅ PERFECT CHAIN! · ❤️ ${lives} left`
                            : (isPartial
                                ? `🎖️ CHAIN SURVIVED! · ${score}/${maxScore} steps solved · ❤️ ${lives} left`
                                : `🎯 ${score}/${maxScore} steps solved · ❤️ ${lives} left`);
                    }
                }
                break;
            }
            case 'top_scorers': {
                titleLine = isEs ? `⚽ Playmaker: Máximos Goleadores #${puzzleNum}` : `⚽ Playmaker: Top Scorers #${puzzleNum}`;
                const target = opts.targetName || (typeof DAILY_SCORERS_GAME !== 'undefined' ? `${DAILY_SCORERS_GAME.league} ${DAILY_SCORERS_GAME.season}` : (isEs ? 'Bota de Oro' : 'Golden Boot'));
                subLine = isEs ? `🏆 ${target} Bota de Oro` : `🏆 ${target} Golden Boot`;
                if (isEs) {
                    statusLine = won
                        ? `👑 ¡TODOS LOS ${maxScore} GOLEADORES ENCONTRADOS! · ❤️ ${lives} vidas`
                        : (isPartial
                            ? `🎖️ ¡TABLERO COMPLETADO! · ${score}/${maxScore} goleadores adivinados · ❤️ ${lives} vidas`
                            : `🎯 ${score}/${maxScore} goleadores adivinados · ❤️ ${lives} vidas`);
                } else {
                    statusLine = won
                        ? `👑 ALL ${maxScore} TOP SCORERS FOUND! · ❤️ ${lives} left`
                        : (isPartial
                            ? `🎖️ BOARD CLEARED! · ${score}/${maxScore} top scorers guessed · ❤️ ${lives} left`
                            : `🎯 ${score}/${maxScore} top scorers guessed · ❤️ ${lives} left`);
                }
                break;
            }
            case 'passport_fc': {
                titleLine = isEs ? `⚽ Playmaker: Pasaporte FC #${puzzleNum}` : `⚽ Playmaker: Passport FC #${puzzleNum}`;
                const club = opts.targetName || (typeof DAILY_PASSPORT_GAME !== 'undefined' ? DAILY_PASSPORT_GAME.club : (isEs ? 'Pasaporte de Club' : 'Club Passport'));
                subLine = isEs ? `✈️ Pasaporte de Club: ${club}` : `✈️ Club Passport: ${club}`;
                if (isEs) {
                    statusLine = won
                        ? `🌟 ¡PASAPORTE COMPLETADO! · ❤️ ${lives} vidas`
                        : (isPartial
                            ? `🎖️ ¡PASAPORTE SUPERADO! · ${score}/${maxScore} sellos obtenidos · ❤️ ${lives} vidas`
                            : `🎯 ${score}/${maxScore} sellos obtenidos · ❤️ ${lives} vidas`);
                } else {
                    statusLine = won
                        ? `🌟 PASSPORT COMPLETED! · ❤️ ${lives} left`
                        : (isPartial
                            ? `🎖️ LADDER SURVIVED! · ${score}/${maxScore} stamps collected · ❤️ ${lives} left`
                            : `🎯 ${score}/${maxScore} stamps collected · ❤️ ${lives} left`);
                }
                break;
            }
            default: {
                titleLine = isEs
                    ? `⚽ Playmaker: ${opts.gameName || 'Trivia de Fútbol'} #${puzzleNum}`
                    : `⚽ Playmaker: ${opts.gameName || 'Daily Quiz'} #${puzzleNum}`;
                if (isEs) {
                    statusLine = won 
                        ? `✅ ${score}/${maxScore} correctos · ❤️ ${lives} vidas` 
                        : (isPartial
                            ? `🎖️ ${score}/${maxScore} correctos · ❤️ ${lives} vidas`
                            : `❌ ${score}/${maxScore} correctos · ❤️ ${lives} vidas`);
                } else {
                    statusLine = won 
                        ? `✅ ${score}/${maxScore} correct · ❤️ ${lives} left` 
                        : (isPartial
                            ? `🎖️ ${score}/${maxScore} correct · ❤️ ${lives} left`
                            : `❌ ${score}/${maxScore} correct · ❤️ ${lives} left`);
                }
                break;
            }
        }

        const lines = [
            titleLine,
            subLine,
            emojiGrid,
            statusLine,
            challengeLine,
            `🔗 ${url}`
        ].filter(Boolean);

        return lines.join('\n');
    }

    /**
     * Builds and copies the canonical share text for any game.
     */
    let _lastShareTime = 0;
    function share(opts) {
        const now = Date.now();
        if (now - _lastShareTime < 600) return;
        _lastShareTime = now;

        opts = opts || lastEndGameOpts || {};
        const shareSource = opts.source || opts.shareSource || 'share';
        const text = buildShareText(opts, shareSource);
        const shareUrl = buildShareUrl(opts.url, shareSource);

        trackEvent('share', {
            method: 'clipboard',
            urlSource: shareSource,
            shareUrl: shareUrl,
            extraDetails: `source: ${shareSource}`,
            gameId: opts.gameId || getActiveGameMetadata().gameId,
            won: opts.won,
            outcome: opts.outcome || (opts.won ? 'win' : (opts.isPartial ? 'partial' : 'loss')),
            score: opts.score,
            maxScore: opts.maxScore,
            lives: opts.lives
        });

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text)
                .then(() => toast('Copied result to clipboard!', 'success'))
                .catch(() => _fallbackShare(text));
        } else {
            _fallbackShare(text);
        }
    }

    /**
     * Opens WhatsApp with pre-filled share card text.
     */
    let _lastWaTime = 0;
    function shareWhatsApp(opts) {
        const now = Date.now();
        if (now - _lastWaTime < 600) return;
        _lastWaTime = now;

        opts = opts || lastEndGameOpts || {};
        const shareSource = 'whatsapp';
        const text = buildShareText(opts, shareSource);
        const shareUrl = buildShareUrl(opts.url, shareSource);

        trackEvent('share', {
            method: 'whatsapp',
            urlSource: shareSource,
            shareUrl: shareUrl,
            extraDetails: `source: ${shareSource}`,
            gameId: opts.gameId || getActiveGameMetadata().gameId,
            won: opts.won,
            outcome: opts.outcome || (opts.won ? 'win' : (opts.isPartial ? 'partial' : 'loss')),
            score: opts.score,
            maxScore: opts.maxScore,
            lives: opts.lives
        });

        const waUrl = 'https://api.whatsapp.com/send?text=' + encodeURIComponent(text);
        window.open(waUrl, '_blank', 'noopener,noreferrer');
    }

    function buildEmojiGrid(score, maxScore, won, isPartial = false) {
        const cells = [];
        for (let i = 0; i < maxScore; i++) {
            if (i < score) {
                cells.push('🟩');
            } else if (isPartial) {
                cells.push('🟨');
            } else {
                cells.push('⬛');
            }
        }
        // Group into rows of 5
        const rows = [];
        for (let i = 0; i < cells.length; i += 5) {
            rows.push(cells.slice(i, i + 5).join(''));
        }
        return rows.join('\n');
    }

    function _fallbackShare(text) {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        toast('Copied to clipboard!', 'success');
    }

    /**
     * Shows a custom toast alert.
     * @param {string} msg 
     * @param {'success'|'error'|'info'} [type='info'] 
     */
    function toast(msg, type = 'info') {
        let container = document.getElementById('fa-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'fa-toast-container';
            document.body.appendChild(container);
        }

        const item = document.createElement('div');
        item.className = `fa-toast-item fa-toast-${type}`;
        item.textContent = msg;

        container.appendChild(item);

        // Auto remove after animation finishes
        setTimeout(() => {
            item.style.opacity = '0';
            setTimeout(() => item.remove(), 300);
        }, 2200);
    }

    /**
     * Shows a beautiful theme-aware custom confirmation modal.
     * @param {object} opts
     * @param {string} opts.title
     * @param {string} opts.message
     * @param {string} [opts.confirmText='CONFIRM']
     * @param {string} [opts.cancelText='CANCEL']
     * @param {Function} opts.onConfirm
     * @param {Function} [opts.onCancel]
     */
    function confirmModal(opts) {
        const isEs = (typeof FootyI18n !== 'undefined' && FootyI18n.getLang() === 'es');
        const defaultCancel = isEs ? 'CANCELAR' : 'CANCEL';
        const defaultConfirm = isEs ? 'CONFIRMAR' : 'CONFIRM';

        const backdrop = document.createElement('div');
        backdrop.className = 'fa-confirm-backdrop';

        const card = document.createElement('div');
        card.className = 'fa-confirm-card';

        card.innerHTML = `
            <h4 class="font-headline text-2xl text-accent uppercase italic tracking-wide mb-2">${opts.title}</h4>
            <p class="text-on-surface-variant text-sm mb-6">${opts.message}</p>
            <div class="flex gap-3 justify-center">
                <button id="fa-confirm-cancel" class="flex-1 py-2.5 bg-surface-container-high border border-white/10 text-white font-headline text-md uppercase italic rounded-xl hover:bg-surface-container-highest transition-all">
                    ${opts.cancelText || defaultCancel}
                </button>
                <button id="fa-confirm-ok" class="flex-1 py-2.5 bg-accent text-black font-headline text-md uppercase italic rounded-xl hover:brightness-110 active:scale-95 transition-all">
                    ${opts.confirmText || defaultConfirm}
                </button>
            </div>
        `;

        backdrop.appendChild(card);
        document.body.appendChild(backdrop);

        const close = (cb) => {
            backdrop.remove();
            if (cb) cb();
        };

        document.getElementById('fa-confirm-ok').onclick = () => close(opts.onConfirm);
        document.getElementById('fa-confirm-cancel').onclick = () => close(opts.onCancel);
    }

    // ── VAR System State ──────────────────────────────────────────
    const varState = {
        checkedPlayers: new Set(),
        tokens: 1,           // Player starts with 1 token!
        successfulUses: 0,   // Number of successful appeals
        maxSuccess: 3        // Hard cap: max 3 successful reviews per game
    };

    /**
     * Shows a transient right/wrong answer feedback popup with optional VAR review button.
     * @param {object} opts
     * @param {boolean} opts.isCorrect
     * @param {string} opts.title
     * @param {string} opts.message
     * @param {string} [opts.guess]
     * @param {string} [opts.gameId]
     * @param {number} [opts.puzzleNum]
     * @param {string} [opts.theme]
     * @param {string} [opts.context]
     * @param {boolean} [opts.canVar]
     * @param {Function} [opts.onVarAccepted]
     * @param {Function} [opts.onVarRejected]
     */
    function showFeedback(opts) {
        // Clean up any existing feedback cards to avoid stacking
        document.querySelectorAll('.fa-feedback-backdrop').forEach(el => el.remove());

        // Dispatch bottom toast for high visibility across mobile & desktop viewports
        const toastMsg = opts.title ? `${opts.title} ${opts.message ? '— ' + opts.message : ''}` : (opts.message || (opts.isCorrect ? 'Correct!' : 'Incorrect!'));
        toast(toastMsg, opts.isCorrect ? 'success' : 'error');

        const meta = getActiveGameMetadata();
        const gameId = opts.gameId || meta.gameId;
        const isVarSupportedGame = ['top_scorers', 'top_transfers', 'player_chain', 'passport_fc'].includes(gameId);
        const normGuess = opts.guess ? normalizeStr(opts.guess) : '';
        const alreadyChecked = normGuess && varState.checkedPlayers.has(normGuess);
        const hasToken = varState.tokens > 0 && varState.successfulUses < varState.maxSuccess;
        const canShowVar = !opts.isCorrect && opts.canVar !== false && isVarSupportedGame && Boolean(opts.guess) && !alreadyChecked && hasToken;

        const backdrop = document.createElement('div');
        backdrop.className = 'fa-feedback-backdrop';

        const card = document.createElement('div');
        card.className = 'fa-feedback-card';

        const color = opts.isCorrect ? '#39ff14' : '#ff4d4d';
        const glow = opts.isCorrect ? 'rgba(57, 255, 20, 0.35)' : 'rgba(255, 77, 77, 0.35)';

        card.style.setProperty('--feedback-color', color);
        card.style.setProperty('--feedback-glow', glow);

        card.innerHTML = `
            <span class="material-symbols-outlined text-4xl shrink-0" style="color: ${color}">
                ${opts.isCorrect ? 'check_circle' : 'cancel'}
            </span>
            <div style="flex: 1;">
                <h4 class="font-headline text-lg uppercase italic tracking-wide" style="color: ${color}; margin: 0; line-height: 1.2;">
                    ${opts.title}
                </h4>
                <p class="text-on-surface-variant text-xs font-semibold" style="margin: 4px 0 0 0; color: #a3a3a3; line-height: 1.3;">
                    ${opts.message}
                </p>
                ${canShowVar ? `
                <div style="margin-top: 8px; display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                    <button id="fa-feedback-var-btn" class="fa-var-btn" type="button">
                        <span class="material-symbols-outlined" style="font-size: 15px;">live_tv</span>
                        <span>Check VAR</span>
                        <span class="fa-var-badge">1 left</span>
                    </button>
                </div>
                ` : ''}
            </div>
        `;

        backdrop.appendChild(card);
        document.body.appendChild(backdrop);

        let dismissTimer = null;
        const dismissDelay = canShowVar ? 5500 : 1500;

        function dismiss() {
            if (!backdrop.parentNode) return;
            backdrop.style.opacity = '0';
            backdrop.style.transform = 'translate(-50%, -20px)';
            backdrop.style.transition = 'opacity 0.25s cubic-bezier(0.4, 0, 1, 1), transform 0.25s cubic-bezier(0.4, 0, 1, 1)';
            setTimeout(() => { if (backdrop.parentNode) backdrop.remove(); }, 250);
        }

        dismissTimer = setTimeout(dismiss, dismissDelay);

        if (canShowVar) {
            const varBtn = card.querySelector('#fa-feedback-var-btn');
            if (varBtn) {
                varBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    clearTimeout(dismissTimer);
                    backdrop.remove();
                    startVarReview(opts);
                });
            }
        }
    }

    /**
     * Triggers the full VAR Review Modal and dispatches Groq Llama 3.3 verification via Google Apps Script.
     * @param {object} opts
     */
    function startVarReview(opts) {
        const meta = getActiveGameMetadata();
        const gameId = opts.gameId || meta.gameId;
        const puzzleNum = opts.puzzleNum !== undefined ? opts.puzzleNum : meta.puzzleNum;
        const normGuess = normalizeStr(opts.guess || '');

        if (!opts.guess) return;

        if (varState.checkedPlayers.has(normGuess)) {
            toast(`"${opts.guess}" was already reviewed by VAR!`, 'info');
            return;
        }

        if (varState.tokens <= 0 || varState.successfulUses >= varState.maxSuccess) {
            toast('No VAR checks remaining for this match!', 'error');
            return;
        }

        // Consume token while review is in flight
        varState.tokens = 0;
        // Mark this player as reviewed for this match (strictly 1 time per player per game)
        varState.checkedPlayers.add(normGuess);

        // Build Loading Modal DOM
        const modalBackdrop = document.createElement('div');
        modalBackdrop.className = 'fa-var-modal-backdrop';

        const modalCard = document.createElement('div');
        modalCard.className = 'fa-var-modal-card';

        modalCard.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span class="material-symbols-outlined" style="color: #39ff14; font-size: 20px;">live_tv</span>
                    <span style="font-family: 'Space Grotesk', monospace; font-size: 0.75rem; font-weight: 700; color: #39ff14; letter-spacing: 0.08em; text-transform: uppercase;">
                        OFFICIAL VAR REVIEW
                    </span>
                </div>
                <span class="fa-var-badge">1 in review</span>
            </div>

            <div style="margin-bottom: 14px;">
                <h3 style="font-family: 'Anton', Impact, sans-serif; font-size: 1.5rem; text-transform: uppercase; letter-spacing: 0.03em; margin: 0; line-height: 1.1; color: #ffffff;" id="var-modal-title">
                    VAR CHECK IN PROGRESS
                </h3>
                <p style="margin: 4px 0 0 0; font-size: 0.82rem; color: #a3a3a3;">
                    Appealing: <strong style="color: #ffffff;">${opts.guess}</strong>
                </p>
            </div>

            <!-- TV Monitor Frame -->
            <div class="fa-var-monitor" id="var-monitor">
                <div class="fa-var-scanlines"></div>
                <div class="fa-var-rec-badge">
                    <span class="fa-var-rec-dot"></span>
                    <span>VAR ROOM / LIVE</span>
                </div>
                <img class="fa-var-gif" id="var-gif-img" src="" alt="VAR Replay" style="display: none;" />
                <div id="var-gif-spinner" style="display: flex; flex-direction: column; align-items: center; gap: 8px; color: #666;">
                    <span class="material-symbols-outlined text-3xl animate-spin" style="color: #39ff14;">rotate_right</span>
                    <span style="font-size: 0.7rem; font-family: 'Space Grotesk', monospace; letter-spacing: 0.05em; color: #888;">LOADING REPLAY...</span>
                </div>
            </div>

            <!-- Animated Scanline Pulse Bar -->
            <div class="fa-var-pulse-bar" id="var-pulse-bar">
                <div class="fa-var-pulse-bar-fill"></div>
            </div>

            <!-- Status Box / Result Explanation -->
            <div id="var-status-box" style="text-align: center; margin-top: 8px;">
                <p id="var-status-text" style="margin: 0; font-size: 0.8rem; font-weight: 600; color: #a3a3a3; font-family: 'Space Grotesk', monospace; letter-spacing: 0.04em;">
                    CONNECTING TO MATCH OFFICIALS...
                </p>
            </div>

            <!-- Action Button -->
            <div id="var-action-container" style="display: none; margin-top: 16px; text-align: center;">
                <button id="var-dismiss-btn" style="width: 100%; padding: 12px; border-radius: 10px; font-weight: 700; font-family: 'Space Grotesk', sans-serif; text-transform: uppercase; letter-spacing: 0.05em; cursor: pointer; transition: all 0.2s;">
                    CONTINUE MATCH
                </button>
            </div>
        `;

        modalBackdrop.appendChild(modalCard);
        document.body.appendChild(modalBackdrop);

        // Fetch Giphy GIF using search query 'VAR'
        const gifImg = modalCard.querySelector('#var-gif-img');
        const gifSpinner = modalCard.querySelector('#var-gif-spinner');

        fetchGiphyGif('VAR', (gifUrl) => {
            if (gifUrl && gifImg) {
                gifImg.src = gifUrl;
                gifImg.onload = () => {
                    gifImg.style.display = 'block';
                    if (gifSpinner) gifSpinner.style.display = 'none';
                };
            }
        });

        // Backup fallback GIF if Giphy search is delayed
        setTimeout(() => {
            if (gifSpinner && gifImg && gifImg.style.display === 'none') {
                gifImg.src = 'https://media.giphy.com/media/3o7TKSjRrfIPjeiVyM/giphy.gif';
                gifImg.style.display = 'block';
                gifSpinner.style.display = 'none';
            }
        }, 2200);

        // Rotating status messages while checking
        const statusMsgs = [
            'CONNECTING TO MATCH OFFICIALS...',
            'ANALYZING MULTI-ANGLE REPLAY...',
            'REVIEWING OFFICIAL COMPETITION ARCHIVE...',
            'DECISION PENDING...'
        ];
        let msgIndex = 0;
        const msgInterval = setInterval(() => {
            msgIndex = (msgIndex + 1) % statusMsgs.length;
            const sEl = modalCard.querySelector('#var-status-text');
            if (sEl && !sEl.dataset.done) {
                sEl.textContent = statusMsgs[msgIndex];
            }
        }, 800);

        // Prepare payload for backend
        const payload = {
            type: 'var_check',
            gameId: gameId,
            puzzleNum: puzzleNum,
            theme: opts.theme || '',
            guess: opts.guess,
            context: opts.context || '',
            visitorId: getVisitorId(),
            sessionId: getSessionId(),
            url: window.location.href
        };

        trackEvent('var_appeal', {
            gameId: gameId,
            puzzleNum: puzzleNum,
            guess: opts.guess,
            extraDetails: `theme: ${opts.theme || ''} | context: ${opts.context || ''}`
        });

        const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
        const timeoutId = setTimeout(() => {
            if (controller) controller.abort();
        }, 35000);

        fetch(FEEDBACK_WEBHOOK_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'text/plain;charset=utf-8'
            },
            body: JSON.stringify(payload),
            signal: controller ? controller.signal : undefined
        })
        .then(res => {
            clearTimeout(timeoutId);
            return res.text();
        })
        .then(text => {
            clearInterval(msgInterval);
            let data;
            try {
                data = JSON.parse(text);
            } catch (jsonErr) {
                console.warn('[FootyUI] VAR returned non-JSON response:', text);
                data = {
                    accepted: false,
                    isError: true,
                    reason: 'VAR service returned an invalid response. Token restored for retry.'
                };
            }
            trackEvent('var_decision', {
                gameId: gameId,
                puzzleNum: puzzleNum,
                guess: opts.guess,
                isCorrect: data.accepted === true,
                extraDetails: `accepted: ${data.accepted} | reason: ${data.reason || ''} | stat: ${data.stat || ''}`
            });
            renderDecision(data);
        })
        .catch(err => {
            clearTimeout(timeoutId);
            console.error('[FootyUI] VAR check request failed:', err);
            clearInterval(msgInterval);
            const isTimeout = err && err.name === 'AbortError';
            trackEvent('var_decision', {
                gameId: gameId,
                puzzleNum: puzzleNum,
                guess: opts.guess,
                isCorrect: false,
                extraDetails: isTimeout ? 'error: timeout' : 'error: unable to reach VAR review server'
            });
            renderDecision({
                accepted: false,
                isError: true,
                reason: isTimeout
                    ? 'VAR review server timed out. Token restored for retry.'
                    : 'Unable to reach VAR review server. Please check connection. Token restored.'
            });
        });

        function renderDecision(result) {
            const titleEl = modalCard.querySelector('#var-modal-title');
            const statusTextEl = modalCard.querySelector('#var-status-text');
            const pulseBar = modalCard.querySelector('#var-pulse-bar');
            const actionCont = modalCard.querySelector('#var-action-container');
            const dismissBtn = modalCard.querySelector('#var-dismiss-btn');

            if (statusTextEl) statusTextEl.dataset.done = 'true';
            if (pulseBar) pulseBar.style.display = 'none';

            if (result.accepted) {
                modalCard.classList.add('accepted');
                if (titleEl) {
                    titleEl.innerHTML = 'DECISION OVERRULED! ⚽';
                    titleEl.style.color = '#39ff14';
                }

                // If correct, refund the token (up to max 3 successful uses)
                varState.successfulUses++;
                if (varState.successfulUses < varState.maxSuccess) {
                    varState.tokens = 1; // REFUND TOKEN!
                } else {
                    varState.tokens = 0; // Reached max 3 successful appeals
                }

                const remainingCap = varState.maxSuccess - varState.successfulUses;
                const tokenStatusNote = varState.tokens > 0 
                    ? `✓ TOKEN REFUNDED (1 VAR AVAILABLE • ${varState.successfulUses}/${varState.maxSuccess} USED)`
                    : `✓ MAX 3 VAR REVIEWS REACHED (0 LEFT)`;

                if (statusTextEl) {
                    statusTextEl.innerHTML = `
                        <div style="background: rgba(57, 255, 20, 0.12); border: 1px solid rgba(57, 255, 20, 0.35); border-radius: 10px; padding: 12px; margin-top: 8px; text-align: left;">
                            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 6px;">
                                <span class="material-symbols-outlined text-sm" style="color: #39ff14;">check_circle</span>
                                <span style="color: #39ff14; font-weight: 700; font-size: 0.75rem; text-transform: uppercase;">APPEAL UPHELD — DECISION OVERRULED</span>
                            </div>
                            <p style="margin: 0 0 6px 0; color: #e5e2e1; font-size: 0.82rem; line-height: 1.4; font-family: system-ui, sans-serif;">
                                ${result.reason || 'Criteria met according to official records.'}
                            </p>
                            <div style="font-family: 'Space Grotesk', monospace; font-size: 0.68rem; font-weight: 700; color: #39ff14; letter-spacing: 0.05em; text-transform: uppercase;">
                                ${tokenStatusNote}
                            </div>
                        </div>
                    `;
                }

                if (dismissBtn) {
                    dismissBtn.textContent = 'CONTINUE MATCH';
                    dismissBtn.style.background = '#39ff14';
                    dismissBtn.style.color = '#000000';
                    dismissBtn.style.border = 'none';
                    dismissBtn.style.boxShadow = '0 0 15px rgba(57, 255, 20, 0.35)';
                }

                if (opts.onVarAccepted) opts.onVarAccepted(result);

            } else if (result.isError) {
                modalCard.classList.add('rejected');
                // Technical error — refund token and unmark player so they can retry
                varState.tokens = 1;
                varState.checkedPlayers.delete(normGuess);

                if (titleEl) {
                    titleEl.innerHTML = 'VAR UNAVAILABLE ⚠️';
                    titleEl.style.color = '#ffcc00';
                }

                if (statusTextEl) {
                    statusTextEl.innerHTML = `
                        <div style="background: rgba(255, 204, 0, 0.1); border: 1px solid rgba(255, 204, 0, 0.3); border-radius: 10px; padding: 12px; margin-top: 8px; text-align: left;">
                            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 6px;">
                                <span class="material-symbols-outlined text-sm" style="color: #ffcc00;">warning</span>
                                <span style="color: #ffcc00; font-weight: 700; font-size: 0.75rem; text-transform: uppercase;">TECHNICAL ERROR — TOKEN RESTORED</span>
                            </div>
                            <p style="margin: 0 0 6px 0; color: #e5e2e1; font-size: 0.82rem; line-height: 1.4; font-family: system-ui, sans-serif;">
                                ${result.reason || 'VAR review service temporary issue.'}
                            </p>
                            <div style="font-family: 'Space Grotesk', monospace; font-size: 0.68rem; font-weight: 700; color: #ffcc00; letter-spacing: 0.05em; text-transform: uppercase;">
                                ✓ 1 VAR TOKEN PRESERVED FOR RETRY
                            </div>
                        </div>
                    `;
                }

                if (dismissBtn) {
                    dismissBtn.textContent = 'CLOSE';
                    dismissBtn.style.background = '#222';
                    dismissBtn.style.color = '#fff';
                    dismissBtn.style.border = '1px solid rgba(255,255,255,0.15)';
                }

            } else {
                modalCard.classList.add('rejected');
                // If incorrect, DO NOT refund token!
                varState.tokens = 0;

                if (titleEl) {
                    titleEl.innerHTML = 'DECISION STANDS ❌';
                    titleEl.style.color = '#ff4d4d';
                }

                if (statusTextEl) {
                    statusTextEl.innerHTML = `
                        <div style="background: rgba(255, 77, 77, 0.1); border: 1px solid rgba(255, 77, 77, 0.3); border-radius: 10px; padding: 14px; margin-top: 8px; text-align: left;">
                            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 6px;">
                                <span class="material-symbols-outlined text-sm" style="color: #ff4d4d;">cancel</span>
                                <span style="color: #ff4d4d; font-weight: 700; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">VAR CHALLENGE FAILED</span>
                            </div>
                            <p style="margin: 0; color: #e5e2e1; font-size: 0.88rem; line-height: 1.4; font-family: system-ui, sans-serif;">
                                The VAR challenge failed and the decision stands.
                            </p>
                        </div>
                    `;
                }

                if (dismissBtn) {
                    dismissBtn.textContent = 'CLOSE';
                    dismissBtn.style.background = '#222';
                    dismissBtn.style.color = '#fff';
                    dismissBtn.style.border = '1px solid rgba(255,255,255,0.15)';
                }

                if (opts.onVarRejected) opts.onVarRejected(result);
            }

            if (actionCont) actionCont.style.display = 'block';
            if (dismissBtn) {
                dismissBtn.onclick = () => {
                    modalBackdrop.style.opacity = '0';
                    modalBackdrop.style.transition = 'opacity 0.2s ease-out';
                    setTimeout(() => modalBackdrop.remove(), 200);
                };
            }
        }
    }


    // ────────────────────────────────────────────────────────
    // 5. FootyStorage — Namespaced localStorage per game
    // ────────────────────────────────────────────────────────
    /**
     * @param {string} gameId — e.g. "top_transfers"
     */
    function FootyStorage(gameId) {
        const KEY = `footy_v2_${gameId}`;

        const defaults = {
            played: 0,
            won: 0,
            streak: 0,
            bestStreak: 0,
            lastPlayedDate: null,
            lastPuzzleNum: null,
            history: {}   // puzzleNum → { won, score, maxScore }
        };

        function load() {
            try {
                const raw = localStorage.getItem(KEY);
                if (raw) return Object.assign({}, defaults, JSON.parse(raw));
            } catch (_) { }
            return Object.assign({}, defaults);
        }

        function save(data) {
            try { localStorage.setItem(KEY, JSON.stringify(data)); } catch (_) { }
        }

        /** Returns today's ISO date string "YYYY-MM-DD" */
        function todayStr() {
            return new Date().toISOString().slice(0, 10);
        }

        /** Returns true if the user has already completed today's puzzle */
        this.hasPlayedToday = () => {
            const d = load();
            if (d.lastPlayedDate === todayStr()) return true;
            const today = todayStr();
            for (const k in (d.history || {})) {
                if (d.history[k] && d.history[k].date === today) {
                    return true;
                }
            }
            return false;
        };

        /** Returns today's completed result if present */
        this.getTodayResult = () => {
            const d = load();
            const today = todayStr();
            if (d.lastPlayedDate === today && d.lastPuzzleNum !== null) {
                const res = d.history[String(d.lastPuzzleNum)];
                if (res) return res;
            }
            for (const k in (d.history || {})) {
                if (d.history[k] && d.history[k].date === today) {
                    return d.history[k];
                }
            }
            return null;
        };

        /** Returns true if this specific puzzleNum is already in history */
        this.hasPlayedPuzzle = (puzzleNum, isBackInTime = false) => {
            const d = load();
            const histKey = isBackInTime ? `bit_${puzzleNum}` : String(puzzleNum);
            const res = d.history[histKey];
            if (!res) return false;
            // Strict date verification: today's puzzle is only already played if recorded today
            if (!isBackInTime && res.date !== todayStr()) {
                return false;
            }
            return true;
        };

        /** Get stored puzzle result or null */
        this.getPuzzleResult = (puzzleNum, isBackInTime = false) => {
            const d = load();
            const histKey = isBackInTime ? `bit_${puzzleNum}` : String(puzzleNum);
            const res = d.history[histKey] || null;
            // Strict date verification: ignore stale results from previous calendar dates or missing dates
            if (res && !isBackInTime && res.date !== todayStr()) {
                return null;
            }
            return res;
        };

        /** Reset a specific puzzle from history (e.g. for replay / practice mode or recovering corrupt state) */
        this.resetPuzzle = (puzzleNum, isBackInTime = false) => {
            const d = load();
            const histKey = isBackInTime ? `bit_${puzzleNum}` : String(puzzleNum);
            if (d.history[histKey]) {
                delete d.history[histKey];
                if (!isBackInTime && String(d.lastPuzzleNum) === String(puzzleNum)) {
                    d.lastPlayedDate = null;
                    d.lastPuzzleNum = null;
                }
                save(d);
            }
            return d;
        };

        /** Clear any mid-game in-progress state */
        this.clearInProgress = () => {
            try {
                const inprogressKey = `footy_v2_${gameId}_inprogress`;
                localStorage.removeItem(inprogressKey);
            } catch (_) {}
        };

        /** Save mid-game in-progress state (today's puzzle only, not back-in-time) */
        this.saveInProgress = (puzzleNum, state, isBackInTime = false) => {
            if (isBackInTime) return;
            if (this.hasPlayedPuzzle(puzzleNum, false)) return;
            try {
                const inprogressKey = `footy_v2_${gameId}_inprogress`;
                const payload = {
                    puzzleNum: Number(puzzleNum),
                    date: todayStr(),
                    state: state
                };
                localStorage.setItem(inprogressKey, JSON.stringify(payload));
            } catch (_) {}
        };

        /** Retrieve in-progress state for current puzzle, discarding if stale/mismatched */
        this.getInProgress = (puzzleNum, isBackInTime = false) => {
            if (isBackInTime) return null;
            if (this.hasPlayedPuzzle(puzzleNum, false)) return null;
            try {
                const inprogressKey = `footy_v2_${gameId}_inprogress`;
                const raw = localStorage.getItem(inprogressKey);
                if (!raw) return null;
                const data = JSON.parse(raw);
                if (!data || data.date !== todayStr() || Number(data.puzzleNum) !== Number(puzzleNum)) {
                    // Stale or different day / different puzzle -> clean up to prevent spoilers
                    this.clearInProgress();
                    return null;
                }
                return data.state || null;
            } catch (_) {
                return null;
            }
        };

        /** Record a completed game result */
        this.recordResult = (puzzleNum, won, score, maxScore, isBackInTime = false, outcome = null) => {
            this.clearInProgress();
            const d = load();
            const histKey = isBackInTime ? `bit_${puzzleNum}` : String(puzzleNum);
            const existing = d.history[histKey];
            if (existing && (isBackInTime || existing.date === todayStr())) {
                return d;
            }
            const resolvedOutcome = outcome || (won ? 'win' : 'loss');
            const isPartial = resolvedOutcome === 'partial';

            if (!isBackInTime) {
                d.played++;
                if (won) {
                    d.won++;
                    d.streak++;
                } else if (isPartial) {
                    // Partial success preserves streak without resetting to 0 (hard-fought draw / survival)
                } else {
                    d.streak = 0;
                }
                d.bestStreak = Math.max(d.bestStreak, d.streak);
                d.lastPlayedDate = todayStr();
                d.lastPuzzleNum = puzzleNum;
            }
            // Always record in history (even back-in-time, separately keyed)
            d.history[histKey] = { won, outcome: resolvedOutcome, score, maxScore, date: todayStr() };
            save(d);
            return d;
        };

        /** Get full stats object */
        this.getStats = () => load();

        /** Get streak from stored data */
        this.getStreak = () => load().streak;

        /** Get best streak */
        this.getBestStreak = () => load().bestStreak;
    }


    // ────────────────────────────────────────────────────────
    // 6. FootyWrongGuesses — Wrong guess badge renderer
    // ────────────────────────────────────────────────────────
    /**
     * @param {string} sectionId   — ID of the wrapper section (hidden by default)
     * @param {string} containerId — ID of the flex container for badges
     */
    function FootyWrongGuesses(sectionId, containerId) {
        let section = document.getElementById(sectionId);
        let container = document.getElementById(containerId);

        // Auto-correct if arguments were passed in reverse
        if (section && typeof sectionId === 'string' && sectionId.includes('container') && typeof containerId === 'string' && containerId.includes('section')) {
            const tmp = section; section = container; container = tmp;
        }

        const shown = new Set();

        this.has = (text) => {
            if (!text) return false;
            return shown.has(FootyUI.normalizeStr(text));
        };

        this.getAll = () => Array.from(shown);

        this.restore = (list) => {
            if (Array.isArray(list)) {
                list.forEach(item => {
                    if (item) this.add(item);
                });
            }
        };

        this.add = (text) => {
            const norm = FootyUI.normalizeStr(text);
            if (shown.has(norm)) return;
            shown.add(norm);

            section?.classList.remove('hidden');
            const badge = document.createElement('span');
            badge.className = 'fa-wrong-badge';
            badge.textContent = text;
            container?.appendChild(badge);
        };

        this.delete = (text) => {
            if (!text) return;
            const norm = FootyUI.normalizeStr(text);
            if (!shown.has(norm)) return;
            shown.delete(norm);

            if (container) {
                const badges = container.querySelectorAll('.fa-wrong-badge');
                badges.forEach(b => {
                    if (FootyUI.normalizeStr(b.textContent) === norm) {
                        b.remove();
                    }
                });
            }
            if (shown.size === 0 && section) {
                section.classList.add('hidden');
            }
        };
        this.remove = this.delete;

        this.clear = () => {
            shown.clear();
            if (container) container.innerHTML = '';
            section?.classList.add('hidden');
        };
    }


    // ────────────────────────────────────────────────────────
    // 7. buildBackInTimeLinks — Generate back-in-time hrefs
    // ────────────────────────────────────────────────────────
    /**
     * Generates link objects for the modal's "play past puzzles" section.
     * @param {string} gameId    — e.g. "top_transfers"
     * @param {number} maxDays   — how many past days to offer (default 7)
     * @param {FootyStorage} storage
     * @param {number} [currentPuzzleNum] — current puzzle number
     * @returns {Array<{label, href}>}
     */
    function buildBackInTimeLinks(gameId, maxDays, storage, currentPuzzleNum) {
        maxDays = maxDays || 7;
        const isEs = (typeof FootyI18n !== 'undefined' && FootyI18n.getLang() === 'es');
        const enLabels = ['Yesterday', '2 days ago', '3 days ago', '4 days ago',
            '5 days ago', '6 days ago', '7 days ago',
            '8 days ago', '9 days ago', '10 days ago'];
        const esLabels = ['Ayer', 'Hace 2 días', 'Hace 3 días', 'Hace 4 días',
            'Hace 5 días', 'Hace 6 días', 'Hace 7 días',
            'Hace 8 días', 'Hace 9 días', 'Hace 10 días'];
        const labels = isEs ? esLabels : enLabels;

        const links = [];
        for (let d = 1; d <= maxDays; d++) {
            if (typeof currentPuzzleNum === 'number' && (currentPuzzleNum - d) < 1) {
                break;
            }
            const label = labels[d - 1] || (isEs ? `Hace ${d} días` : `${d} days ago`);
            links.push({
                label,
                href: `${gameId}_d${d}.html`
            });
        }
        return links;
    }


    // ────────────────────────────────────────────────────────
    // 8. initAccentColor — Set CSS custom properties from hex
    // ────────────────────────────────────────────────────────
    /**
     * Called once per game to wire up the --fa-accent-rgb CSS var
     * so shared components (dropdown hover, badges, etc.) use the
     * game's own accent color without hardcoding it in footy-ui.css.
     * @param {string} hex — e.g. "#39ff14" or "#00f0ff"
     */
    function initAccentColor(hex) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        document.documentElement.style.setProperty('--fa-accent-rgb', `${r},${g},${b}`);
        document.documentElement.style.setProperty('--fa-accent-glow', `rgba(${r},${g},${b},0.25)`);
    }


    // ────────────────────────────────────────────────────────
    // 9. Utility helpers
    // ────────────────────────────────────────────────────────
    function formatFee(val, transferType) {
        const isEs = (typeof FootyI18n !== 'undefined' && FootyI18n.getLang() === 'es');
        const fee = parseFloat(val);
        const typeStr = (transferType || '').toString().trim().toLowerCase();

        if (!isNaN(fee) && fee > 0) {
            const formatted = fee >= 1000000 ? `€${(fee / 1000000).toFixed(1)}M` : (fee >= 1000 ? `€${(fee / 1000).toFixed(0)}K` : `€${fee}`);
            if (typeStr === 'loan') {
                return isEs ? `${formatted} (Cesión)` : `${formatted} (Loan)`;
            }
            return formatted;
        }

        if (typeStr === 'loan') {
            return isEs ? 'Cesión' : 'Loan';
        }
        if (typeStr === 'return from loan' || typeStr === 'loan return') {
            return isEs ? 'Fin de Cesión' : 'Loan Return';
        }
        if (typeStr === 'transfer' || typeStr === 'free' || typeStr === 'free transfer') {
            return isEs ? 'Traspaso Libre' : 'Free Transfer';
        }
        if (typeStr === 'draft') {
            return isEs ? 'Draft' : 'Draft';
        }

        return isEs ? 'Libre / Cesión' : 'Free / Loan';
    }

    function todayStr() {
        return new Date().toISOString().slice(0, 10);
    }


    // ────────────────────────────────────────────────────────
    // ────────────────────────────────────────────────────────
    // 10. Auto-initialize Analytics, Error Tracking & Cookie Consent Banner
    // ────────────────────────────────────────────────────────
    function initAnalyticsAndConsent() {
        const gaMeta = document.querySelector('meta[name="google-analytics-id"]');
        const gaId = gaMeta ? gaMeta.getAttribute('content') : null;
        if (!gaId || gaId.startsWith('G-XXX')) {
            return;
        }

        const consent = localStorage.getItem('footy_consent');
        if (consent === 'accepted') {
            loadGA4(gaId);
        } else if (consent === 'declined') {
            console.log('[FootyUI] Analytics cookies declined by user.');
        } else {
            showConsentBanner(gaId);
        }
    }

    function loadGA4(gaId) {
        // Inject Google Tag Manager script
        const script = document.createElement('script');
        script.async = true;
        script.src = `https://www.googletagmanager.com/gtag/js?id=${gaId}`;
        document.head.appendChild(script);

        window.dataLayer = window.dataLayer || [];
        window.gtag = function () { dataLayer.push(arguments); };
        window.gtag('js', new Date());
        window.gtag('config', gaId);

        // Error tracking catcher
        window.addEventListener('error', function (event) {
            if (window.gtag) {
                window.gtag('event', 'exception', {
                    'description': event.message + ' at ' + event.filename + ':' + event.lineno,
                    'fatal': true
                });
            }
        });

        window.addEventListener('unhandledrejection', function (event) {
            if (window.gtag) {
                window.gtag('event', 'exception', {
                    'description': 'Unhandled Promise: ' + (event.reason ? event.reason.message || event.reason : 'unknown'),
                    'fatal': false
                });
            }
        });
    }

    function showConsentBanner(gaId) {
        const banner = document.createElement('div');
        banner.className = 'fa-consent-banner';

        // Account for relative path based on location
        const isGame = window.location.pathname.includes('/games/');
        const privacyPath = isGame ? '../privacy.html' : 'privacy.html';
        const termsPath = isGame ? '../terms.html' : 'terms.html';
        const isEs = (typeof FootyI18n !== 'undefined' && FootyI18n.getLang() === 'es');

        const title = isEs ? 'Uso de Cookies' : 'Cookie Consent';
        const bodyText = isEs
            ? `Utilizamos cookies para analizar el tráfico, registrar errores y mejorar tu experiencia de juego. Al pulsar "ACEPTAR TODO", aceptas nuestra <a href="${privacyPath}" class="text-accent underline hover:brightness-110">Política de Privacidad</a> y nuestros <a href="${termsPath}" class="text-accent underline hover:brightness-110">Términos y Condiciones</a>.`
            : `We use cookies to analyze traffic, track errors, and improve your trivia experience. By clicking "ACCEPT ALL", you agree to our <a href="${privacyPath}" class="text-accent underline hover:brightness-110">Privacy Policy</a> and <a href="${termsPath}" class="text-accent underline hover:brightness-110">Terms & Conditions</a>.`;
        const declineText = isEs ? 'RECHAZAR' : 'DECLINE';
        const acceptText = isEs ? 'ACEPTAR TODO' : 'ACCEPT ALL';

        banner.innerHTML = `
            <div class="fa-consent-content">
                <span class="material-symbols-outlined text-accent text-2xl shrink-0">cookie</span>
                <div class="space-y-1 text-left flex-grow">
                    <h5 class="font-title text-sm font-bold text-white uppercase tracking-wider">${title}</h5>
                    <p class="text-on-surface-variant text-xs leading-relaxed max-w-lg">
                        ${bodyText}
                    </p>
                </div>
                <div class="flex gap-2 shrink-0 w-full sm:w-auto justify-end">
                    <button id="fa-consent-decline" class="px-4 py-2 bg-surface border border-white/10 text-on-surface-variant hover:text-white rounded-xl text-xs font-bold uppercase tracking-wider transition-all">
                        ${declineText}
                    </button>
                    <button id="fa-consent-accept" class="px-4 py-2 bg-accent text-black hover:brightness-110 active:scale-95 rounded-xl text-xs font-bold uppercase tracking-wider transition-all">
                        ${acceptText}
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(banner);

        document.getElementById('fa-consent-accept').addEventListener('click', () => {
            localStorage.setItem('footy_consent', 'accepted');
            banner.remove();
            loadGA4(gaId);
        });

        document.getElementById('fa-consent-decline').addEventListener('click', () => {
            localStorage.setItem('footy_consent', 'declined');
            banner.remove();
        });
    }

    // ── Visitor & Session Identification ─────────────────────
    function getVisitorId() {
        let vid = localStorage.getItem('footy_visitor_id');
        if (!vid) {
            vid = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : 'v_' + Math.random().toString(36).substring(2, 11) + Date.now().toString(36);
            try { localStorage.setItem('footy_visitor_id', vid); } catch (_) {}
        }
        return vid;
    }

    function getSessionId() {
        let sid = sessionStorage.getItem('footy_session_id');
        if (!sid) {
            sid = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : 's_' + Math.random().toString(36).substring(2, 11) + Date.now().toString(36);
            try { sessionStorage.setItem('footy_session_id', sid); } catch (_) {}
        }
        return sid;
    }

    // ── Feedback System ──────────────────────────────────────
    function getActiveGameMetadata() {
        const path = window.location.pathname;
        const gameIdMatch = path.match(/\/games\/([a-zA-Z0-9_-]+?)(?:_d\d+)?\.html/);
        const gameId = gameIdMatch ? gameIdMatch[1] : 'lobby';
        const isBackInTime = /_d\d+\.html$/.test(path);
        
        let puzzleNum = 0;
        const badgeEl = document.getElementById('puzzle-badge');
        if (badgeEl) {
            const badgeText = badgeEl.textContent || '';
            const numMatch = badgeText.match(/#(\d+)/);
            if (numMatch) {
                puzzleNum = parseInt(numMatch[1], 10);
            }
        }
        return { gameId, isBackInTime, puzzleNum };
    }

    function trackEvent(eventName, params = {}) {
        if (!FEEDBACK_WEBHOOK_URL || FEEDBACK_WEBHOOK_URL.includes('XXXX')) {
            return;
        }

        if (typeof window !== 'undefined' && window.location) {
            const host = window.location.hostname;
            const path = window.location.pathname;

            // Only track production events from the official domain
            if (host !== 'playmaker.best' && host !== 'www.playmaker.best') {
                return;
            }

            // Never track template files or invalid paths
            if (path.includes('/templates/') || path.endsWith('_template.html')) {
                return;
            }
        }

        const meta = getActiveGameMetadata();
        const urlSource = params.urlSource || params.source || getUrlSource();

        let extraDetails = params.extraDetails || '';
        if (urlSource && !extraDetails.includes('source:')) {
            extraDetails = extraDetails ? `${extraDetails} | source: ${urlSource}` : `source: ${urlSource}`;
        }
        if (params.method && !extraDetails.includes('method:')) {
            extraDetails = extraDetails ? `${extraDetails} | method: ${params.method}` : `method: ${params.method}`;
        }

        const payload = {
            type: 'event',
            eventName: eventName,
            visitorId: getVisitorId(),
            sessionId: getSessionId(),
            gameId: params.gameId || meta.gameId,
            puzzleNum: params.puzzleNum !== undefined ? params.puzzleNum : meta.puzzleNum,
            score: params.score,
            maxScore: params.maxScore,
            lives: params.lives !== undefined ? params.lives : params.livesLeft,
            won: params.won,
            isCorrect: params.isCorrect !== undefined ? params.isCorrect : (params.correct !== undefined ? params.correct : undefined),
            guess: params.guess !== undefined ? params.guess : undefined,
            step: params.step !== undefined ? params.step : (params.slot !== undefined ? params.slot : undefined),
            target: params.target !== undefined ? params.target : undefined,
            isBackInTime: params.isBackInTime !== undefined ? params.isBackInTime : meta.isBackInTime,
            extraDetails: extraDetails,
            url: window.location.href,
            urlSource: urlSource,
            source: urlSource,
            method: params.method || '',
            shareUrl: params.shareUrl || '',
            timestamp: new Date().toISOString()
        };

        fetch(FEEDBACK_WEBHOOK_URL, {
            method: 'POST',
            mode: 'no-cors',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        }).catch(err => {
            console.error('[FootyUI] Event tracking error:', err);
        });
    }

    // ── Global Puzzle Overrides (Real-time Cloud Sync) ───────
    async function syncPuzzleOverrides(gameId, puzzleNum, onApply) {
        if (!gameId || !puzzleNum || !FEEDBACK_WEBHOOK_URL) return;

        const cacheKey = `fa_overrides_${gameId}_${puzzleNum}`;
        const cacheTimeKey = `fa_overrides_time_${gameId}_${puzzleNum}`;
        const now = Date.now();

        // 1. Check local cache (valid for 15 minutes)
        try {
            const cached = localStorage.getItem(cacheKey);
            const cachedTime = parseInt(localStorage.getItem(cacheTimeKey) || '0', 10);
            if (cached && (now - cachedTime < 15 * 60 * 1000)) {
                const parsed = JSON.parse(cached);
                if (Array.isArray(parsed) && parsed.length > 0 && typeof onApply === 'function') {
                    onApply(parsed);
                }
            }
        } catch (e) {}

        // 2. Fetch fresh overrides from Apps Script backend
        try {
            const url = `${FEEDBACK_WEBHOOK_URL}?action=get_overrides&gameId=${encodeURIComponent(gameId)}&puzzleNum=${encodeURIComponent(puzzleNum)}`;
            const res = await fetch(url);
            if (res.ok) {
                const data = await res.json();
                if (data.status === 'success' && Array.isArray(data.overrides)) {
                    localStorage.setItem(cacheKey, JSON.stringify(data.overrides));
                    localStorage.setItem(cacheTimeKey, now.toString());
                    if (data.overrides.length > 0 && typeof onApply === 'function') {
                        onApply(data.overrides);
                    }
                }
            }
        } catch (err) {
            // Non-blocking background sync
            console.debug('[FootyUI] Cloud overrides sync error:', err);
        }
    }

    function initFeedbackSystem() {
        const isEs = (typeof FootyI18n !== 'undefined' && FootyI18n.getLang() === 'es');
        // Create floating button
        const trigger = document.createElement('button');
        trigger.className = 'fa-feedback-trigger';
        trigger.id = 'fa-feedback-btn';
        trigger.innerHTML = `
            <span class="material-symbols-outlined" style="font-size: 18px">rate_review</span>
            <span>${isEs ? 'Comentarios' : 'Feedback'}</span>
        `;
        document.body.appendChild(trigger);

        // Create modal
        const modal = document.createElement('div');
        modal.className = 'fa-feedback-modal-backdrop hidden';
        modal.id = 'fa-feedback-modal';
        modal.innerHTML = `
            <div class="fa-feedback-modal-card">
                <button id="fa-feedback-close" class="absolute top-4 right-4 text-on-surface-variant hover:text-white transition-colors" type="button">
                    <span class="material-symbols-outlined text-2xl">close</span>
                </button>
                <h4 class="font-headline text-2xl text-accent uppercase italic tracking-wide mb-2">${isEs ? 'ENVIAR COMENTARIOS' : 'SEND FEEDBACK'}</h4>
                <p class="text-on-surface-variant text-xs mb-4">${isEs ? '¿Tienes una sugerencia o encontraste un error? ¡Cuéntanos!' : 'Have a bug report or a suggestion? Let us know!'}</p>
                
                <form id="fa-feedback-form" class="space-y-4 text-left">
                    <div>
                        <label class="block text-[10px] font-mono uppercase tracking-widest text-on-surface-variant mb-1.5">${isEs ? 'Categoría' : 'Category'}</label>
                        <select id="fa-feedback-category" class="fa-feedback-input" style="color-scheme: dark;" required>
                            <option value="Suggestion">${isEs ? 'Sugerencia' : 'Suggestion'}</option>
                            <option value="Bug Report">${isEs ? 'Reporte de Error' : 'Bug Report'}</option>
                            <option value="Question">${isEs ? 'Pregunta' : 'Question'}</option>
                            <option value="Other">${isEs ? 'Otro' : 'Other'}</option>
                        </select>
                    </div>
                    
                    <div>
                        <label class="block text-[10px] font-mono uppercase tracking-widest text-on-surface-variant mb-1.5">${isEs ? 'Tu Mensaje' : 'Your Message'}</label>
                        <textarea id="fa-feedback-message" rows="4" class="fa-feedback-input" placeholder="${isEs ? '¿Qué te gustaría decirnos?...' : "What's on your mind?..."}" required></textarea>
                    </div>
                    
                    <div>
                        <label class="block text-[10px] font-mono uppercase tracking-widest text-on-surface-variant mb-1.5">${isEs ? 'Correo Electrónico (Opcional)' : 'Email (Optional)'}</label>
                        <input type="email" id="fa-feedback-email" class="fa-feedback-input" placeholder="your@email.com">
                    </div>
                    
                    <div class="pt-2">
                        <button type="submit" id="fa-feedback-submit" class="w-full py-3 bg-accent text-black font-headline text-lg uppercase italic rounded-xl hover:brightness-110 active:scale-95 transition-all flex items-center justify-center gap-2">
                            ${isEs ? 'ENVIAR COMENTARIOS' : 'SUBMIT FEEDBACK'}
                        </button>
                    </div>
                </form>
            </div>
        `;
        document.body.appendChild(modal);

        // Open modal
        trigger.addEventListener('click', () => {
            modal.classList.remove('hidden');
            trackEvent('feedback_open');
        });

        // Close modal
        const closeBtn = modal.querySelector('#fa-feedback-close');
        const closeModal = () => {
            modal.classList.add('hidden');
        };
        closeBtn.addEventListener('click', closeModal);

        // Close on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });

        // Submit form
        const form = modal.querySelector('#fa-feedback-form');
        const submitBtn = modal.querySelector('#fa-feedback-submit');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const host = window.location.hostname;
            const path = window.location.pathname;
            if (host !== 'playmaker.best' && host !== 'www.playmaker.best') {
                toast(isEs ? 'Los comentarios solo se envían en el sitio oficial.' : 'Feedback is only submitted on the live site.', 'info');
                return;
            }
            if (path.includes('/templates/') || path.endsWith('_template.html')) {
                return;
            }

            const category = modal.querySelector('#fa-feedback-category').value;
            const message = modal.querySelector('#fa-feedback-message').value;
            const email = modal.querySelector('#fa-feedback-email').value;

            submitBtn.disabled = true;
            submitBtn.textContent = isEs ? 'ENVIANDO...' : 'SUBMITTING...';

            const payload = {
                type: 'feedback',
                category,
                message,
                email,
                visitorId: getVisitorId(),
                sessionId: getSessionId(),
                url: window.location.href,
                timestamp: new Date().toISOString()
            };

            try {
                if (!FEEDBACK_WEBHOOK_URL || FEEDBACK_WEBHOOK_URL.includes('XXXX')) {
                    throw new Error('Webhook URL not configured');
                }

                await fetch(FEEDBACK_WEBHOOK_URL, {
                    method: 'POST',
                    mode: 'no-cors',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                toast(isEs ? '¡Comentarios enviados! Muchas gracias.' : 'Feedback submitted! Thank you.', 'success');
                trackEvent('feedback_submit', { extraDetails: category });
                modal.querySelector('#fa-feedback-message').value = '';
                modal.querySelector('#fa-feedback-email').value = '';
                closeModal();
            } catch (err) {
                console.error('[FootyUI] Feedback submission error:', err);
                toast(isEs ? 'Error al enviar comentarios. Por favor intenta de nuevo.' : 'Error submitting feedback. Please try again.', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = isEs ? 'ENVIAR COMENTARIOS' : 'SUBMIT FEEDBACK';
            }
        });
    }

    // Auto game start detection
    let gameStarted = false;
    function detectGameStart(e) {
        if (gameStarted) return;
        if (e.target.closest('#fa-guess-panel') || 
            e.target.closest('button[onclick*="reveal"]') || 
            (e.type === 'keydown' && e.target.closest('#guess-input'))) {
            gameStarted = true;
            trackEvent('game_start');
            document.removeEventListener('click', detectGameStart, true);
            document.removeEventListener('keydown', detectGameStart, true);
        }
    }
    document.addEventListener('click', detectGameStart, true);
    document.addEventListener('keydown', detectGameStart, true);

    // Run initialization
    // ────────────────────────────────────────────────────────
    // PWA Service Worker & Install Prompt System
    // ────────────────────────────────────────────────────────
    let deferredInstallPrompt = null;

    function isAppInstalled() {
        if (typeof window === 'undefined') return false;
        return window.matchMedia('(display-mode: standalone)').matches ||
               window.navigator.standalone === true ||
               document.referrer.includes('android-app://');
    }

    function isIOSDevice() {
        if (typeof navigator === 'undefined') return false;
        const ua = navigator.userAgent.toLowerCase();
        return /iphone|ipad|ipod/.test(ua) && !ua.includes('crios') && !ua.includes('fxios');
    }

    function isPWADismissedRecently() {
        try {
            const dismissedAt = localStorage.getItem('playmaker_pwa_dismissed');
            if (!dismissedAt) return false;
            const daysSince = (Date.now() - parseInt(dismissedAt, 10)) / (1000 * 60 * 60 * 24);
            return daysSince < 7; // Cooldown for 7 days
        } catch (e) {
            return false;
        }
    }

    function dismissPWAPrompt() {
        try {
            localStorage.setItem('playmaker_pwa_dismissed', Date.now().toString());
        } catch (e) {}
        const el = document.getElementById('fa-pwa-banner-wrap');
        if (el) el.remove();
        trackEvent('pwa_prompt_dismissed');
    }

    function showIOSInstallSheet() {
        if (document.getElementById('fa-pwa-ios-modal')) return;

        const overlay = document.createElement('div');
        overlay.id = 'fa-pwa-ios-modal';
        overlay.className = 'fa-pwa-ios-modal-overlay';
        overlay.innerHTML = `
            <div class="fa-pwa-ios-sheet">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span class="material-symbols-outlined" style="color:#39ff14; font-size:24px;">install_mobile</span>
                        <h3 style="font-family:'Space Grotesk',system-ui,sans-serif; font-size:1.1rem; font-weight:700; margin:0;">Install Playmaker</h3>
                    </div>
                    <button id="fa-pwa-ios-close" class="fa-pwa-btn-close" aria-label="Close">
                        <span class="material-symbols-outlined">close</span>
                    </button>
                </div>
                <p style="font-size:0.85rem; color:rgba(255,255,255,0.7); margin-bottom:16px;">
                    Install this app on your iPhone or iPad for the best fullscreen arcade experience:
                </p>
                <div class="fa-pwa-ios-step">
                    <span class="fa-pwa-ios-step-num">1</span>
                    <span>Tap the <strong>Share</strong> button <span class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; color:#39ff14;">ios_share</span> in Safari's toolbar</span>
                </div>
                <div class="fa-pwa-ios-step">
                    <span class="fa-pwa-ios-step-num">2</span>
                    <span>Scroll down and tap <strong>Add to Home Screen</strong> <span class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; color:#39ff14;">add_box</span></span>
                </div>
                <button id="fa-pwa-ios-done" class="fa-pwa-btn-install" style="width:100%; justify-content:center; margin-top:16px; padding:12px;">
                    Got It!
                </button>
            </div>
        `;

        document.body.appendChild(overlay);

        const closeBtn = document.getElementById('fa-pwa-ios-close');
        const doneBtn = document.getElementById('fa-pwa-ios-done');
        const closeSheet = () => {
            overlay.remove();
            dismissPWAPrompt();
        };

        if (closeBtn) closeBtn.addEventListener('click', closeSheet);
        if (doneBtn) doneBtn.addEventListener('click', closeSheet);
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeSheet();
        });
    }

    function renderPWABanner() {
        if (isAppInstalled() || isPWADismissedRecently() || document.getElementById('fa-pwa-banner-wrap')) {
            return;
        }

        const isGamesSubdir = window.location.pathname.includes('/games/');
        const iconPath = isGamesSubdir ? '../assets/favicon.png' : 'assets/favicon.png';

        const wrap = document.createElement('div');
        wrap.id = 'fa-pwa-banner-wrap';
        wrap.className = 'fa-pwa-banner-wrap';
        wrap.innerHTML = `
            <div class="fa-pwa-banner">
                <img src="${iconPath}" alt="Playmaker Icon" class="fa-pwa-icon" onerror="this.src='https://playmaker.best/assets/favicon.png'" />
                <div class="fa-pwa-content">
                    <div class="fa-pwa-title">
                        Playmaker <span class="fa-pwa-badge">App</span>
                    </div>
                    <div class="fa-pwa-desc">
                        Install for instant daily quizzes & streak tracking!
                    </div>
                </div>
                <div class="fa-pwa-actions">
                    <button id="fa-pwa-btn-install" class="fa-pwa-btn-install" aria-label="Install App">
                        <span class="material-symbols-outlined" style="font-size:16px;">download</span> Install
                    </button>
                    <button id="fa-pwa-btn-close" class="fa-pwa-btn-close" aria-label="Dismiss banner">
                        <span class="material-symbols-outlined" style="font-size:18px;">close</span>
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(wrap);
        trackEvent('pwa_banner_shown');

        const installBtn = document.getElementById('fa-pwa-btn-install');
        const closeBtn = document.getElementById('fa-pwa-btn-close');

        if (installBtn) {
            installBtn.addEventListener('click', async () => {
                trackEvent('pwa_install_click');
                if (deferredInstallPrompt) {
                    deferredInstallPrompt.prompt();
                    const { outcome } = await deferredInstallPrompt.userChoice;
                    trackEvent('pwa_prompt_outcome', { outcome });
                    if (outcome === 'accepted') {
                        wrap.remove();
                    }
                    deferredInstallPrompt = null;
                } else if (isIOSDevice()) {
                    showIOSInstallSheet();
                } else {
                    // Fallback guidance for desktop / general browsers without prompt
                    toast('Tap your browser settings menu (⋮) and select "Install App" or "Add to Home Screen".');
                    dismissPWAPrompt();
                }
            });
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', dismissPWAPrompt);
        }
    }

    function initPWAInstall() {
        if (typeof window === 'undefined') return;

        // Register Service Worker
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                const swUrl = window.location.pathname.includes('/games/') ? '../sw.js' : './sw.js';
                navigator.serviceWorker.register(swUrl).catch((err) => {
                    console.debug('[FootyUI] SW registration note:', err);
                });
            });
        }

        // Catch native install prompt
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredInstallPrompt = e;
            renderPWABanner();
        });

        // For iOS devices or standalone check
        if (isIOSDevice() && !isAppInstalled() && !isPWADismissedRecently()) {
            // Delay slightly so it does not interfere with initial page rendering
            setTimeout(renderPWABanner, 2500);
        }

        window.addEventListener('appinstalled', () => {
            trackEvent('pwa_installed_success');
            const wrap = document.getElementById('fa-pwa-banner-wrap');
            if (wrap) wrap.remove();
        });
    }

    // ── Language Switcher Integration ────────────────────────
    function initLanguageSwitcher(containerId = 'lang-switcher') {
        if (typeof FootyI18n === 'undefined') return;
        const container = document.getElementById(containerId);
        if (container) {
            const isEs = FootyI18n.getLang() === 'es';
            container.innerHTML = `
                <a href="${FootyI18n.getCounterpartUrl('en')}" onclick="FootyI18n.setLang('en')" class="px-2 py-0.5 rounded transition-all ${!isEs ? 'bg-accent/20 text-accent font-bold shadow-sm' : 'text-on-surface-variant hover:text-white'}" title="Switch to English">EN</a>
                <span class="text-white/20 text-[10px] select-none">|</span>
                <a href="${FootyI18n.getCounterpartUrl('es')}" onclick="FootyI18n.setLang('es')" class="px-2 py-0.5 rounded transition-all ${isEs ? 'bg-accent/20 text-accent font-bold shadow-sm' : 'text-on-surface-variant hover:text-white'}" title="Cambiar a Español">ES</a>
            `;
        }
    }

    // Auto-init on DOM ready
    function initHowToPlay() {
        const htpBtn = document.getElementById('how-to-play-btn');
        const htpModal = document.getElementById('how-to-play-modal');
        if (!htpModal) return;

        const openModal = () => {
            htpModal.classList.remove('hidden');
            trackEvent('how_to_play_open');
        };
        const closeModal = () => {
            htpModal.classList.add('hidden');
        };

        if (htpBtn) {
            htpBtn.addEventListener('click', openModal);
        }

        const closeBtn = document.getElementById('close-how-to-play-btn');
        const closeBtn2 = document.getElementById('close-how-to-play-btn2');
        if (closeBtn) closeBtn.addEventListener('click', closeModal);
        if (closeBtn2) closeBtn2.addEventListener('click', closeModal);

        htpModal.addEventListener('click', (e) => {
            if (e.target === htpModal) closeModal();
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !htpModal.classList.contains('hidden')) {
                closeModal();
            }
        });
    }

    // ────────────────────────────────────────────────────────
    // More Daily Challenges Suggestions Component
    // ────────────────────────────────────────────────────────
    const GAMES_REGISTRY = [
        {
            id: 'top_transfers',
            icon: 'payments',
            color: '#00f0ff',
            nameKey: 'game_top_transfers',
            taglineKey: 'tagline_top_transfers',
            defaultName: 'Top Transfers',
            defaultTagline: 'Guess the record signings',
            file: 'top_transfers.html'
        },
        {
            id: 'transfer_destination',
            icon: 'alt_route',
            color: '#39ff14',
            nameKey: 'game_transfer_destination',
            taglineKey: 'tagline_transfer_destination',
            defaultName: 'Transfer Destination',
            defaultTagline: "Guess a player's career path",
            file: 'transfer_destination.html'
        },
        {
            id: 'top_scorers',
            icon: 'sports_soccer',
            color: '#f59e0b',
            nameKey: 'game_top_scorers',
            taglineKey: 'tagline_top_scorers',
            defaultName: 'Top Scorers',
            defaultTagline: 'Name the top goalscorers',
            file: 'top_scorers.html'
        },
        {
            id: 'club_connect',
            icon: 'hub',
            color: '#e879f9',
            nameKey: 'game_club_connect',
            taglineKey: 'tagline_club_connect',
            defaultName: 'Club Connect',
            defaultTagline: '5 players, 1 club signed them all',
            file: 'club_connect.html'
        },
        {
            id: 'player_chain',
            icon: 'link',
            color: '#38bdf8',
            nameKey: 'game_player_chain',
            taglineKey: 'tagline_player_chain',
            defaultName: 'Player Chain',
            defaultTagline: 'Connect consecutive clubs through shared teammates',
            file: 'player_chain.html'
        },
        {
            id: 'passport_fc',
            icon: 'public',
            color: '#fbbf24',
            nameKey: 'game_passport_fc',
            taglineKey: 'tagline_passport_fc',
            defaultName: 'Passport FC',
            defaultTagline: 'Collect nationality stamps for a mystery club',
            file: 'passport_fc.html'
        }
    ];

    function initGameSuggestions(opts = {}) {
        const container = document.getElementById(opts.containerId || 'fa-game-suggestions');
        if (!container) return;

        const currentGame = opts.currentGame || (typeof container.getAttribute === 'function' ? container.getAttribute('data-current-game') : '') || (typeof window !== 'undefined' ? window.GAME_ID : '') || '';
        const otherGames = GAMES_REGISTRY.filter(g => g.id !== currentGame);

        const isI18n = typeof FootyI18n !== 'undefined';
        const t = (k, fb) => isI18n ? FootyI18n.t(k) : fb;
        const currentLang = isI18n ? FootyI18n.getLang() : 'en';

        const isSpanishPath = typeof window !== 'undefined' && window.location && (
            window.location.pathname.includes('/es/') || currentLang === 'es'
        );

        const homeUrl = isSpanishPath ? '../../es/' : '../index.html';
        const sectionTitle = t('more_daily_challenges', 'MORE DAILY CHALLENGES');
        const solvedText = t('badge_solved', 'SOLVED ✅');
        const backText = t('back_to_playmaker', '← Back to Playmaker');

        let cardsHtml = '';
        otherGames.forEach(game => {
            const gameTitle = t(game.nameKey, game.defaultName);
            const gameTagline = t(game.taglineKey, game.defaultTagline);

            let isSolved = false;
            let isPlayed = false;
            try {
                const storage = new FootyStorage(game.id);
                const todayRes = storage.getTodayResult();
                if (todayRes) {
                    isPlayed = true;
                    if (todayRes.won) {
                        isSolved = true;
                    }
                } else if (storage.hasPlayedToday()) {
                    isPlayed = true;
                    const stats = storage.getStats();
                    if (stats && stats.won > 0 && stats.streak > 0) {
                        isSolved = true;
                    }
                }
            } catch (e) {}

            const solvedText = t('badge_solved', 'SOLVED ✅');
            const failedText = t('badge_failed', 'FAILED ❌');

            const statusBadge = isSolved
                ? `<span class="fa-suggestion-badge-solved">${solvedText}</span>`
                : (isPlayed ? `<span class="fa-suggestion-badge-failed">${failedText}</span>` : '');

            cardsHtml += `
                <a href="${game.file}" class="fa-suggestion-card" data-game-id="${game.id}">
                    <div class="fa-suggestion-icon-wrap" style="color: ${game.color}">
                        <span class="material-symbols-outlined fa-suggestion-icon">${game.icon}</span>
                    </div>
                    <div class="fa-suggestion-content">
                        <div class="fa-suggestion-title-row">
                            <span class="fa-suggestion-title" style="color: ${game.color}">${gameTitle}</span>
                            ${statusBadge}
                        </div>
                        <p class="fa-suggestion-tagline">${gameTagline}</p>
                    </div>
                </a>
            `;
        });

        container.innerHTML = `
            <section class="fa-suggestions-wrapper">
                <h3 class="fa-suggestions-header">
                    <span class="material-symbols-outlined text-sm text-accent">grid_view</span>
                    ${sectionTitle}
                </h3>
                <div class="fa-suggestions-grid">
                    ${cardsHtml}
                </div>
                <div class="fa-suggestions-back">
                    <a href="${homeUrl}">${backText}</a>
                </div>
            </section>
        `;

        const cardLinks = container.querySelectorAll('.fa-suggestion-card');
        cardLinks.forEach(card => {
            card.addEventListener('click', () => {
                const targetGame = card.getAttribute('data-game-id');
                trackEvent('game_suggestion_click', {
                    from_game: currentGame,
                    to_game: targetGame,
                    locale: currentLang
                });
            });
        });
    }

    function autoInitSuggestions() {
        const el = document.getElementById('fa-game-suggestions');
        if (el) {
            initGameSuggestions({ containerId: 'fa-game-suggestions' });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initAnalyticsAndConsent();
            initFeedbackSystem();
            initPWAInstall();
            initLanguageSwitcher();
            initHowToPlay();
            autoInitSuggestions();
            trackEvent('page_view');
        });
    } else {
        initAnalyticsAndConsent();
        initFeedbackSystem();
        initPWAInstall();
        initLanguageSwitcher();
        initHowToPlay();
        autoInitSuggestions();
        trackEvent('page_view');
    }


    // ────────────────────────────────────────────────────────
    // Public API
    // ────────────────────────────────────────────────────────
    global.FootyUI = {
        FootyDropdown,
        FootyLives,
        FootyModal,
        FootyStorage,
        FootyWrongGuesses,
        buildBackInTimeLinks,
        initAccentColor,
        share,
        shareWhatsApp,
        buildShareText,
        buildShareUrl,
        getUrlSource,
        buildEmojiGrid,
        formatFee,
        todayStr,
        toast,
        confirm: confirmModal,
        showFeedback,
        startVarReview,
        getVarState: () => varState,
        trackEvent,
        trackGuess: (params) => trackEvent('guess', params),
        trackHint: (params) => trackEvent('hint', params),
        trackSkip: (params) => trackEvent('skip', params),
        trackGiveUp: (params) => trackEvent('give_up', params),
        trackExtraLife: (params) => trackEvent('extra_life', params),
        trackVarAppeal: (params) => trackEvent('var_appeal', params),
        trackVarDecision: (params) => trackEvent('var_decision', params),
        trackGameEnd: (params) => trackEvent('game_end', params),
        syncPuzzleOverrides,
        getVisitorId,
        getSessionId,
        normalizeStr,
        canonicalClub,
        isClubMatch,
        isPlayerMatch,
        initPWAInstall,
        showIOSInstallSheet,
        renderPWABanner,
        initLanguageSwitcher,
        initGameSuggestions,
        GAMES_REGISTRY
    };

})(window);

