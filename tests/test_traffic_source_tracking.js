/**
 * Unit tests for Traffic Source collection & Events Sheet mapping.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

function createMockElement(id = 'elem', tagName = 'div') {
    const classes = new Set();
    const children = [];
    return {
        id,
        tagName,
        style: {},
        classList: {
            add: (...cls) => cls.forEach(c => classes.add(c)),
            remove: (...cls) => cls.forEach(c => classes.delete(c)),
            contains: (c) => classes.has(c)
        },
        innerHTML: '',
        textContent: '',
        appendChild: (child) => children.push(child),
        querySelector: (sel) => createMockElement(sel),
        querySelectorAll: () => [],
        getAttribute: () => null,
        setAttribute: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        remove: () => {}
    };
}

// Mock browser environment
function createMockWindow(url = 'https://playmaker.best/games/top_transfers.html', referrer = '') {
    const sessionStorageStore = {};
    const localStorageStore = {};

    const parsedUrl = new URL(url);

    const mockDoc = {
        referrer: referrer,
        getElementById: (id) => createMockElement(id),
        querySelector: (sel) => createMockElement(sel),
        querySelectorAll: () => [],
        addEventListener: () => {},
        readyState: 'complete',
        createElement: (tag) => createMockElement(tag, tag),
        body: createMockElement('body', 'body')
    };

    const mockWin = {
        location: {
            href: url,
            hostname: parsedUrl.hostname,
            pathname: parsedUrl.pathname,
            search: parsedUrl.search
        },
        document: mockDoc,
        sessionStorage: {
            getItem: (k) => sessionStorageStore[k] || null,
            setItem: (k, v) => { sessionStorageStore[k] = String(v); },
            removeItem: (k) => { delete sessionStorageStore[k]; },
            clear: () => { Object.keys(sessionStorageStore).forEach(k => delete sessionStorageStore[k]); }
        },
        localStorage: {
            getItem: (k) => localStorageStore[k] || null,
            setItem: (k, v) => { localStorageStore[k] = String(v); },
            removeItem: (k) => { delete localStorageStore[k]; }
        },
        fetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
        navigator: {
            clipboard: { writeText: () => Promise.resolve() },
            userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
        },
        addEventListener: () => {},
        removeEventListener: () => {},
        URL: URL,
        URLSearchParams: URLSearchParams,
        console: console,
        Date: Date,
        Math: Math,
        JSON: JSON,
        crypto: {
            randomUUID: () => '11111111-2222-3333-4444-555555555555'
        }
    };

    mockDoc.defaultView = mockWin;
    mockWin.window = mockWin;
    mockWin.global = mockWin;

    return { mockWin, sessionStorageStore };
}

// Load and evaluate footy-ui.js in a mocked context
function loadFootyUI(mockWin) {
    const code = fs.readFileSync(path.join(__dirname, '../games/footy-ui.js'), 'utf8');
    const context = vm.createContext(mockWin);
    vm.runInContext(code, context);
    return mockWin.FootyUI;
}

console.log("▶ Running Traffic Source Tracking & Analytics Tests...");

// Test 1: Query param utm_source (e.g. utm_source=instagram)
{
    const { mockWin } = createMockWindow('https://playmaker.best/games/top_transfers.html?utm_source=instagram');
    const FootyUI = loadFootyUI(mockWin);
    assert.strictEqual(FootyUI.getUrlSource(), 'instagram', 'Should extract utm_source=instagram');
    console.log("  ✓ Extracts utm_source=instagram from query params");
}

// Test 2: Query param ref (e.g. ref=tiktok)
{
    const { mockWin } = createMockWindow('https://playmaker.best/games/top_transfers.html?ref=tiktok');
    const FootyUI = loadFootyUI(mockWin);
    assert.strictEqual(FootyUI.getUrlSource(), 'tiktok', 'Should extract ref=tiktok');
    console.log("  ✓ Extracts ref=tiktok from query params");
}

// Test 3: Query param source (e.g. source=youtube)
{
    const { mockWin } = createMockWindow('https://playmaker.best/games/top_transfers.html?source=youtube');
    const FootyUI = loadFootyUI(mockWin);
    assert.strictEqual(FootyUI.getUrlSource(), 'youtube', 'Should extract source=youtube');
    console.log("  ✓ Extracts source=youtube from query params");
}

// Test 4: Referrer from Google (e.g. https://www.google.com/)
{
    const { mockWin } = createMockWindow('https://playmaker.best/games/top_transfers.html', 'https://www.google.com/search?q=playmaker+football');
    const FootyUI = loadFootyUI(mockWin);
    assert.strictEqual(FootyUI.getUrlSource(), 'google', 'Should detect google from referrer');
    console.log("  ✓ Detects google from document.referrer");
}

// Test 5: Referrer from Google International (e.g. https://www.google.co.uk/)
{
    const { mockWin } = createMockWindow('https://playmaker.best/games/top_transfers.html', 'https://www.google.co.uk/');
    const FootyUI = loadFootyUI(mockWin);
    assert.strictEqual(FootyUI.getUrlSource(), 'google', 'Should detect google from google.co.uk referrer');
    console.log("  ✓ Detects google from google.co.uk referrer");
}

// Test 6: Referrer from TikTok (e.g. https://www.tiktok.com/)
{
    const { mockWin } = createMockWindow('https://playmaker.best/games/top_transfers.html', 'https://www.tiktok.com/@playmaker.best');
    const FootyUI = loadFootyUI(mockWin);
    assert.strictEqual(FootyUI.getUrlSource(), 'tiktok', 'Should detect tiktok from referrer');
    console.log("  ✓ Detects tiktok from document.referrer");
}

// Test 7: Referrer from YouTube (e.g. https://www.youtube.com/)
{
    const { mockWin } = createMockWindow('https://playmaker.best/games/top_transfers.html', 'https://www.youtube.com/@best.playmaker');
    const FootyUI = loadFootyUI(mockWin);
    assert.strictEqual(FootyUI.getUrlSource(), 'youtube', 'Should detect youtube from referrer');
    console.log("  ✓ Detects youtube from document.referrer");
}

// Test 8: Referrer from Instagram (e.g. https://l.instagram.com/)
{
    const { mockWin } = createMockWindow('https://playmaker.best/games/top_transfers.html', 'https://l.instagram.com/');
    const FootyUI = loadFootyUI(mockWin);
    assert.strictEqual(FootyUI.getUrlSource(), 'instagram', 'Should detect instagram from referrer');
    console.log("  ✓ Detects instagram from document.referrer");
}

// Test 9: Ad click IDs (e.g. gclid, ttclid)
{
    const { mockWin: winGoogleAds } = createMockWindow('https://playmaker.best/games/top_transfers.html?gclid=xyz123');
    const FootyUI1 = loadFootyUI(winGoogleAds);
    assert.strictEqual(FootyUI1.getUrlSource(), 'google_ads', 'Should detect google_ads from gclid');

    const { mockWin: winTiktokAds } = createMockWindow('https://playmaker.best/games/top_transfers.html?ttclid=abc456');
    const FootyUI2 = loadFootyUI(winTiktokAds);
    assert.strictEqual(FootyUI2.getUrlSource(), 'tiktok', 'Should detect tiktok from ttclid');
    console.log("  ✓ Detects ad platform click IDs (gclid, ttclid)");
}

// Test 10: Session persistence across pages
{
    const { mockWin } = createMockWindow('https://playmaker.best/games/top_transfers.html?utm_source=tiktok');
    const FootyUI = loadFootyUI(mockWin);
    assert.strictEqual(FootyUI.getUrlSource(), 'tiktok');

    // Simulate navigating to another page without URL parameters or referrer
    mockWin.location.href = 'https://playmaker.best/games/passport_fc.html';
    mockWin.location.search = '';
    mockWin.document.referrer = 'https://playmaker.best/games/top_transfers.html';
    assert.strictEqual(FootyUI.getUrlSource(), 'tiktok', 'Session storage should persist traffic source across navigation');
    console.log("  ✓ Persists traffic source across page navigation via sessionStorage");
}

// Test 11: Google Apps Script buildEventsRow mapping
{
    const gasCode = fs.readFileSync(path.join(__dirname, '../google-apps-script.js'), 'utf8');
    const gasContext = vm.createContext({
        console: console,
        Date: Date
    });
    vm.runInContext(gasCode + '\nthis.buildEventsRow = buildEventsRow;\nthis.ensureEventsHeaders = ensureEventsHeaders;', gasContext);

    const headers = [
        'Timestamp',
        'Event Name',
        'Game ID',
        'Puzzle Number',
        'Puzzle ID',
        'Score',
        'Max Score',
        'Lives Left',
        'Won',
        'Is Correct',
        'Guess',
        'Step',
        'Target',
        'Extra Details',
        'URL',
        'Visitor ID',
        'Session ID',
        'URL Source'
    ];

    const payload = {
        eventName: 'guess',
        gameId: 'top_transfers',
        puzzleNum: 234,
        puzzleId: 'tt_234',
        score: 3,
        maxScore: 10,
        lives: 2,
        won: false,
        isCorrect: true,
        guess: 'Erling Haaland',
        step: 1,
        target: 'Manchester City',
        extraDetails: 'source: tiktok',
        url: 'https://playmaker.best/games/top_transfers.html',
        visitorId: 'v_123',
        sessionId: 's_456',
        urlSource: 'tiktok',
        source: 'tiktok'
    };

    const row = gasContext.buildEventsRow(headers, payload, '2026-09-23T18:00:00.000Z');
    const urlSourceIndex = headers.indexOf('URL Source');
    assert.strictEqual(row[urlSourceIndex], 'tiktok', 'GAS buildEventsRow should populate URL Source column with tiktok');

    // Also test alternate column name: "Traffic Source" or "Source"
    const altHeaders = ['Timestamp', 'Event Name', 'Traffic Source'];
    const altRow = gasContext.buildEventsRow(altHeaders, payload, '2026-09-23T18:00:00.000Z');
    assert.strictEqual(altRow[2], 'tiktok', 'GAS buildEventsRow should populate Traffic Source column');

    console.log("  ✓ GAS buildEventsRow correctly maps traffic source to URL Source / Traffic Source column");
}

console.log("\n🎉 ALL TRAFFIC SOURCE & EVENTS SHEET TESTS PASSED!\n");
