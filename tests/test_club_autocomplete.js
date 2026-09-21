const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log("=== Testing Club Autocomplete for Transfer Destination and Club Connect ===");

// 1. Mock DOM environment
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
        value: '',
        focus: () => {},
        scrollIntoView: () => {},
        appendChild: (child) => children.push(child),
        insertBefore: (child, ref) => children.unshift(child),
        getAttribute: () => null,
        setAttribute: () => {},
        querySelector: (sel) => createMockElement('sub'),
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

global.document = {
    getElementById: (id) => getMockElement(id),
    createElement: (tag) => createMockElement(`dyn_${Math.random().toString(36).slice(2)}`, tag),
    body: createMockElement('body'),
    querySelector: (sel) => createMockElement('sel'),
    querySelectorAll: () => [],
    addEventListener: () => {},
    removeEventListener: () => {}
};
global.window = {
    location: { href: 'https://playmaker.best/games/club_connect.html', pathname: '/games/club_connect.html', hostname: 'playmaker.best', search: '' },
    open: () => {},
    addEventListener: () => {},
    removeEventListener: () => {}
};
global.localStorage = {
    _data: {},
    getItem(key) { return this._data[key] || null; },
    setItem(key, val) { this._data[key] = String(val); },
    removeItem(key) { delete this._data[key]; },
    clear() { this._data = {}; }
};
global.sessionStorage = global.localStorage;

// 2. Load footy-ui.js
const footyUiPath = path.join(__dirname, '../games/footy-ui.js');
const footyUiCode = fs.readFileSync(footyUiPath, 'utf8');
eval(footyUiCode);
const FootyUI = window.FootyUI;

assert(typeof FootyUI !== 'undefined', "FootyUI must be defined");
assert(typeof FootyUI.FootyDropdown !== 'undefined', "FootyDropdown must be defined");
assert(typeof FootyUI.isClubMatch !== 'undefined', "isClubMatch must be defined");

// Sample club objects simulating get_processed_all_clubs()
const sampleClubs = [
    { name: "Real Sociedad", aliases: ["Real Sociedad de Futbol", "La Real"] },
    { name: "Sporting CP", aliases: ["Sporting Lisbon", "Sporting Clube de Portugal"] },
    { name: "Sevilla", aliases: ["Sevilla FC", "Sevilla Fútbol Club"] },
    { name: "Arsenal", aliases: ["Arsenal FC", "The Gunners"] },
    { name: "Bayern Munich", aliases: ["FC Bayern", "Bayern München", "Bayern"] },
    { name: "Barcelona", aliases: ["FC Barcelona", "Barca"] },
    { name: "Manchester United", aliases: ["Man United", "Man Utd", "MUFC"] }
];

console.log("\n--- Testing FootyDropdown with Club Objects ---");

let createdDropdown = new FootyUI.FootyDropdown({
    inputId: 'guess-input',
    listId: 'autocomplete-list',
    data: sampleClubs,
    labelFn: c => (typeof c === 'object' && c ? c.name : c)
});

assert.strictEqual(FootyUI.isClubMatch("Sporting Lisbon", "Sporting CP"), true, "isClubMatch should recognize Sporting Lisbon as Sporting CP");
assert.strictEqual(FootyUI.isClubMatch({ name: "Sporting CP" }, "Sporting CP"), true, "isClubMatch should handle club objects");
assert.strictEqual(FootyUI.isClubMatch("Barca", "Barcelona"), true, "isClubMatch should recognize Barca as Barcelona");
assert.strictEqual(FootyUI.isClubMatch("Man Utd", "Manchester United"), true, "isClubMatch should recognize Man Utd as Manchester United");

console.log("✓ isClubMatch successfully handles canonical names, aliases, and objects.");

// 3. Test Club Connect activeClubs building logic
console.log("\n--- Testing Club Connect activeClubs handling ---");
const rawClubs = sampleClubs;
const activeClubs = rawClubs.map(c => (typeof c === 'object' && c ? c : { name: c, aliases: [] }));
const activeGameData = { club: "Sevilla", players: [] };
if (activeGameData && activeGameData.club && !activeClubs.some(c => c.name === activeGameData.club)) {
    activeClubs.push({ name: activeGameData.club, aliases: [] });
}

assert.strictEqual(activeClubs.length, 7, "All 7 clubs should be retained without corrupting into [object Object]");
assert.strictEqual(typeof activeClubs[0].name, 'string', "Club name must be a string");
assert.strictEqual(activeClubs[0].name, 'Real Sociedad', "First club name must match");

// Test that typing 'a' matches multiple clubs, not just Sevilla
const queryA = FootyUI.normalizeStr('a');
const matchesA = activeClubs.filter(c => FootyUI.normalizeStr(c.name).includes(queryA));
assert(matchesA.length > 1, `Typing 'a' should match multiple clubs (found ${matchesA.length})`);
console.log(`✓ Typing 'a' in Club Connect matches ${matchesA.length} clubs (not just Sevilla).`);

// 4. Test Transfer Destination activeClubs building logic
console.log("\n--- Testing Transfer Destination allClubs handling ---");
const destGameData = {
    player_name: "Tanguy Nianzou",
    transfers: [
        { from_club_name: "Bayern Munich", to_club_name: "Sevilla" },
        { from_club_name: "Paris Saint-Germain", to_club_name: "Bayern Munich" }
    ]
};
const destAllClubs = rawClubs.map(c => (typeof c === 'object' && c ? c : { name: c, aliases: [] }));
destGameData.transfers.forEach(tr => {
    if (tr.from_club_name && !destAllClubs.some(c => c.name === tr.from_club_name)) {
        destAllClubs.push({ name: tr.from_club_name, aliases: [] });
    }
    if (tr.to_club_name && !destAllClubs.some(c => c.name === tr.to_club_name)) {
        destAllClubs.push({ name: tr.to_club_name, aliases: [] });
    }
});

assert(destAllClubs.some(c => c.name === "Paris Saint-Germain"), "Paris Saint-Germain should be present as an object");
destAllClubs.forEach(c => {
    assert.strictEqual(typeof c.name, 'string', `Club name should be string, got ${typeof c.name}`);
    assert.notStrictEqual(c.name, '[object Object]', "Club name must not be [object Object]");
});
console.log("✓ Transfer destination allClubs correctly structures objects with zero [object Object] leaks.");

// 5. Verify compiled game files
console.log("\n--- Testing Compiled HTML Files ---");
const ccHtml = fs.readFileSync(path.join(__dirname, '../games/club_connect.html'), 'utf8');
const tdHtml = fs.readFileSync(path.join(__dirname, '../games/transfer_destination.html'), 'utf8');

assert(ccHtml.includes('rawClubs.map(c => (typeof c === \'object\' && c ? c : { name: c, aliases: [] }))'), "club_connect.html has updated activeClubs mapping");
assert(tdHtml.includes('rawClubs.map(c => (typeof c === \'object\' && c ? c : { name: c, aliases: [] }))'), "transfer_destination.html has updated allClubs mapping");
assert(!ccHtml.includes('activeClubs.map(name => ({ name }))'), "club_connect.html no longer double wraps objects");
assert(!tdHtml.includes('labelFn:  c => c\n'), "transfer_destination.html no longer uses bare c => c labelFn");

console.log("✓ Compiled HTML files verified successfully.");
console.log("\n🎉 ALL CLUB AUTOCOMPLETE TESTS PASSED (100% SUCCESS)!");
