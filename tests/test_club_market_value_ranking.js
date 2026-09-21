const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log("=== Testing Club Market Value Autocomplete Prioritization ===");

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
    location: { href: 'https://playmaker.best/games/transfer_destination.html', pathname: '/games/transfer_destination.html', hostname: 'playmaker.best', search: '' },
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

// 3. Load actual all_clubs.json
const allClubsPath = path.join(__dirname, '../all_clubs.json');
assert(fs.existsSync(allClubsPath), "all_clubs.json must exist");
const allClubs = JSON.parse(fs.readFileSync(allClubsPath, 'utf8'));

console.log(`Loaded ${allClubs.length} clubs from all_clubs.json`);

// Verify that clubs have market_value
const clubsWithValue = allClubs.filter(c => typeof c === 'object' && c.market_value > 0);
console.log(`Clubs with positive market_value: ${clubsWithValue.length}`);
assert(clubsWithValue.length > 50, "Should have dozens of clubs with positive market valuation");

// 4. Helper function to emulate FootyDropdown searchAndRank
function searchAndRankClubs(query, data = allClubs, maxResults = 10) {
    const normQ = FootyUI.normalizeStr(query);
    if (!normQ) return [];

    const results = [];
    for (let i = 0; i < data.length; i++) {
        const item = data[i];
        const rawLabel = typeof item === 'object' && item ? item.name : String(item);
        const normLabel = FootyUI.normalizeStr(rawLabel);

        let matches = normLabel.includes(normQ);
        let matchedAlias = null;
        let aliasTier = 99;

        const aliases = (item && typeof item === 'object' && (item.Aliases || item.aliases || item.AltNames || item.alt_names)) || [];
        if (Array.isArray(aliases)) {
            for (let a of aliases) {
                const normA = FootyUI.normalizeStr(a);
                if (!normA) continue;
                if (normA === normQ || normA.split(/\s+/).some(w => w === normQ)) {
                    matches = true;
                    matchedAlias = a;
                    aliasTier = Math.min(aliasTier, 1);
                } else if (normA.startsWith(normQ) || normA.split(/\s+/).some(w => w.startsWith(normQ))) {
                    matches = true;
                    matchedAlias = a;
                    aliasTier = Math.min(aliasTier, 2);
                } else if (normA.includes(normQ)) {
                    matches = true;
                    matchedAlias = a;
                    aliasTier = Math.min(aliasTier, 3);
                }
            }
        }

        if (!matches) continue;

        let tier = 4;
        const words = normLabel.split(/\s+/);
        if (normLabel === normQ || words.some(w => w === normQ)) {
            tier = 1;
        } else if (normLabel.startsWith(normQ) || words.some(w => w.startsWith(normQ))) {
            tier = 2;
        } else if (normLabel.includes(normQ)) {
            tier = 3;
        } else if (matchedAlias) {
            tier = aliasTier <= 2 ? 2 : 3;
        }

        let value = 0;
        if (item && typeof item === 'object') {
            value = Number(item.MarketValue || item.market_value || item.highest_market_value || item.value || 0) || 0;
        }

        results.push({
            item,
            tier,
            value,
            len: normLabel.length,
            label: rawLabel,
            matchedAlias
        });
    }

    results.sort((a, b) => {
        if (a.tier !== b.tier) return a.tier - b.tier;
        if (b.value !== a.value) return b.value - a.value;
        if (a.len !== b.len) return a.len - b.len;
        return a.label.localeCompare(b.label);
    });

    return results.slice(0, maxResults);
}

// 5. Run test assertions on common club search prefixes
console.log("\n--- Testing Club Autocomplete Market Value Prioritization ---");

// Test: "real" -> Real Madrid should be #1
{
    const results = searchAndRankClubs("real");
    console.log("Query 'real' top 3:", results.slice(0, 3).map(r => `${r.label} (val: €${r.value.toLocaleString()})`));
    assert(results.length > 0, "Should return results for 'real'");
    assert.strictEqual(results[0].label, "Real Madrid", "Real Madrid must be ranked #1 for query 'real'");
}

// Test: "inter" -> Inter Milan or Inter should be #1
{
    const results = searchAndRankClubs("inter");
    console.log("Query 'inter' top 3:", results.slice(0, 3).map(r => `${r.label} (val: €${r.value.toLocaleString()})`));
    assert(results.length > 0, "Should return results for 'inter'");
    const topLabels = results.slice(0, 2).map(r => r.label);
    assert(topLabels.includes("Inter Milan") || topLabels.includes("Inter"), "Inter Milan must be in top ranks for 'inter'");
}

// Test: "city" -> Manchester City should be #1
{
    const results = searchAndRankClubs("city");
    console.log("Query 'city' top 3:", results.slice(0, 3).map(r => `${r.label} (val: €${r.value.toLocaleString()})`));
    assert(results.length > 0, "Should return results for 'city'");
    assert.strictEqual(results[0].label, "Manchester City", "Manchester City must be ranked #1 for query 'city'");
}

// Test: "united" -> Manchester United should be #1
{
    const results = searchAndRankClubs("united");
    console.log("Query 'united' top 3:", results.slice(0, 3).map(r => `${r.label} (val: €${r.value.toLocaleString()})`));
    assert(results.length > 0, "Should return results for 'united'");
    assert.strictEqual(results[0].label, "Manchester United", "Manchester United must be ranked #1 for query 'united'");
}

// Test: "arsenal" -> Arsenal / Arsenal FC should be #1
{
    const results = searchAndRankClubs("arsenal");
    console.log("Query 'arsenal' top 3:", results.slice(0, 3).map(r => `${r.label} (val: €${r.value.toLocaleString()})`));
    assert(results.length > 0, "Should return results for 'arsenal'");
    assert(results[0].label.startsWith("Arsenal"), "Arsenal must be ranked #1 for query 'arsenal'");
}

// Test: "bayern" -> Bayern Munich should be #1
{
    const results = searchAndRankClubs("bayern");
    console.log("Query 'bayern' top 3:", results.slice(0, 3).map(r => `${r.label} (val: €${r.value.toLocaleString()})`));
    assert(results.length > 0, "Should return results for 'bayern'");
    assert(results[0].label.includes("Bayern"), "Bayern Munich must be ranked #1 for query 'bayern'");
}

// Test: "milan" -> AC Milan or Inter Milan in top 2
{
    const results = searchAndRankClubs("milan");
    console.log("Query 'milan' top 3:", results.slice(0, 3).map(r => `${r.label} (val: €${r.value.toLocaleString()})`));
    assert(results.length > 0, "Should return results for 'milan'");
    const topTwo = results.slice(0, 2).map(r => r.label);
    assert(topTwo.includes("AC Milan") || topTwo.includes("Inter Milan") || topTwo.includes("Milan"), "AC Milan or Inter Milan must be in top 2 for 'milan'");
}

console.log("\n✅ All club market value prioritization tests PASSED!");
