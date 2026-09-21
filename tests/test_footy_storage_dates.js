/**
 * test_footy_storage_dates.js
 * Unit tests verifying FootyStorage date-strict puzzle checking and reset functionality.
 */

const fs = require('fs');
const path = require('path');

function createMockElement(id, tagName = 'div') {
    const classes = new Set();
    const children = [];
    let text = '';
    return {
        id,
        tagName,
        style: {},
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
        innerHTML: '',
        appendChild: (child) => children.push(child),
        insertBefore: (child, ref) => children.unshift(child),
        querySelector: () => createMockElement('sub'),
        querySelectorAll: () => [],
        getAttribute: (attr) => null,
        setAttribute: () => {},
        addEventListener: () => {},
        removeEventListener: () => {}
    };
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
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener: () => {},
    removeEventListener: () => {}
};
global.window = {
    location: { href: 'https://playmaker.best/games/player_chain.html', pathname: '/games/player_chain.html', hostname: 'playmaker.best', search: '' },
    open: () => {},
    addEventListener: () => {},
    removeEventListener: () => {}
};
global.sessionStorage = {
    _data: {},
    getItem: (k) => global.sessionStorage._data[k] || null,
    setItem: (k, v) => { global.sessionStorage._data[k] = String(v); },
    removeItem: (k) => { delete global.sessionStorage._data[k]; }
};
global.localStorage = {
    _data: {},
    getItem: (k) => global.localStorage._data[k] || null,
    setItem: (k, v) => { global.localStorage._data[k] = String(v); },
    removeItem: (k) => { delete global.localStorage._data[k]; }
};
global.navigator = {
    clipboard: {
        writeText: () => Promise.resolve()
    }
};

const footyUiCode = fs.readFileSync(path.join(__dirname, '..', 'games', 'footy-ui.js'), 'utf8');
eval(footyUiCode);
const FootyUI = global.window.FootyUI;

console.log("=== Testing FootyStorage Date Scoping and Reset ===");

const storage = new FootyUI.FootyStorage('player_chain_test');
const todayStr = new Date().toISOString().slice(0, 10);
const yesterdayStr = new Date(Date.now() - 86400000).toISOString().slice(0, 10);

// 1. Manually inject a stale record from a previous calendar date (e.g. yesterday) for Puzzle #10
const rawData = {
    played: 1,
    won: 1,
    streak: 1,
    bestStreak: 1,
    lastPlayedDate: yesterdayStr,
    lastPuzzleNum: 10,
    history: {
        "10": { won: true, outcome: "win", score: 4, maxScore: 4, date: yesterdayStr },
        "11": { won: true, outcome: "win", score: 4, maxScore: 4 } // Legacy record missing .date field
    }
};
localStorage.setItem('footy_v2_player_chain_test', JSON.stringify(rawData));

// Verify that today's game ignores stale record
console.log("\n[Test 1] Stale previous date record ignored for today's puzzle");
const staleResult = storage.getPuzzleResult(10, false);
if (staleResult === null) {
    console.log("  ✓ getPuzzleResult(10, false) returned null for stale date:", yesterdayStr);
} else {
    console.error("  ❌ FAILED: getPuzzleResult returned stale result:", staleResult);
    process.exit(1);
}

const hasPlayed = storage.hasPlayedPuzzle(10, false);
if (!hasPlayed) {
    console.log("  ✓ hasPlayedPuzzle(10, false) correctly returned false");
} else {
    console.error("  ❌ FAILED: hasPlayedPuzzle returned true for stale date");
    process.exit(1);
}

// Verify legacy record without date is also rejected
console.log("\n[Test 1b] Legacy record without date field is rejected");
const legacyResult = storage.getPuzzleResult(11, false);
if (legacyResult === null && !storage.hasPlayedPuzzle(11, false)) {
    console.log("  ✓ getPuzzleResult(11, false) returned null for legacy missing date");
} else {
    console.error("  ❌ FAILED: getPuzzleResult did not reject legacy record without date");
    process.exit(1);
}

// 2. Record a result for TODAY and verify it is retrieved
console.log("\n[Test 2] Result recorded today is properly retrieved");
storage.recordResult(10, true, 4, 4, false, 'win');

const todayResult = storage.getPuzzleResult(10, false);
if (todayResult && todayResult.date === todayStr && todayResult.won) {
    console.log("  ✓ getPuzzleResult(10, false) returned today's valid result:", todayResult);
} else {
    console.error("  ❌ FAILED: getPuzzleResult failed to return today's result:", todayResult);
    process.exit(1);
}

// 3. Test resetPuzzle
console.log("\n[Test 3] Reset / Replay clears puzzle history and lastPlayedDate");
storage.resetPuzzle(10, false);

const afterReset = storage.getPuzzleResult(10, false);
if (afterReset === null && !storage.hasPlayedPuzzle(10, false)) {
    console.log("  ✓ resetPuzzle(10, false) successfully wiped puzzle #10 state");
} else {
    console.error("  ❌ FAILED: resetPuzzle did not clear puzzle history");
    process.exit(1);
}

console.log("\n✅ ALL FOOTYSTORAGE TESTS PASSED SUCCESSFULLY!");
