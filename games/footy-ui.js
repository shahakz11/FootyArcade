/**
 * footy-ui.js — FootyArcade Shared Component Library
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
     * @param {Function} cfg.filterFn      — (item, query) => boolean
     * @param {Function} cfg.onSelect      — (item) => void called on selection
     * @param {number}   [cfg.maxResults]  — Max dropdown rows (default 7)
     */
    function FootyDropdown(cfg) {
        const input = document.getElementById(cfg.inputId);
        const list = document.getElementById(cfg.listId);
        if (!input || !list) {
            console.warn('[FootyUI] FootyDropdown: element not found', cfg);
            return;
        }

        const maxResults = cfg.maxResults || 7;
        let activeIndex = -1;
        let currentItems = [];
        let selectedItem = null;

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

                const label = document.createElement('span');
                label.textContent = cfg.labelFn(item);
                row.appendChild(label);

                if (cfg.badgeFn) {
                    const badge = document.createElement('span');
                    badge.className = 'fa-row-badge';
                    badge.textContent = cfg.badgeFn(item);
                    row.appendChild(badge);
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
            input.value = cfg.labelFn(item);
            list.classList.add('hidden');
            document.getElementById('error-message')?.classList.add('hidden');
            input.focus();
            if (cfg.onSelect) cfg.onSelect(item);
        }

        // Public method — call after programmatic value set to reset selection
        this.clearSelection = () => { selectedItem = null; };

        // Public method — returns the currently selected item (null if none)
        this.getSelected = () => selectedItem;

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
                const matches = cfg.data.filter(item => cfg.filterFn(item, q)).slice(0, maxResults);
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
                }
            } else if (e.key === 'Escape') {
                list.classList.add('hidden');
            }
        });

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
    function FootyLives(cfg) {
        let lives = cfg.initial;
        const counterEl = document.getElementById(cfg.counterId);
        const heartEl = cfg.heartId ? document.getElementById(cfg.heartId) : null;

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
        this.add = (n = 1) => { lives += n; update(); };
        this.lose = (n = 1) => { lives = Math.max(0, lives - n); update(); };
        this.isDead = () => lives <= 0;

        // Render initial value
        if (counterEl) counterEl.textContent = lives;
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

        this.show = (opts) => {
            // Track game completion
            trackEvent('game_end', {
                won: opts.won,
                score: opts.score,
                maxScore: opts.maxScore,
                extraDetails: opts.title
            });

            // opts: { won, score, maxScore, streak, extraText, shareText, backInTimeLinks }
            const iconEl = document.getElementById(cfg.iconId || 'modal-icon');
            const titleEl = document.getElementById(cfg.titleId || 'modal-title');
            const msgEl = document.getElementById(cfg.messageId || 'modal-message');
            const scoreEl = document.getElementById(cfg.scoreId || 'modal-score');
            const streakEl = document.getElementById(cfg.streakId || 'modal-streak');

            if (iconEl) {
                iconEl.textContent = opts.won ? 'emoji_events' : 'dangerous';
                iconEl.className = `material-symbols-outlined text-6xl ${opts.won ? 'text-accent' : 'text-error'}`;
            }
            if (titleEl) titleEl.textContent = opts.title || (opts.won ? 'COMPLETED!' : 'GAME OVER');
            if (msgEl) msgEl.textContent = opts.message || '';
            if (scoreEl) scoreEl.textContent = `${opts.score}/${opts.maxScore}`;
            if (streakEl) streakEl.textContent = opts.streak;

            if (cfg.extraInfoId && opts.extraText) {
                const el = document.getElementById(cfg.extraInfoId);
                if (el) el.textContent = opts.extraText;
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

            modal?.classList.remove('hidden');
        };

        this.hide = () => modal?.classList.add('hidden');
    }


    // ────────────────────────────────────────────────────────
    // 4. FootyShare — Standardised share text
    // ────────────────────────────────────────────────────────
    /**
     * Builds and copies the canonical share text for any game.
     * @param {object} opts
     * @param {string} opts.gameName
     * @param {number} opts.puzzleNum
     * @param {number} opts.score
     * @param {number} opts.maxScore
     * @param {number} opts.lives       — remaining lives
     * @param {number} opts.initialLives
     * @param {boolean} opts.won
     * @param {string} opts.url
     */
    function share(opts) {
        // Track share event
        trackEvent('share', {
            won: opts.won,
            score: opts.score,
            maxScore: opts.maxScore,
            lives: opts.lives
        });

        const livesUsed = opts.initialLives - opts.lives;
        const blocks = buildEmojiGrid(opts.score, opts.maxScore, opts.won);
        const text = [
            `⚽ FootyArcade — ${opts.gameName} #${opts.puzzleNum}`,
            blocks,
            `${opts.won ? '✅' : '❌'} ${opts.score}/${opts.maxScore} correct · ❤️ ${livesUsed} lives used`,
            `🔗 ${opts.url}`
        ].join('\n');

        if (navigator.clipboard) {
            navigator.clipboard.writeText(text)
                .then(() => _toast('Copied to clipboard!'))
                .catch(() => _fallbackShare(text));
        } else {
            _fallbackShare(text);
        }
    }

    function buildEmojiGrid(score, maxScore, won) {
        const cells = [];
        for (let i = 0; i < maxScore; i++) {
            cells.push(i < score ? '🟩' : '⬛');
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
        const backdrop = document.createElement('div');
        backdrop.className = 'fa-confirm-backdrop';

        const card = document.createElement('div');
        card.className = 'fa-confirm-card';

        card.innerHTML = `
            <h4 class="font-headline text-2xl text-accent uppercase italic tracking-wide mb-2">${opts.title}</h4>
            <p class="text-on-surface-variant text-sm mb-6">${opts.message}</p>
            <div class="flex gap-3 justify-center">
                <button id="fa-confirm-cancel" class="flex-1 py-2.5 bg-surface-container-high border border-white/10 text-white font-headline text-md uppercase italic rounded-xl hover:bg-surface-container-highest transition-all">
                    ${opts.cancelText || 'CANCEL'}
                </button>
                <button id="fa-confirm-ok" class="flex-1 py-2.5 bg-accent text-black font-headline text-md uppercase italic rounded-xl hover:brightness-110 active:scale-95 transition-all">
                    ${opts.confirmText || 'CONFIRM'}
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

    /**
     * Shows a transient right/wrong answer feedback popup.
     * @param {object} opts
     * @param {boolean} opts.isCorrect
     * @param {string} opts.title
     * @param {string} opts.message
     */
    function showFeedback(opts) {
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
            <div>
                <h4 class="font-headline text-lg uppercase italic tracking-wide" style="color: ${color}; margin: 0; line-height: 1.2;">
                    ${opts.title}
                </h4>
                <p class="text-on-surface-variant text-xs font-semibold" style="margin: 4px 0 0 0; color: #a3a3a3; line-height: 1.3;">
                    ${opts.message}
                </p>
            </div>
        `;

        backdrop.appendChild(card);
        document.body.appendChild(backdrop);

        setTimeout(() => {
            backdrop.style.opacity = '0';
            backdrop.style.transform = 'translate(-50%, -20px)';
            backdrop.style.transition = 'opacity 0.25s cubic-bezier(0.4, 0, 1, 1), transform 0.25s cubic-bezier(0.4, 0, 1, 1)';
            setTimeout(() => backdrop.remove(), 250);
        }, 1500);
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
            return d.lastPlayedDate === todayStr();
        };

        /** Returns true if this specific puzzleNum is already in history */
        this.hasPlayedPuzzle = (puzzleNum) => {
            const d = load();
            return !!d.history[puzzleNum];
        };

        /** Record a completed game result */
        this.recordResult = (puzzleNum, won, score, maxScore, isBackInTime = false) => {
            const d = load();
            if (!isBackInTime) {
                d.played++;
                if (won) { d.won++; d.streak++; } else { d.streak = 0; }
                d.bestStreak = Math.max(d.bestStreak, d.streak);
                d.lastPlayedDate = todayStr();
                d.lastPuzzleNum = puzzleNum;
            }
            // Always record in history (even back-in-time, separately keyed)
            const histKey = isBackInTime ? `bit_${puzzleNum}` : String(puzzleNum);
            d.history[histKey] = { won, score, maxScore, date: todayStr() };
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
        const section = document.getElementById(sectionId);
        const container = document.getElementById(containerId);
        const shown = new Set();

        this.add = (text) => {
            if (shown.has(text.toLowerCase())) return;
            shown.add(text.toLowerCase());

            section?.classList.remove('hidden');
            const badge = document.createElement('span');
            badge.className = 'fa-wrong-badge';
            badge.textContent = text;
            container?.appendChild(badge);
        };

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
     * @returns {Array<{label, href}>}
     */
    function buildBackInTimeLinks(gameId, maxDays, storage) {
        maxDays = maxDays || 7;
        const labels = ['Yesterday', '2 days ago', '3 days ago', '4 days ago',
            '5 days ago', '6 days ago', '7 days ago',
            '8 days ago', '9 days ago', '10 days ago'];
        const links = [];
        for (let d = 1; d <= maxDays; d++) {
            const label = labels[d - 1] || `${d} days ago`;
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
    function formatFee(val) {
        const fee = parseFloat(val);
        if (isNaN(fee) || fee === 0) return 'Free / Loan';
        if (fee >= 1000000) return `€${(fee / 1000000).toFixed(1)}M`;
        if (fee >= 1000) return `€${(fee / 1000).toFixed(0)}K`;
        return 'Free';
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

        banner.innerHTML = `
            <div class="fa-consent-content">
                <span class="material-symbols-outlined text-accent text-2xl shrink-0">cookie</span>
                <div class="space-y-1 text-left flex-grow">
                    <h5 class="font-title text-sm font-bold text-white uppercase tracking-wider">Cookie Consent</h5>
                    <p class="text-on-surface-variant text-xs leading-relaxed max-w-lg">
                        We use cookies to analyze traffic, track errors, and improve your trivia experience. By clicking "ACCEPT ALL", you agree to our 
                        <a href="${privacyPath}" class="text-accent underline hover:brightness-110">Privacy Policy</a> and 
                        <a href="${termsPath}" class="text-accent underline hover:brightness-110">Terms & Conditions</a>.
                    </p>
                </div>
                <div class="flex gap-2 shrink-0 w-full sm:w-auto justify-end">
                    <button id="fa-consent-decline" class="px-4 py-2 bg-surface border border-white/10 text-on-surface-variant hover:text-white rounded-xl text-xs font-bold uppercase tracking-wider transition-all">
                        DECLINE
                    </button>
                    <button id="fa-consent-accept" class="px-4 py-2 bg-accent text-black hover:brightness-110 active:scale-95 rounded-xl text-xs font-bold uppercase tracking-wider transition-all">
                        ACCEPT ALL
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

    // ── Feedback System ──────────────────────────────────────
    const FEEDBACK_WEBHOOK_URL = 'https://script.google.com/macros/s/AKfycbxEG3jA0QduSlh3ZmMR-98lTK1i4AbO-FgmFpymlJTof_8DZpZdmODSto0Q4NTyX7_7OA/exec';

    function trackEvent(eventName, params = {}) {
        if (!FEEDBACK_WEBHOOK_URL || FEEDBACK_WEBHOOK_URL.includes('XXXX')) {
            return;
        }

        const payload = {
            type: 'event',
            eventName: eventName,
            gameId: params.gameId || global.GAME_ID || '',
            puzzleNum: params.puzzleNum !== undefined ? params.puzzleNum : (global.puzzleNum !== undefined ? global.puzzleNum : 0),
            score: params.score,
            maxScore: params.maxScore,
            lives: params.lives,
            won: params.won,
            isBackInTime: params.isBackInTime !== undefined ? params.isBackInTime : (global.isBackInTime !== undefined ? global.isBackInTime : false),
            extraDetails: params.extraDetails || '',
            url: window.location.href,
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

    function initFeedbackSystem() {
        // Create floating button
        const trigger = document.createElement('button');
        trigger.className = 'fa-feedback-trigger';
        trigger.id = 'fa-feedback-btn';
        trigger.innerHTML = `
            <span class="material-symbols-outlined" style="font-size: 18px">rate_review</span>
            <span>Feedback</span>
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
                <h4 class="font-headline text-2xl text-accent uppercase italic tracking-wide mb-2">SEND FEEDBACK</h4>
                <p class="text-on-surface-variant text-xs mb-4">Have a bug report or a suggestion? Let us know!</p>
                
                <form id="fa-feedback-form" class="space-y-4 text-left">
                    <div>
                        <label class="block text-[10px] font-mono uppercase tracking-widest text-on-surface-variant mb-1.5">Category</label>
                        <select id="fa-feedback-category" class="fa-feedback-input" style="color-scheme: dark;" required>
                            <option value="Suggestion">Suggestion</option>
                            <option value="Bug Report">Bug Report</option>
                            <option value="Question">Question</option>
                            <option value="Other">Other</option>
                        </select>
                    </div>
                    
                    <div>
                        <label class="block text-[10px] font-mono uppercase tracking-widest text-on-surface-variant mb-1.5">Your Message</label>
                        <textarea id="fa-feedback-message" rows="4" class="fa-feedback-input" placeholder="What's on your mind?..." required></textarea>
                    </div>
                    
                    <div>
                        <label class="block text-[10px] font-mono uppercase tracking-widest text-on-surface-variant mb-1.5">Email (Optional)</label>
                        <input type="email" id="fa-feedback-email" class="fa-feedback-input" placeholder="your@email.com">
                    </div>
                    
                    <div class="pt-2">
                        <button type="submit" id="fa-feedback-submit" class="w-full py-3 bg-accent text-black font-headline text-lg uppercase italic rounded-xl hover:brightness-110 active:scale-95 transition-all flex items-center justify-center gap-2">
                            SUBMIT FEEDBACK
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
            const category = modal.querySelector('#fa-feedback-category').value;
            const message = modal.querySelector('#fa-feedback-message').value;
            const email = modal.querySelector('#fa-feedback-email').value;

            submitBtn.disabled = true;
            submitBtn.textContent = 'SUBMITTING...';

            const payload = {
                type: 'feedback',
                category,
                message,
                email,
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

                toast('Feedback submitted! Thank you.', 'success');
                trackEvent('feedback_submit', { extraDetails: category });
                modal.querySelector('#fa-feedback-message').value = '';
                modal.querySelector('#fa-feedback-email').value = '';
                closeModal();
            } catch (err) {
                console.error('[FootyUI] Feedback submission error:', err);
                toast('Error submitting feedback. Please try again.', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'SUBMIT FEEDBACK';
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
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initAnalyticsAndConsent();
            initFeedbackSystem();
            trackEvent('page_view');
        });
    } else {
        initAnalyticsAndConsent();
        initFeedbackSystem();
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
        formatFee,
        todayStr,
        toast,
        confirm: confirmModal,
        showFeedback,
        trackEvent,
    };

})(window);

