/**
 * tests/test_new_game_tag.js
 * Verification Suite for New Game Tag & Boosting
 * ===============================================
 * Validates:
 * 1. FootyUI.isNewGame and FootyUI.getGamePuzzleNum logic and boundaries (#1 to #30).
 * 2. New game tag appears on new released game cards in homepage (index.html, es/index.html).
 * 3. Tag coexists alongside all use cases:
 *    - Unplayed today
 *    - Started / in_progress
 *    - Successful (won and partial)
 *    - Failed (loss / missed)
 * 4. New game tag appears in suggested games at bottom of game pages.
 * 5. New games are boosted and appear first during the new game period.
 * 6. Non-new games (puzzle > 30) and coming_soon games do not show the tag.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

let passed = 0;
let failed = 0;

function it(title, fn) {
    try {
        fn();
        console.log(`  ✓ ${title}`);
        passed++;
    } catch (e) {
        console.error(`  ✗ ${title}`);
        console.error(e);
        failed++;
    }
}

// ─────────────────────────────────────────────────────────────
// Setup Browser Environment Mocks
// ─────────────────────────────────────────────────────────────
function createMockElement(id, tagName = 'div') {
    const classes = new Set();
    const children = [];
    const attributes = {};
    let text = '';
    let html = '';

    const el = {
        id,
        tagName: tagName.toUpperCase(),
        style: {
            setProperty: () => {},
            cssText: '',
            display: ''
        },
        classList: {
            add: (...cls) => cls.forEach(c => classes.add(c)),
            remove: (...cls) => cls.forEach(c => classes.delete(c)),
            contains: (c) => classes.has(c),
            toggle: (c, force) => {
                if (force === undefined) {
                    classes.has(c) ? classes.delete(c) : classes.add(c);
                } else if (force) {
                    classes.add(c);
                } else {
                    classes.delete(c);
                }
            }
        },
        get className() { return Array.from(classes).join(' '); },
        set className(str) {
            classes.clear();
            (str || '').split(/\s+/).filter(Boolean).forEach(c => classes.add(c));
        },
        get textContent() { return text; },
        set textContent(val) { text = String(val); },
        get innerHTML() { return html; },
        set innerHTML(val) {
            html = String(val);
            children.length = 0;
            const linkMatches = [...html.matchAll(/<a\s+([^>]*?)href="([^"]*)"([^>]*?)>([\s\S]*?)<\/a>/gi)];
            linkMatches.forEach((m, idx) => {
                const linkEl = createMockElement(`dyn_a_${idx}`, 'a');
                linkEl.href = m[2];
                const fullAttrs = m[1] + ' ' + m[3];
                const dataGameMatch = fullAttrs.match(/data-game-id="([^"]+)"/);
                if (dataGameMatch) linkEl.setAttribute('data-game-id', dataGameMatch[1]);
                const dataStatusMatch = fullAttrs.match(/data-status="([^"]+)"/);
                if (dataStatusMatch) linkEl.setAttribute('data-status', dataStatusMatch[1]);
                const dataIsNewMatch = fullAttrs.match(/data-is-new="([^"]+)"/);
                if (dataIsNewMatch) linkEl.setAttribute('data-is-new', dataIsNewMatch[1]);
                const classMatch = fullAttrs.match(/class="([^"]+)"/);
                if (classMatch) linkEl.className = classMatch[1];
                linkEl.innerHTML = m[4];
                children.push(linkEl);
            });
        },
        appendChild: (child) => children.push(child),
        insertBefore: (child) => children.unshift(child),
        children,
        querySelector: (sel) => {
            const all = el.querySelectorAll(sel);
            return all.length > 0 ? all[0] : createMockElement('sub');
        },
        querySelectorAll: (sel) => {
            if (sel === '.fa-suggestion-card') {
                return children.filter(c => c.classList.contains('fa-suggestion-card'));
            }
            if (sel === 'a') {
                return children.filter(c => c.tagName === 'A');
            }
            return [];
        },
        getAttribute: (k) => attributes[k] || null,
        setAttribute: (k, v) => { attributes[k] = String(v); },
        addEventListener: () => {},
        removeEventListener: () => {}
    };
    return el;
}

const mockElements = {};
function getMockElement(id) {
    if (!mockElements[id]) {
        mockElements[id] = createMockElement(id);
    }
    return mockElements[id];
}

global.document = {
    getElementById: (id) => getMockElement(id),
    createElement: (tag) => createMockElement(`dyn_${Math.random().toString(36).slice(2)}`, tag),
    body: createMockElement('body'),
    querySelector: () => createMockElement('sub'),
    querySelectorAll: () => [],
    addEventListener: () => {},
    removeEventListener: () => {},
    readyState: 'complete'
};

global.window = {
    location: { href: 'https://playmaker.best/games/top_transfers.html', pathname: '/games/top_transfers.html', hostname: 'playmaker.best', search: '' },
    open: () => {},
    addEventListener: () => {},
    removeEventListener: () => {}
};

global.sessionStorage = {
    _data: {},
    getItem: (k) => global.sessionStorage._data[k] || null,
    setItem: (k, v) => { global.sessionStorage._data[k] = String(v); },
    removeItem: (k) => { delete global.sessionStorage._data[k]; },
    clear: () => { global.sessionStorage._data = {}; }
};

global.localStorage = {
    _data: {},
    getItem: (k) => global.localStorage._data[k] || null,
    setItem: (k, v) => { global.localStorage._data[k] = String(v); },
    removeItem: (k) => { delete global.localStorage._data[k]; },
    clear: () => { global.localStorage._data = {}; },
    get length() { return Object.keys(global.localStorage._data).length; },
    key: (i) => Object.keys(global.localStorage._data)[i] || null
};

// Load footy-i18n.js & footy-ui.js
const i18nCode = fs.readFileSync(path.join(__dirname, '..', 'games', 'footy-i18n.js'), 'utf8');
eval(i18nCode);
const FootyI18n = global.window.FootyI18n;

const footyUiCode = fs.readFileSync(path.join(__dirname, '..', 'games', 'footy-ui.js'), 'utf8');
eval(footyUiCode);
const FootyUI = global.window.FootyUI;

console.log("=== Testing New Game Tag & Boosting Functionality ===\n");

// ─────────────────────────────────────────────────────────────
// Test Suite
// ─────────────────────────────────────────────────────────────

it('1. Puzzle number calculation matches launch date offset accurately', () => {
    // Launch on 2026-10-31
    const gameAB = { id: 'anyone_but', launchDate: '2026-10-31' };
    assert.strictEqual(FootyUI.getGamePuzzleNum(gameAB, '2026-10-31'), 1, 'Launch day must be Puzzle #1');
    assert.strictEqual(FootyUI.getGamePuzzleNum(gameAB, '2026-11-01'), 2, 'Day 2 must be Puzzle #2');
    assert.strictEqual(FootyUI.getGamePuzzleNum(gameAB, '2026-11-29'), 30, 'Day 30 must be Puzzle #30');
    assert.strictEqual(FootyUI.getGamePuzzleNum(gameAB, '2026-11-30'), 31, 'Day 31 must be Puzzle #31');

    // Default launch date 2026-07-27 (top_transfers)
    const gameTT = { id: 'top_transfers', launchDate: '2026-07-27' };
    assert.strictEqual(FootyUI.getGamePuzzleNum(gameTT, '2026-10-31'), 97, '2026-10-31 should be Puzzle #97');
});

it('2. isNewGame is strictly active from Puzzle #1 through Puzzle #30', () => {
    const game = { id: 'new_game', launchDate: '2026-10-31' };
    // Inside window
    assert.strictEqual(FootyUI.isNewGame(game, '2026-10-31'), true, 'Puzzle #1 must be new');
    assert.strictEqual(FootyUI.isNewGame(game, '2026-11-14'), true, 'Puzzle #15 must be new');
    assert.strictEqual(FootyUI.isNewGame(game, '2026-11-29'), true, 'Puzzle #30 must be new (exact boundary)');

    // Outside window
    assert.strictEqual(FootyUI.isNewGame(game, '2026-11-30'), false, 'Puzzle #31 must NOT be new (boundary + 1)');
    assert.strictEqual(FootyUI.isNewGame(game, '2026-12-15'), false, 'Puzzle #46 must NOT be new');

    // Before launch
    assert.strictEqual(FootyUI.isNewGame(game, '2026-10-30'), false, 'Before launch date must NOT be new');

    // Coming soon games are never new
    assert.strictEqual(FootyUI.isNewGame({ id: 'future', status: 'coming_soon', puzzleNum: 1 }), false);
});

it('3. In-game suggestions boost new game to position 0 and render tag', () => {
    global.localStorage.clear();
    for (let k in mockElements) delete mockElements[k];

    FootyUI.initGameSuggestions({ containerId: 'fa-game-suggestions', currentGame: 'top_transfers' });
    const container = getMockElement('fa-game-suggestions');
    const cards = container.querySelectorAll('.fa-suggestion-card');

    assert.strictEqual(cards.length, 7, 'Should display all other 7 live games');
    // First card must be the new game (anyone_but)
    assert.strictEqual(cards[0].getAttribute('data-game-id'), 'anyone_but', 'New game anyone_but must be boosted to first position');
    assert.strictEqual(cards[0].getAttribute('data-is-new'), 'true', 'Card 0 must have data-is-new="true"');
    assert.ok(cards[0].innerHTML.includes('fa-suggestion-badge-new'), 'Card 0 must render fa-suggestion-badge-new');
    assert.ok(cards[0].innerHTML.includes('fa-new-game-tag'), 'Card 0 must have fa-new-game-tag class');
});

it('4. Tag coexists alongside all gameplay states in suggestions (unplayed, started, won, partial, loss)', () => {
    const today = FootyUI.todayStr();

    // 4a. Unplayed state
    global.localStorage.clear();
    for (let k in mockElements) delete mockElements[k];
    FootyUI.initGameSuggestions({ containerId: 'fa-game-suggestions', currentGame: 'top_transfers' });
    let cont = getMockElement('fa-game-suggestions');
    let card = cont.querySelectorAll('.fa-suggestion-card').find(c => c.getAttribute('data-game-id') === 'anyone_but');
    assert.ok(card.innerHTML.includes('fa-suggestion-badge-new'), 'Unplayed: NEW badge present');
    assert.ok(!card.innerHTML.includes('fa-suggestion-badge-solved'), 'Unplayed: no solved badge');
    assert.ok(!card.innerHTML.includes('fa-suggestion-badge-failed'), 'Unplayed: no failed badge');

    // 4b. Started (in_progress) state
    global.localStorage.setItem('footy_v2_anyone_but_inprogress', JSON.stringify({
        date: today, puzzleNum: 1, state: { step: 1 }
    }));
    for (let k in mockElements) delete mockElements[k];
    FootyUI.initGameSuggestions({ containerId: 'fa-game-suggestions', currentGame: 'top_transfers' });
    cont = getMockElement('fa-game-suggestions');
    card = cont.querySelectorAll('.fa-suggestion-card').find(c => c.getAttribute('data-game-id') === 'anyone_but');
    assert.ok(card.innerHTML.includes('fa-suggestion-badge-new'), 'Started: NEW badge present');
    assert.ok(card.innerHTML.includes('fa-suggestion-badge-inprogress'), 'Started: IN PROGRESS badge also present');

    // 4c. Successful (won) state
    global.localStorage.clear();
    const storage = new FootyUI.FootyStorage('anyone_but');
    storage.recordResult(1, true, 5, 5, false, 'win');
    for (let k in mockElements) delete mockElements[k];
    FootyUI.initGameSuggestions({ containerId: 'fa-game-suggestions', currentGame: 'top_transfers' });
    cont = getMockElement('fa-game-suggestions');
    card = cont.querySelectorAll('.fa-suggestion-card').find(c => c.getAttribute('data-game-id') === 'anyone_but');
    assert.ok(card.innerHTML.includes('fa-suggestion-badge-new'), 'Won: NEW badge present');
    assert.ok(card.innerHTML.includes('fa-suggestion-badge-solved'), 'Won: SOLVED badge also present');

    // 4d. Partial state
    global.localStorage.clear();
    storage.recordResult(1, false, 3, 5, false, 'partial');
    for (let k in mockElements) delete mockElements[k];
    FootyUI.initGameSuggestions({ containerId: 'fa-game-suggestions', currentGame: 'top_transfers' });
    cont = getMockElement('fa-game-suggestions');
    card = cont.querySelectorAll('.fa-suggestion-card').find(c => c.getAttribute('data-game-id') === 'anyone_but');
    assert.ok(card.innerHTML.includes('fa-suggestion-badge-new'), 'Partial: NEW badge present');
    assert.ok(card.innerHTML.includes('fa-suggestion-badge-partial'), 'Partial: PARTIAL badge also present');

    // 4e. Failed (loss) state
    global.localStorage.clear();
    storage.recordResult(1, false, 0, 5, false, 'loss');
    for (let k in mockElements) delete mockElements[k];
    FootyUI.initGameSuggestions({ containerId: 'fa-game-suggestions', currentGame: 'top_transfers' });
    cont = getMockElement('fa-game-suggestions');
    card = cont.querySelectorAll('.fa-suggestion-card').find(c => c.getAttribute('data-game-id') === 'anyone_but');
    assert.ok(card.innerHTML.includes('fa-suggestion-badge-new'), 'Failed: NEW badge present');
    assert.ok(card.innerHTML.includes('fa-suggestion-badge-failed'), 'Failed: MISSED badge also present');
});

it('5. Suggesting from new game itself excludes new game and maintains standard order', () => {
    global.localStorage.clear();
    for (let k in mockElements) delete mockElements[k];

    FootyUI.initGameSuggestions({ containerId: 'fa-game-suggestions', currentGame: 'anyone_but' });
    const container = getMockElement('fa-game-suggestions');
    const cards = container.querySelectorAll('.fa-suggestion-card');

    assert.strictEqual(cards.length, 7);
    const ids = cards.map(c => c.getAttribute('data-game-id'));
    assert.ok(!ids.includes('anyone_but'), 'Current game anyone_but must be excluded from its own suggestions');
});

it('6. Homepage markup and scripts support new game badge and priority boost in EN & ES', () => {
    const enHtml = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
    const esHtml = fs.readFileSync(path.join(__dirname, '..', 'es', 'index.html'), 'utf8');

    // Must query FootyUI.isNewGame
    assert.ok(enHtml.includes('FootyUI.isNewGame(game)'), 'EN homepage queries isNewGame');
    assert.ok(esHtml.includes('FootyUI.isNewGame(game)'), 'ES homepage queries isNewGame');

    // Must have fa-new-game-tag
    assert.ok(enHtml.includes('fa-new-game-tag'), 'EN homepage has fa-new-game-tag');
    assert.ok(esHtml.includes('fa-new-game-tag'), 'ES homepage has fa-new-game-tag');

    // Must boost new games in sort: newA !== newB
    assert.ok(enHtml.includes('const newA = a.isNew ? 0 : 1'), 'EN homepage sorts new games first');
    assert.ok(esHtml.includes('const newA = a.isNew ? 0 : 1'), 'ES homepage sorts new games first');

    // Badges container wraps both new tag and status badge
    assert.ok(enHtml.includes('${newBadgeHtml}') && enHtml.includes('${badgeHtml}'), 'EN homepage renders both new badge and status badge');
    assert.ok(esHtml.includes('${newBadgeHtml}') && esHtml.includes('${badgeHtml}'), 'ES homepage renders both new badge and status badge');
});

if (failed > 0) {
    console.error(`\nFAILED: ${failed} tests failed.`);
    process.exit(1);
} else {
    console.log(`\nALL ${passed} TESTS PASSED SUCCESSFULLY!`);
    process.exit(0);
}
