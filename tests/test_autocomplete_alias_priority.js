const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log("=== Testing Autocomplete Alias Priority & Bracket Suppression (Task #46) ===");

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
        pathname: '/games/top_transfers.html',
        href: 'http://localhost:3000/games/top_transfers.html'
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

// 2. Evaluate games/footy-ui.js
const footyUiCode = fs.readFileSync(path.join(__dirname, '..', 'games', 'footy-ui.js'), 'utf8');
eval(footyUiCode);

const FootyUI = global.window.FootyUI;
assert(FootyUI, "FootyUI must be exported on global window");
assert(FootyUI.FootyDropdown, "FootyDropdown must exist");

// 3. Test dataset
const samplePlayers = [
    {
        Name: "Fernandinho (All)",
        Nationality: "",
        Position: "",
        MarketValue: 0,
        Aliases: [
            "Fernandinho",
            "Fernando Luiz Roza",
            "Édis Baise / Fernandinho",
            "Fernando Silva dos Santos"
        ]
    },
    {
        Name: "Fernando",
        Nationality: "Brazil",
        Position: "Midfielder",
        MarketValue: 5000000
    },
    {
        Name: "Fernando Torres",
        Nationality: "Spain",
        Position: "Forward",
        MarketValue: 20000000
    },
    {
        Name: "Rafinha (All)",
        Nationality: "",
        Position: "",
        MarketValue: 0,
        Aliases: [
            "Rafinha",
            "Rafael Alcântara",
            "Márcio Rafael Ferreira de Souza"
        ]
    },
    {
        Name: "Raphinha",
        Nationality: "Brazil",
        Position: "Forward",
        MarketValue: 60000000
    }
];

const sampleClubs = [
    {
        name: "Barcelona",
        market_value: 900000000,
        aliases: [
            "Barcelona Atl",
            "FC Barcelona",
            "Futbol Barcelona",
            "Barça"
        ]
    },
    {
        name: "Barcelona SC",
        market_value: 15000000,
        aliases: []
    },
    {
        name: "Barco",
        market_value: 100000,
        aliases: []
    }
];

async function runTests() {
    // Helper to simulate typed input and wait for 60ms debounce
    const typeAndSearch = (inputElem, text) => {
        inputElem.value = text;
        inputElem._trigger('input');
        return new Promise(resolve => setTimeout(resolve, 80));
    };

    // Test 1: Query 'fernandinho' must rank 'Fernandinho (All)' at #1 (Tier 1)
    console.log("Test 1: Query 'fernandinho' priority for 'Fernandinho (All)'");
    const playerInput = getMockElement('test-player-input');
    const playerList = getMockElement('test-player-list');

    const playerDropdown = new FootyUI.FootyDropdown({
        inputId: 'test-player-input',
        listId: 'test-player-list',
        data: samplePlayers,
        labelFn: p => p.Name,
        badgeFn: p => {
            if (!p || (p.Name && /\(all\)$/i.test(p.Name))) return '';
            return `${p.Nationality || ''}${p.Position ? ' · ' + p.Position : ''}`;
        },
        onSelect: p => {}
    });

    await typeAndSearch(playerInput, 'fernandinho');

    assert(playerList.children.length > 0, "Dropdown should have rendered rows");
    const firstRow = playerList.children[0];
    const firstRowLabel = firstRow.children.find(c => c.tagName === 'span' && !c.className.includes('fa-row-badge'));

    assert.strictEqual(firstRowLabel.textContent, 'Fernandinho (All)', "First result must be 'Fernandinho (All)'");

    // Verify NO bracketed alias hints were appended
    const hasBracketedHint = firstRow.children.some(c => c.className && c.className.includes('text-amber-400'));
    assert.strictEqual(hasBracketedHint, false, "Must NOT contain amber bracketed alias hint");

    // Verify NO position/country badge was appended for (All) alias
    const hasBadge = firstRow.children.some(c => c.className && c.className.includes('fa-row-badge'));
    assert.strictEqual(hasBadge, false, "Must NOT contain position/country badge for alias entry");
    console.log("✓ 'Fernandinho (All)' is ranked #1 with clean display (no brackets, no badge)");

    // Test 2: Query 'barcel' for clubs
    console.log("Test 2: Query 'barcel' for 'Barcelona'");
    const clubInput = getMockElement('test-club-input');
    const clubList = getMockElement('test-club-list');

    const clubDropdown = new FootyUI.FootyDropdown({
        inputId: 'test-club-input',
        listId: 'test-club-list',
        data: sampleClubs,
        labelFn: c => c.name,
        onSelect: c => {}
    });

    await typeAndSearch(clubInput, 'barcel');

    assert(clubList.children.length > 0, "Club dropdown should render rows");
    const firstClubRow = clubList.children[0];
    const firstClubLabel = firstClubRow.children.find(c => c.tagName === 'span');
    assert.strictEqual(firstClubLabel.textContent, 'Barcelona', "First club must be 'Barcelona'");

    const clubHasBracketedHint = firstClubRow.children.some(c => c.className && c.className.includes('text-amber-400'));
    assert.strictEqual(clubHasBracketedHint, false, "Club dropdown must NOT contain bracketed alias hint");
    console.log("✓ 'Barcelona' ranked #1 without bracketed alias hint");

    // Test 3: Query 'rafinha'
    console.log("Test 3: Query 'rafinha'");
    await typeAndSearch(playerInput, 'rafinha');

    assert(playerList.children.length > 0, "Should render Rafinha rows");
    const firstRafinhaRow = playerList.children[0];
    const firstRafinhaLabel = firstRafinhaRow.children.find(c => c.tagName === 'span' && !c.className.includes('fa-row-badge'));
    assert.strictEqual(firstRafinhaLabel.textContent, 'Rafinha (All)', "First result must be 'Rafinha (All)'");
    console.log("✓ 'Rafinha (All)' ranked #1 for exact query 'rafinha'");

    console.log("\n✅ All autocomplete alias priority & bracket suppression tests PASSED!");
}

runTests().catch(err => {
    console.error(err);
    process.exit(1);
});
