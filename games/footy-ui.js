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
        return str
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .replace(/[-._']/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
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
                const rawLabel = cfg.labelFn(item);
                const normLabel = normalizeStr(rawLabel);

                let matches = normLabel.includes(normQ);
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
                } else {
                    tier = 3;
                }

                results.push({
                    item,
                    tier,
                    len: normLabel.length,
                    label: rawLabel
                });
            }

            results.sort((a, b) => {
                if (a.tier !== b.tier) return a.tier - b.tier;
                if (a.len !== b.len) return a.len - b.len;
                return a.label.localeCompare(b.label);
            });

            return results.map(r => r.item);
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

        function buildGiphyQuery(opts) {
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
            // Track game completion
            trackEvent('game_end', {
                won: opts.won,
                score: opts.score,
                maxScore: opts.maxScore,
                extraDetails: opts.title
            });

            // opts: { won, score, maxScore, streak, extraText, shareText, backInTimeLinks, playerName, targetName, targetType }
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

            // Giphy GIF integration
            let gifContainer = document.getElementById(cfg.gifContainerId || 'modal-gif-container');
            let gifEl = document.getElementById(cfg.gifId || 'modal-gif');

            if (!gifContainer && modal) {
                const modalCard = modal.querySelector('.fa-modal-card') || modal.firstElementChild;
                if (modalCard) {
                    gifContainer = document.createElement('div');
                    gifContainer.id = cfg.gifContainerId || 'modal-gif-container';
                    gifContainer.className = 'w-full max-h-36 sm:max-h-44 rounded-2xl overflow-hidden bg-black/40 border border-white/10 flex items-center justify-center relative my-2 sm:my-3 hidden';
                    gifEl = document.createElement('img');
                    gifEl.id = cfg.gifId || 'modal-gif';
                    gifEl.className = 'w-full h-36 sm:h-44 object-cover rounded-2xl';
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

                const query = buildGiphyQuery(opts);

                fetchGiphyGif(query, (gifUrl) => {
                    if (gifUrl) {
                        gifEl.src = gifUrl;
                        gifContainer.classList.remove('hidden');
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
            `⚽ Playmaker — ${opts.gameName} #${opts.puzzleNum}`,
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
        const meta = getActiveGameMetadata();
        const gameId = opts.gameId || meta.gameId;
        const isVarSupportedGame = ['top_scorers', 'top_transfers', 'player_chain'].includes(gameId);
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

        fetch(FEEDBACK_WEBHOOK_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'text/plain;charset=utf-8'
            },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            clearInterval(msgInterval);
            renderDecision(data);
        })
        .catch(err => {
            console.error('[FootyUI] VAR check request failed:', err);
            clearInterval(msgInterval);
            renderDecision({
                accepted: false,
                reason: 'Unable to reach VAR review server. Please check connection.'
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
            return d.lastPlayedDate === todayStr();
        };

        /** Returns true if this specific puzzleNum is already in history */
        this.hasPlayedPuzzle = (puzzleNum, isBackInTime = false) => {
            const d = load();
            const histKey = isBackInTime ? `bit_${puzzleNum}` : String(puzzleNum);
            return !!d.history[histKey];
        };

        /** Get stored puzzle result or null */
        this.getPuzzleResult = (puzzleNum, isBackInTime = false) => {
            const d = load();
            const histKey = isBackInTime ? `bit_${puzzleNum}` : String(puzzleNum);
            return d.history[histKey] || null;
        };

        /** Record a completed game result */
        this.recordResult = (puzzleNum, won, score, maxScore, isBackInTime = false) => {
            const d = load();
            const histKey = isBackInTime ? `bit_${puzzleNum}` : String(puzzleNum);
            if (d.history[histKey]) {
                return d;
            }
            if (!isBackInTime) {
                d.played++;
                if (won) { d.won++; d.streak++; } else { d.streak = 0; }
                d.bestStreak = Math.max(d.bestStreak, d.streak);
                d.lastPlayedDate = todayStr();
                d.lastPuzzleNum = puzzleNum;
            }
            // Always record in history (even back-in-time, separately keyed)
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
        const labels = ['Yesterday', '2 days ago', '3 days ago', '4 days ago',
            '5 days ago', '6 days ago', '7 days ago',
            '8 days ago', '9 days ago', '10 days ago'];
        const links = [];
        for (let d = 1; d <= maxDays; d++) {
            if (typeof currentPuzzleNum === 'number' && (currentPuzzleNum - d) < 1) {
                break;
            }
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
    const FEEDBACK_WEBHOOK_URL = 'https://script.google.com/macros/s/AKfycbxEG3jA0QduSlh3ZmMR-98lTK1i4AbO-FgmFpymlJTof_8DZpZdmODSto0Q4NTyX7_7OA/exec';

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

        const payload = {
            type: 'event',
            eventName: eventName,
            visitorId: getVisitorId(),
            sessionId: getSessionId(),
            gameId: params.gameId || meta.gameId,
            puzzleNum: params.puzzleNum !== undefined ? params.puzzleNum : meta.puzzleNum,
            score: params.score,
            maxScore: params.maxScore,
            lives: params.lives,
            won: params.won,
            isBackInTime: params.isBackInTime !== undefined ? params.isBackInTime : meta.isBackInTime,
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
            const host = window.location.hostname;
            const path = window.location.pathname;
            if (host !== 'playmaker.best' && host !== 'www.playmaker.best') {
                toast('Feedback is only submitted on the live site.', 'info');
                return;
            }
            if (path.includes('/templates/') || path.endsWith('_template.html')) {
                return;
            }

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
        startVarReview,
        getVarState: () => varState,
        trackEvent,
        syncPuzzleOverrides,
        getVisitorId,
        getSessionId,
        normalizeStr,
    };

})(window);

