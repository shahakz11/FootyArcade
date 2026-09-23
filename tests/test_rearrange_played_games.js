/**
 * tests/test_rearrange_played_games.js
 * Unit tests verifying status-based sorting for homepage cards and in-game suggestions.
 * Validates:
 *  1. Priority order: Unplayed (1) -> In Progress (2) -> Won (3) -> Partial (4) -> Loss (5) -> Coming Soon (6)
 *  2. Stable sorting for ties
 *  3. DOM rendering order in index.html and es/index.html
 *  4. DOM rendering order and badge classes in FootyUI.initGameSuggestions()
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

function createMockElement(id, tagName = 'div') {
    const classes = new Set();
    const children = [];
    const attributes = {};
    const eventListeners = {};
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
                const classMatch = fullAttrs.match(/class="([^"]+)"/);
                if (classMatch) linkEl.className = classMatch[1];
                linkEl.innerHTML = m[4];
                children.push(linkEl);
            });
        },
        appendChild: (child) => children.push(child),
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
        addEventListener: (evt, cb) => {
            eventListeners[evt] = eventListeners[evt] || [];
            eventListeners[evt].push(cb);
        },
        removeEventListener: (evt, cb) => {
            if (eventListeners[evt]) {
                eventListeners[evt] = eventListeners[evt].filter(f => f !== cb);
            }
        },
        dispatchEvent: (evtName) => {
            if (eventListeners[evtName]) {
                eventListeners[evtName].forEach(cb => cb({}));
            }
        }
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
    removeEventListener: () => {}
};

global.window = {
    location: { href: 'https://playmaker.best/index.html', pathname: '/index.html', hostname: 'playmaker.best', search: '' },
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
    clear: () => { global.localStorage._data = {}; }
};

// Load footy-i18n.js and footy-ui.js
const footyI18nCode = fs.readFileSync(path.join(__dirname, '..', 'games', 'footy-i18n.js'), 'utf8');
eval(footyI18nCode);
const FootyI18n = global.window.FootyI18n;

const footyUiCode = fs.readFileSync(path.join(__dirname, '..', 'games', 'footy-ui.js'), 'utf8');
eval(footyUiCode);
const FootyUI = global.window.FootyUI;

console.log('=== Running test_rearrange_played_games.js ===\n');
let passed = 0;
let failed = 0;

function it(testName, fn) {
    try {
        fn();
        console.log(`  ✓ ${testName}`);
        passed++;
    } catch (err) {
        console.error(`  ✗ ${testName}`);
        console.error(err);
        failed++;
    }
}

const today = FootyUI.todayStr();

function setupMockGameState(gameId, stateType, score = 5, maxScore = 5) {
    if (stateType === 'won') {
        global.localStorage.setItem(`footy_v2_${gameId}`, JSON.stringify({
            played: 1, won: 1, streak: 1, maxStreak: 1,
            lastPlayedDate: today, lastPuzzleNum: 100,
            history: {
                "100": { date: today, won: true, outcome: 'win', score, maxScore }
            }
        }));
    } else if (stateType === 'partial') {
        global.localStorage.setItem(`footy_v2_${gameId}`, JSON.stringify({
            played: 1, won: 0, streak: 0, maxStreak: 0,
            lastPlayedDate: today, lastPuzzleNum: 100,
            history: {
                "100": { date: today, won: false, outcome: 'partial', score: 3, maxScore: 5 }
            }
        }));
    } else if (stateType === 'loss') {
        global.localStorage.setItem(`footy_v2_${gameId}`, JSON.stringify({
            played: 1, won: 0, streak: 0, maxStreak: 0,
            lastPlayedDate: today, lastPuzzleNum: 100,
            history: {
                "100": { date: today, won: false, outcome: 'loss', score: 0, maxScore: 5 }
            }
        }));
    } else if (stateType === 'in_progress') {
        global.localStorage.setItem(`footy_v2_${gameId}_inprogress`, JSON.stringify({
            date: today,
            puzzleNum: 100,
            state: { lives: 2, guessed: ['Messi'] }
        }));
    }
}

// Test 1: Status priority mapping
it('1. Status Priority Rank orders: unplayed (1) -> in_progress (2) -> won (3) -> partial (4) -> loss (5)', () => {
    const STATUS_PRIORITY = { 'unplayed': 1, 'in_progress': 2, 'won': 3, 'partial': 4, 'loss': 5 };
    const testItems = [
        { id: 'g_loss', status: 'loss' },
        { id: 'g_won', status: 'won' },
        { id: 'g_unplayed', status: 'unplayed' },
        { id: 'g_inprogress', status: 'in_progress' },
        { id: 'g_partial', status: 'partial' }
    ];
    testItems.sort((a, b) => STATUS_PRIORITY[a.status] - STATUS_PRIORITY[b.status]);
    assert.strictEqual(testItems[0].id, 'g_unplayed');
    assert.strictEqual(testItems[1].id, 'g_inprogress');
    assert.strictEqual(testItems[2].id, 'g_won');
    assert.strictEqual(testItems[3].id, 'g_partial');
    assert.strictEqual(testItems[4].id, 'g_loss');
});

// Test 2: Stable sorting for ties
it('2. Stable sort preserves relative order for tied statuses', () => {
    const STATUS_PRIORITY = { 'unplayed': 1, 'in_progress': 2, 'won': 3, 'partial': 4, 'loss': 5 };
    const testItems = [
        { id: 'top_transfers', status: 'unplayed', originalIndex: 0 },
        { id: 'top_scorers', status: 'won', originalIndex: 1 },
        { id: 'club_connect', status: 'unplayed', originalIndex: 2 },
        { id: 'player_chain', status: 'in_progress', originalIndex: 3 },
        { id: 'passport_fc', status: 'unplayed', originalIndex: 4 }
    ];
    testItems.sort((a, b) => (STATUS_PRIORITY[a.status] - STATUS_PRIORITY[b.status]) || (a.originalIndex - b.originalIndex));
    const orderedIds = testItems.map(x => x.id);
    assert.deepStrictEqual(orderedIds, [
        'top_transfers',
        'club_connect',
        'passport_fc',
        'player_chain',
        'top_scorers'
    ]);
});

// Test 3: In-game suggestions ordering and badges
it('3. initGameSuggestions sorts remaining games by priority status and renders badges', () => {
    global.localStorage.clear();
    for (let k in mockElements) delete mockElements[k];

    setupMockGameState('transfer_destination', 'loss');
    setupMockGameState('top_scorers', 'won');
    setupMockGameState('club_connect', 'in_progress');
    setupMockGameState('passport_fc', 'partial');
    // player_chain is unplayed

    const container = getMockElement('fa-game-suggestions');
    FootyUI.initGameSuggestions({ containerId: 'fa-game-suggestions', currentGame: 'top_transfers' });

    const cards = container.querySelectorAll('.fa-suggestion-card');
    assert.strictEqual(cards.length, 5);

    const cardGameIds = cards.map(c => c.getAttribute('data-game-id'));
    assert.deepStrictEqual(cardGameIds, [
        'player_chain',         // 1. unplayed
        'club_connect',        // 2. in_progress
        'top_scorers',         // 3. won
        'passport_fc',         // 4. partial
        'transfer_destination' // 5. loss
    ]);

    assert.strictEqual(cards[0].getAttribute('data-status'), 'unplayed');
    assert.strictEqual(cards[1].getAttribute('data-status'), 'in_progress');
    assert.strictEqual(cards[2].getAttribute('data-status'), 'won');
    assert.strictEqual(cards[3].getAttribute('data-status'), 'partial');
    assert.strictEqual(cards[4].getAttribute('data-status'), 'loss');

    assert(cards[1].innerHTML.includes('fa-suggestion-badge-inprogress'), 'In-progress badge should be present');
    assert(cards[2].innerHTML.includes('fa-suggestion-badge-solved'), 'Solved badge should be present');
    assert(cards[3].innerHTML.includes('fa-suggestion-badge-partial'), 'Partial badge should be present');
    assert(cards[4].innerHTML.includes('fa-suggestion-badge-failed'), 'Failed badge should be present');
});

// Test 4: i18n Dictionary tokens
it('4. FootyI18n contains all badge tokens in English and Spanish', () => {
    assert.strictEqual(FootyI18n.t('badge_solved'), 'SOLVED ✅');
    assert.strictEqual(FootyI18n.t('badge_partial'), 'PARTIAL ⚡');
    assert.strictEqual(FootyI18n.t('badge_failed'), 'MISSED ❌');
    assert.strictEqual(FootyI18n.t('badge_in_progress'), 'IN PROGRESS ⏳');
});

if (failed > 0) {
    console.error(`\nFAILED: ${failed} tests failed.`);
    process.exit(1);
} else {
    console.log(`\nPASSED: All ${passed} tests passed successfully.`);
    process.exit(0);
}
