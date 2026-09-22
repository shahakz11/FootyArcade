/**
 * test_mid_game_storage.js
 * Unit tests verifying FootyStorage in-progress mid-game persistence,
 * spoiler/date isolation, back-in-time gating, and automatic cleanup.
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
        style: {
            setProperty: (k, v) => {},
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
    location: { href: 'https://playmaker.best/games/top_transfers.html', pathname: '/games/top_transfers.html', hostname: 'playmaker.best', search: '' },
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

const footyUiCode = fs.readFileSync(path.join(__dirname, '..', 'games', 'footy-ui.js'), 'utf8');
eval(footyUiCode);
const FootyUI = global.window.FootyUI;

console.log("=== Testing FootyStorage In-Progress Mid-Game Persistence ===");

const storage = new FootyUI.FootyStorage('top_transfers_test');
const todayStr = new Date().toISOString().slice(0, 10);
const yesterdayStr = new Date(Date.now() - 86400000).toISOString().slice(0, 10);

// Test 1: Save in-progress state for today's puzzle
console.log("\n[Test 1] Save and retrieve in-progress state for today");
const sampleState = {
    score: 3,
    lives: 4,
    guessedPlayers: ["Cristiano Ronaldo", "Gareth Bale", "Eden Hazard"],
    manuallyRevealed: [],
    revealedHints: ["Zinedine Zidane"],
    wrongGuesses: ["Lionel Messi"]
};

storage.saveInProgress(42, sampleState, false);
const retrieved = storage.getInProgress(42, false);

if (retrieved && retrieved.score === 3 && retrieved.lives === 4 && retrieved.guessedPlayers.length === 3) {
    console.log("  ✓ Correctly saved and retrieved today's in-progress state");
} else {
    console.error("  ❌ FAILED: retrieved state mismatch:", retrieved);
    process.exit(1);
}

// Test 2: Back-in-time puzzles must NEVER save or retrieve in-progress state
console.log("\n[Test 2] Back-in-time isolation");
storage.saveInProgress(42, sampleState, true); // isBackInTime = true
const bitRetrieved = storage.getInProgress(42, true);
if (bitRetrieved === null) {
    console.log("  ✓ Back-in-time returns null for getInProgress");
} else {
    console.error("  ❌ FAILED: Back-in-time returned non-null state:", bitRetrieved);
    process.exit(1);
}

// Test 3: Stale date / yesterday's in-progress is purged immediately
console.log("\n[Test 3] Stale in-progress state from yesterday is rejected and cleared");
global.localStorage.setItem('footy_v2_top_transfers_test_inprogress', JSON.stringify({
    puzzleNum: 42,
    date: yesterdayStr,
    state: sampleState
}));

const staleState = storage.getInProgress(42, false);
if (staleState === null && global.localStorage.getItem('footy_v2_top_transfers_test_inprogress') === null) {
    console.log("  ✓ Stale date rejected and key purged from localStorage");
} else {
    console.error("  ❌ FAILED: Stale state not purged:", staleState);
    process.exit(1);
}

// Test 4: Different puzzleNum is rejected and purged (tomorrow's puzzle spoiler protection)
console.log("\n[Test 4] Puzzle number mismatch is rejected and cleared");
global.localStorage.setItem('footy_v2_top_transfers_test_inprogress', JSON.stringify({
    puzzleNum: 41, // yesterday's puzzleNum
    date: todayStr,
    state: sampleState
}));

const mismatchState = storage.getInProgress(42, false);
if (mismatchState === null && global.localStorage.getItem('footy_v2_top_transfers_test_inprogress') === null) {
    console.log("  ✓ Puzzle mismatch rejected and cleared");
} else {
    console.error("  ❌ FAILED: Mismatched puzzle state not cleared:", mismatchState);
    process.exit(1);
}

// Test 5: Finished game automatically clears in-progress state
console.log("\n[Test 5] Completing a game clears in-progress state");
storage.saveInProgress(42, sampleState, false);
if (global.localStorage.getItem('footy_v2_top_transfers_test_inprogress') === null) {
    console.error("  ❌ FAILED: in-progress was not saved");
    process.exit(1);
}
storage.recordResult(42, true, 10, 10, false, 'win');
if (global.localStorage.getItem('footy_v2_top_transfers_test_inprogress') === null) {
    console.log("  ✓ recordResult cleanly cleared in-progress storage");
} else {
    console.error("  ❌ FAILED: in-progress key still present after recordResult");
    process.exit(1);
}

// Test 6: In-progress cannot overwrite an already completed game
console.log("\n[Test 6] saveInProgress does not write for already completed game");
storage.saveInProgress(42, sampleState, false);
const shouldBeNull = storage.getInProgress(42, false);
if (shouldBeNull === null) {
    console.log("  ✓ saveInProgress safely ignored for completed game");
} else {
    console.error("  ❌ FAILED: In-progress restored for already played puzzle");
    process.exit(1);
}

// Test 7: FootyWrongGuesses getAll and restore
console.log("\n[Test 7] FootyWrongGuesses getAll and restore");
const wg = new FootyUI.FootyWrongGuesses('wrong-section', 'wrong-container');
wg.add('Player A');
wg.add('Player B');
const allBad = wg.getAll();
if (allBad.length === 2 && allBad.includes('player a') && allBad.includes('player b')) {
    console.log("  ✓ FootyWrongGuesses.getAll() returned all bad guesses:", allBad);
} else {
    console.error("  ❌ FAILED: FootyWrongGuesses.getAll() returned:", allBad);
    process.exit(1);
}

const wg2 = new FootyUI.FootyWrongGuesses('wrong-section-2', 'wrong-container-2');
wg2.restore(['Player X', 'Player Y']);
if (wg2.has('Player X') && wg2.has('Player Y')) {
    console.log("  ✓ FootyWrongGuesses.restore() restored all badges");
} else {
    console.error("  ❌ FAILED: FootyWrongGuesses.restore() failed");
    process.exit(1);
}

console.log("\n✅ ALL MID-GAME IN-PROGRESS STORAGE TESTS PASSED SUCCESSFULLY!");
