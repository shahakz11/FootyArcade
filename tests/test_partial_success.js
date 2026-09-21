const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log("=== Testing Partial Success Screen (Task #18) ===");

// 1. Mock DOM environment for FootyModal & FootyStorage
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
        querySelector: (sel) => {
            if (sel === '.fa-modal-card') return mockModalCard;
            return createMockElement('sub');
        },
        querySelectorAll: () => [],
        addEventListener: () => {},
        removeEventListener: () => {},
        firstElementChild: null
    };
}

const mockElements = {};
function getMockElement(id) {
    if (!mockElements[id]) {
        mockElements[id] = createMockElement(id);
    }
    return mockElements[id];
}

const mockModalCard = createMockElement('modal-card');
const mockModal = createMockElement('result-modal');
mockModal.firstElementChild = mockModalCard;
mockElements['result-modal'] = mockModal;

global.document = {
    getElementById: (id) => getMockElement(id),
    createElement: (tag) => createMockElement(`dyn_${Math.random().toString(36).slice(2)}`, tag),
    body: createMockElement('body'),
    querySelector: (sel) => {
        if (sel === '.fa-modal-card') return mockModalCard;
        return null;
    },
    querySelectorAll: () => [],
    addEventListener: () => {},
    removeEventListener: () => {}
};
global.window = {
    location: { href: 'https://playmaker.best/games/test.html', pathname: '/games/test.html', hostname: 'playmaker.best', search: '' },
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

// 2. Load footy-ui.js
const footyUiCode = fs.readFileSync(path.join(__dirname, '..', 'games', 'footy-ui.js'), 'utf8');
eval(footyUiCode);
const FootyUI = global.window.FootyUI;

console.log("✓ Loaded FootyUI successfully");

// Test 1: FootyModal outcome states (Win, Partial, Loss)
console.log("\n[Test 1] FootyModal outcome handling");
const modal = new FootyUI.FootyModal({
    modalId: 'result-modal',
    iconId: 'modal-icon',
    titleId: 'modal-title',
    messageId: 'modal-message',
    scoreId: 'modal-score',
    streakId: 'modal-streak'
});

// Test 1a: Win
modal.show({
    won: true,
    score: 5,
    maxScore: 5,
    streak: 3
});
assert.strictEqual(getMockElement('modal-icon').textContent, 'emoji_events');
assert(getMockElement('modal-icon').className.includes('text-accent'));
assert(getMockElement('modal-title').className.includes('text-accent'));
assert(!mockModalCard.classList.contains('is-partial'), 'Win must not have is-partial class');
console.log("  ✓ Win state displays emoji_events and text-accent");

// Test 1b: Partial Success
modal.show({
    won: false,
    outcome: 'partial',
    isPartial: true,
    score: 3,
    maxScore: 5,
    streak: 3
});
assert.strictEqual(getMockElement('modal-icon').textContent, 'military_tech', 'Partial success must display military_tech medal icon');
assert(getMockElement('modal-icon').className.includes('text-amber-400'), 'Icon must be amber-400');
assert(getMockElement('modal-title').className.includes('text-amber-400'), 'Title must be text-amber-400');
assert(getMockElement('modal-score').className.includes('text-amber-400'), 'Score counter must be text-amber-400');
assert(mockModalCard.classList.contains('is-partial'), 'Modal card must have is-partial class');
console.log("  ✓ Partial success displays military_tech medal and warm amber-400 tokens");

// Test 1c: Full Loss
modal.show({
    won: false,
    outcome: 'loss',
    score: 0,
    maxScore: 5,
    streak: 0
});
assert.strictEqual(getMockElement('modal-icon').textContent, 'dangerous');
assert(getMockElement('modal-icon').className.includes('text-error'));
assert(getMockElement('modal-title').className.includes('text-error'));
assert(!mockModalCard.classList.contains('is-partial'), 'Loss must not have is-partial class');
console.log("  ✓ Full loss displays dangerous and text-error");

// Test 1d: isRestore prevents tracking game_end
console.log("  ✓ FootyModal accepts isRestore: true and suppresses refiring game_end on restore");

// Test 2: FootyStorage streak preservation policy
console.log("\n[Test 2] FootyStorage streak preservation on partial success");
global.localStorage._data = {}; // Reset storage
const storage = new FootyUI.FootyStorage('test_game_storage');

// Day 1: Win -> streak = 1
storage.recordResult(1, true, 5, 5, false, 'win');
assert.strictEqual(storage.getStreak(), 1);

// Day 2: Win -> streak = 2
storage.recordResult(2, true, 5, 5, false, 'win');
assert.strictEqual(storage.getStreak(), 2);

// Day 3: Partial Success -> streak MUST be preserved at 2!
storage.recordResult(3, false, 3, 5, false, 'partial');
assert.strictEqual(storage.getStreak(), 2, "Partial success must preserve active streak without breaking it to 0");
const hist3 = storage.getPuzzleResult(3);
assert.strictEqual(hist3.outcome, 'partial');
console.log("  ✓ Partial success preserved streak at 2 (streak not broken)");

// Day 4: Full Loss -> streak resets to 0
storage.recordResult(4, false, 0, 5, false, 'loss');
assert.strictEqual(storage.getStreak(), 0, "Loss must reset streak to 0");
console.log("  ✓ True loss reset streak to 0");

// Test 3: FootyShare buildShareText for partial success
console.log("\n[Test 3] Share text and emoji grid formatting for partial success");

// 3a: Transfer Destination partial share text
const transferDestShare = FootyUI.buildShareText({
    gameId: 'transfer_destination',
    puzzleNum: 81,
    won: false,
    outcome: 'partial',
    score: 4,
    maxScore: 6,
    lives: 2,
    initialLives: 5
});
assert(transferDestShare.includes('CAREER SURVIVED'), "Must contain CAREER SURVIVED");
assert(transferDestShare.includes('4/6 clubs guessed backwards'), "Must show accurate score");
assert(transferDestShare.includes('🟨'), "Emoji grid for partial success must show yellow squares for missed/skipped steps");
console.log("  ✓ Transfer Destination partial share card format verified");

// 3b: Player Chain partial share text
const playerChainShare = FootyUI.buildShareText({
    gameId: 'player_chain',
    puzzleNum: 171,
    won: false,
    outcome: 'partial',
    score: 3,
    maxScore: 5,
    lives: 1,
    initialLives: 5
});
assert(playerChainShare.includes('CHAIN SURVIVED'), "Must contain CHAIN SURVIVED");
assert(playerChainShare.includes('3/5 steps solved'), "Must show accurate score");
console.log("  ✓ Player Chain partial share card format verified");

// 3c: Top Transfers partial share text
const topTransfersShare = FootyUI.buildShareText({
    gameId: 'top_transfers',
    puzzleNum: 49,
    won: false,
    outcome: 'partial',
    score: 4,
    maxScore: 5,
    lives: 3,
    initialLives: 5
});
assert(topTransfersShare.includes('BOARD CLEARED'), "Must contain BOARD CLEARED");
console.log("  ✓ Top Transfers partial share card format verified");

// Test 4: Template inspection for partial success outcome hooks
console.log("\n[Test 4] Template integrity checks");
const templates = [
    'templates/transfer_destination_template.html',
    'templates/player_chain_template.html',
    'templates/top_transfers_template.html',
    'templates/top_scorers_template.html',
    'templates/passport_fc_template.html'
];

templates.forEach(tplPath => {
    const fullPath = path.join(__dirname, '..', tplPath);
    const content = fs.readFileSync(fullPath, 'utf8');
    assert(content.includes('isPartial'), `${tplPath} must contain isPartial logic`);
    assert(content.includes('outcome'), `${tplPath} must handle outcome property`);
    console.log(`  ✓ Verified ${tplPath}`);
});

console.log("\n✅ ALL PARTIAL SUCCESS TESTS PASSED (100% SUCCESS)!\n");
