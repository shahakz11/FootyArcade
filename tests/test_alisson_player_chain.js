const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log("=== Testing Player Match & Autocomplete Resolution (Alisson & Aliases) ===");

// 1. Mock DOM environment
function createMockElement(id, tagName = 'div') {
    const classes = new Set();
    const children = [];
    let text = '';
    const elementListeners = {};
    return {
        id,
        tagName,
        children,
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
        get innerHTML() { return ''; },
        set innerHTML(val) {
            if (val === '') {
                children.length = 0;
            }
        },
        value: '',
        focus: () => {},
        scrollIntoView: () => {},
        appendChild: (child) => children.push(child),
        insertBefore: (child, ref) => children.unshift(child),
        getAttribute: () => null,
        setAttribute: () => {},
        querySelector: (sel) => createMockElement('sub'),
        querySelectorAll: () => [],
        addEventListener: (evt, handler) => {
            elementListeners[evt] = handler;
        },
        removeEventListener: (evt) => {
            delete elementListeners[evt];
        },
        _trigger: (evt) => {
            if (elementListeners[evt]) elementListeners[evt]();
        },
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

global.window = {
    addEventListener: () => {},
    removeEventListener: () => {},
    localStorage: {
        getItem: () => null,
        setItem: () => {},
        removeItem: () => {}
    },
    location: {
        search: '',
        pathname: '/games/player_chain.html',
        href: 'http://localhost:3000/games/player_chain.html'
    }
};

global.document = {
    getElementById: (id) => getMockElement(id),
    createElement: (tag) => createMockElement(`dyn_${Math.random()}`, tag),
    querySelector: (sel) => createMockElement('sub'),
    querySelectorAll: (sel) => [],
    addEventListener: () => {},
    removeEventListener: () => {},
    body: createMockElement('body')
};

// 2. Load games/footy-ui.js
const footyUiCode = fs.readFileSync(path.join(__dirname, '..', 'games', 'footy-ui.js'), 'utf8');
eval(footyUiCode);

const FootyUI = global.window.FootyUI;
assert(FootyUI, "FootyUI must be exported on global window");

// 3. Test normalizeStr & isPlayerMatch
console.log("Test 1: normalizeStr handling of (All) and aliases");
assert.strictEqual(FootyUI.normalizeStr("Alisson (All)"), "alisson", "Must normalize 'Alisson (All)' to 'alisson'");
assert.strictEqual(FootyUI.normalizeStr("alisson"), "alisson", "Must normalize 'alisson' to 'alisson'");
assert.strictEqual(FootyUI.normalizeStr("Alisson (ALL)"), "alisson", "Must normalize 'Alisson (ALL)' to 'alisson'");
assert.strictEqual(FootyUI.normalizeStr("Pelé (All)"), "pele", "Must normalize 'Pelé (All)' to 'pele'");
assert.strictEqual(FootyUI.normalizeStr("Ronaldo (All)"), "ronaldo", "Must normalize 'Ronaldo (All)' to 'ronaldo'");
console.log("✓ normalizeStr handles (All) cleanly");

console.log("Test 2: isPlayerMatch comparisons");
assert(FootyUI.isPlayerMatch("Alisson (All)", "Alisson"), "'Alisson (All)' must match target 'Alisson'");
assert(FootyUI.isPlayerMatch("alisson", "Alisson"), "'alisson' must match target 'Alisson'");
assert(FootyUI.isPlayerMatch("Alisson", "Alisson (All)"), "'Alisson' must match 'Alisson (All)'");
assert(FootyUI.isPlayerMatch("alisson (all)", "Alisson"), "'alisson (all)' must match 'Alisson'");

const alissonObj = {
    Name: "Alisson (All)",
    Aliases: ["Alisson", "Alisson Becker", "Alisson Ramses Becker"]
};
assert(FootyUI.isPlayerMatch(alissonObj, "Alisson"), "Player object must match 'Alisson'");
assert(FootyUI.isPlayerMatch("Alisson Becker", alissonObj), "'Alisson Becker' must match player object with Aliases");
assert(FootyUI.isPlayerMatch(alissonObj, "Alisson Becker"), "Player object must match 'Alisson Becker'");
console.log("✓ isPlayerMatch handles string and object comparisons with aliases");

console.log("Test 3: Autocomplete Dropdown & Guess Resolution");
const samplePlayers = [
    alissonObj,
    { Name: "Alisson Santos", Nationality: "Brazil", Position: "Attack", MarketValue: 1000000 },
    { Name: "Ederson (All)", Aliases: ["Ederson", "Ederson Moraes"] },
    { Name: "Mohamed Salah", Nationality: "Egypt", Position: "Attack", MarketValue: 100000000 }
];

const input = getMockElement('guess-input');
const list = getMockElement('autocomplete-list');
const dropdown = new FootyUI.FootyDropdown({
    inputId: 'guess-input',
    listId: 'autocomplete-list',
    data: samplePlayers,
    labelFn: p => p.Name
});

// A. User types "alisson"
const rawGuessA = "alisson";
const normGuessA = FootyUI.normalizeStr(rawGuessA);
const selectedA = dropdown.getSelected(); // null because user didn't click
const matchedA = selectedA ? selectedA.Name : (
    samplePlayers.find(p => FootyUI.isPlayerMatch(p, rawGuessA) || FootyUI.normalizeStr(p.Name) === normGuessA)?.Name
    || (typeof dropdown.getTopMatch === 'function' ? dropdown.getTopMatch(rawGuessA)?.Name : null)
);

assert.strictEqual(matchedA, "Alisson (All)", "Must resolve 'alisson' to 'Alisson (All)'");

// B. User types "alisson (all)"
const rawGuessB = "alisson (all)";
const normGuessB = FootyUI.normalizeStr(rawGuessB);
const matchedB = selectedA ? selectedA.Name : (
    samplePlayers.find(p => FootyUI.isPlayerMatch(p, rawGuessB) || FootyUI.normalizeStr(p.Name) === normGuessB)?.Name
    || (typeof dropdown.getTopMatch === 'function' ? dropdown.getTopMatch(rawGuessB)?.Name : null)
);
assert.strictEqual(matchedB, "Alisson (All)", "Must resolve 'alisson (all)' to 'Alisson (All)'");

// C. Verify validation in Player Chain Step
const targetPlayer = "Alisson";
const validPlayersStep = ["Adriano", "Alisson", "Juan", "Juan Jesus"];

assert(FootyUI.isPlayerMatch(matchedA, targetPlayer), "Instant Win check must succeed for resolved guess");
assert(validPlayersStep.some(p => FootyUI.isPlayerMatch(matchedA, p)), "Step valid player check must succeed");

console.log("✓ Player chain guess resolution verified successfully!");
console.log("\n✅ ALL TESTS PASSED!");
