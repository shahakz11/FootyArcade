/**
 * test_home_screen_status.js
 * Unit tests verifying FootyStorage.getTodayStatus() across all states
 * and validating home screen card status badges and dynamic CTAs.
 */

const assert = require('assert');
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
            setProperty: () => {},
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
        getAttribute: () => null,
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

// Load footy-ui.js
const footyUiCode = fs.readFileSync(path.join(__dirname, '..', 'games', 'footy-ui.js'), 'utf8');
eval(footyUiCode);
const FootyUI = global.window.FootyUI;

console.log("=== Testing FootyStorage getTodayStatus() & Home Screen Status Indicators ===\n");

const todayStr = new Date().toISOString().slice(0, 10);
const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);

// [Test 1] Unplayed status
console.log("[Test 1] Unplayed puzzle returns status 'unplayed'");
global.localStorage.clear();
const storage = new FootyUI.FootyStorage('top_transfers_test');
let status = storage.getTodayStatus();
assert.strictEqual(status.status, 'unplayed', 'Expected unplayed status for empty storage');
console.log("  ✓ Correctly returned 'unplayed' for fresh puzzle");

// [Test 2] In-Progress status
console.log("\n[Test 2] In-Progress session returns status 'in_progress'");
global.localStorage.clear();
storage.saveInProgress(10, { livesRemaining: 2, currentStep: 1 });
status = storage.getTodayStatus();
assert.strictEqual(status.status, 'in_progress', 'Expected in_progress status when active session exists');
assert.strictEqual(status.puzzleNum, 10, 'Expected correct puzzleNum in status');
assert.strictEqual(status.state.livesRemaining, 2, 'Expected state payload in status');
console.log("  ✓ Correctly returned 'in_progress' with active session data");

// [Test 3] Won status
console.log("\n[Test 3] Completed won puzzle returns status 'won'");
global.localStorage.clear();
storage.recordResult(10, true, 5, 5, false, 'win');
status = storage.getTodayStatus();
assert.strictEqual(status.status, 'won', 'Expected won status');
assert.strictEqual(status.outcome, 'win', 'Expected outcome win');
assert.strictEqual(status.score, 5, 'Expected score 5');
assert.strictEqual(status.maxScore, 5, 'Expected maxScore 5');
console.log("  ✓ Correctly returned 'won' with score (5/5)");

// [Test 4] Partial success status
console.log("\n[Test 4] Completed partial success returns status 'partial'");
global.localStorage.clear();
storage.recordResult(11, false, 3, 5, false, 'partial');
status = storage.getTodayStatus();
assert.strictEqual(status.status, 'partial', 'Expected partial status');
assert.strictEqual(status.outcome, 'partial', 'Expected outcome partial');
assert.strictEqual(status.score, 3, 'Expected score 3');
assert.strictEqual(status.maxScore, 5, 'Expected maxScore 5');
console.log("  ✓ Correctly returned 'partial' with score (3/5)");

// [Test 5] Loss / Missed status
console.log("\n[Test 5] Completed loss returns status 'loss'");
global.localStorage.clear();
storage.recordResult(12, false, 1, 5, false, 'loss');
status = storage.getTodayStatus();
assert.strictEqual(status.status, 'loss', 'Expected loss status');
assert.strictEqual(status.outcome, 'loss', 'Expected outcome loss');
console.log("  ✓ Correctly returned 'loss'");

// [Test 6] Stale in-progress from yesterday is not marked in-progress
console.log("\n[Test 6] Stale in-progress from yesterday is discarded");
global.localStorage.clear();
global.localStorage.setItem('footy_v2_top_transfers_test_inprogress', JSON.stringify({
    puzzleNum: 9,
    date: yesterday,
    state: { currentStep: 2 }
}));
status = storage.getTodayStatus();
assert.strictEqual(status.status, 'unplayed', 'Stale in-progress state should not mark today as in_progress');
console.log("  ✓ Correctly ignored stale yesterday in-progress state");

// [Test 7] Verify index.html and es/index.html integration
console.log("\n[Test 7] Verify index.html & es/index.html source integration");
const enIndex = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const esIndex = fs.readFileSync(path.join(__dirname, '..', 'es', 'index.html'), 'utf8');

// English assertions
assert.ok(enIndex.includes('storage.getTodayStatus()'), 'index.html must query storage.getTodayStatus()');
assert.ok(enIndex.includes('Solved'), 'index.html must have Solved badge');
assert.ok(enIndex.includes('Partial'), 'index.html must have Partial badge');
assert.ok(enIndex.includes('Missed'), 'index.html must have Missed badge');
assert.ok(enIndex.includes('In Progress'), 'index.html must have In Progress badge');
assert.ok(enIndex.includes('CONTINUE'), 'index.html must have CONTINUE CTA');

// Spanish assertions
assert.ok(esIndex.includes('storage.getTodayStatus()'), 'es/index.html must query storage.getTodayStatus()');
assert.ok(esIndex.includes('Completado'), 'es/index.html must have Completado badge');
assert.ok(esIndex.includes('Parcial'), 'es/index.html must have Parcial badge');
assert.ok(esIndex.includes('No superado'), 'es/index.html must have No superado badge');
assert.ok(esIndex.includes('En curso'), 'es/index.html must have En curso badge');
assert.ok(esIndex.includes('CONTINUAR'), 'es/index.html must have CONTINUAR CTA');

console.log("  ✓ Both index.html and es/index.html contain complete status badge and CTA logic");

console.log("\n✅ ALL HOME SCREEN STATUS INDICATOR TESTS PASSED SUCCESSFULLY!");
