/**
 * tests/test_cookie_consent.js — Test suite for GDPR Cookie Consent Banner & Google Consent Mode v2
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

// Mock localStorage
const mockStorage = {};
global.localStorage = {
    getItem: (k) => mockStorage[k] || null,
    setItem: (k, v) => { mockStorage[k] = String(v); },
    removeItem: (k) => { delete mockStorage[k]; },
    clear: () => { Object.keys(mockStorage).forEach(k => delete mockStorage[k]); }
};

// Mock DOM
function createMockElement(tag, id = '', className = '') {
    const el = {
        tagName: tag.toUpperCase(),
        id,
        className,
        innerHTML: '',
        style: {},
        attributes: {},
        listeners: {},
        children: [],
        appendChild: function(child) {
            this.children.push(child);
            return child;
        },
        getAttribute: function(name) { return this.attributes[name] || null; },
        setAttribute: function(name, val) { this.attributes[name] = val; },
        querySelector: function(sel) { return createMockElement('div'); },
        querySelectorAll: function(sel) { return []; },
        addEventListener: function(event, handler) {
            if (!this.listeners[event]) this.listeners[event] = [];
            this.listeners[event].push(handler);
        },
        removeEventListener: function(event, handler) {
            if (!this.listeners[event]) return;
            this.listeners[event] = this.listeners[event].filter(h => h !== handler);
        },
        click: function() {
            if (this.listeners['click']) {
                this.listeners['click'].forEach(h => h({ preventDefault: () => {} }));
            }
        },
        remove: function() {
            if (global.document.body.children.includes(this)) {
                global.document.body.children = global.document.body.children.filter(c => c !== this);
            }
        }
    };
    return el;
}

global.document = {
    readyState: 'complete',
    head: { appendChild: () => {} },
    body: {
        children: [],
        appendChild: function(el) {
            this.children.push(el);
            return el;
        }
    },
    createElement: function(tag) {
        return createMockElement(tag);
    },
    getElementById: function(id) {
        const search = (children) => {
            for (const child of children) {
                if (child.id === id) return child;
                if (child.innerHTML && child.innerHTML.includes(`id="${id}"`)) {
                    // Quick simulated innerHTML element lookup
                    return createMockElement('div', id);
                }
            }
            return null;
        };
        return search(this.body.children);
    },
    querySelector: function(sel) { return null; },
    querySelectorAll: function(sel) {
        if (sel === '[data-action="open-cookie-settings"]') {
            const btn = createMockElement('a');
            btn.setAttribute('data-action', 'open-cookie-settings');
            return [btn];
        }
        return [];
    },
    addEventListener: () => {}
};

global.window = {
    location: { pathname: '/index.html' },
    addEventListener: () => {}
};

// Mock dataLayer & gtag
const gtagCalls = [];
global.dataLayer = [];
global.gtag = function(...args) {
    gtagCalls.push(args);
};
global.window.gtag = global.gtag;

// Load footy-i18n.js
const i18nCode = fs.readFileSync(path.join(__dirname, '../games/footy-i18n.js'), 'utf8');
eval(i18nCode);
const FootyI18n = global.window.FootyI18n;

// Load footy-ui.js
const footyUiCode = fs.readFileSync(path.join(__dirname, '../games/footy-ui.js'), 'utf8');
eval(footyUiCode);
const FootyUI = global.window.FootyUI;

console.log('=== Running GDPR Cookie Consent & Google Consent Mode v2 Tests ===\n');

// Test 1: Fresh visitor has null consent
localStorage.clear();
const initialConsent = FootyUI.FootyConsent.getConsent();
assert.strictEqual(initialConsent, null, 'Fresh visitor should return null consent');
console.log('✓ Test 1 Passed: Fresh visitor returns null consent');

// Test 2: Saving "granted" sets localStorage & updates gtag
gtagCalls.length = 0;
FootyUI.FootyConsent.setConsent('granted');
assert.strictEqual(localStorage.getItem('playmaker_cookie_consent'), 'granted');
assert.strictEqual(localStorage.getItem('footy_consent'), 'accepted');
assert.strictEqual(FootyUI.FootyConsent.getConsent(), 'granted');

const consentUpdateGranted = gtagCalls.find(c => c[0] === 'consent' && c[1] === 'update');
assert.ok(consentUpdateGranted, 'gtag consent update must be called');
assert.strictEqual(consentUpdateGranted[2].analytics_storage, 'granted');
assert.strictEqual(consentUpdateGranted[2].ad_storage, 'granted');
console.log('✓ Test 2 Passed: setConsent("granted") updates storage and dispatches gtag granted signals');

// Test 3: Saving "denied" sets localStorage & updates gtag
gtagCalls.length = 0;
FootyUI.FootyConsent.setConsent('denied');
assert.strictEqual(localStorage.getItem('playmaker_cookie_consent'), 'denied');
assert.strictEqual(localStorage.getItem('footy_consent'), 'declined');
assert.strictEqual(FootyUI.FootyConsent.getConsent(), 'denied');

const consentUpdateDenied = gtagCalls.find(c => c[0] === 'consent' && c[1] === 'update');
assert.ok(consentUpdateDenied, 'gtag consent update must be called');
assert.strictEqual(consentUpdateDenied[2].analytics_storage, 'denied');
assert.strictEqual(consentUpdateDenied[2].ad_storage, 'denied');
console.log('✓ Test 3 Passed: setConsent("denied") updates storage and dispatches gtag denied signals');

// Test 4: Migration of legacy footy_consent keys
localStorage.clear();
localStorage.setItem('footy_consent', 'accepted');
assert.strictEqual(FootyUI.FootyConsent.getConsent(), 'granted');
assert.strictEqual(localStorage.getItem('playmaker_cookie_consent'), 'granted');

localStorage.clear();
localStorage.setItem('footy_consent', 'declined');
assert.strictEqual(FootyUI.FootyConsent.getConsent(), 'denied');
assert.strictEqual(localStorage.getItem('playmaker_cookie_consent'), 'denied');
console.log('✓ Test 4 Passed: Legacy footy_consent is transparently migrated to Consent Mode v2');

// Test 5: i18n Translation completeness
const enTitle = FootyI18n.t('cookie_consent_title');
const enAccept = FootyI18n.t('cookie_consent_accept');
const enDecline = FootyI18n.t('cookie_consent_decline');
assert.ok(enTitle && enAccept && enDecline, 'English translation tokens must be populated');

FootyI18n.setLang('es');
const esTitle = FootyI18n.t('cookie_consent_title');
const esAccept = FootyI18n.t('cookie_consent_accept');
const esDecline = FootyI18n.t('cookie_consent_decline');
assert.ok(esTitle && esAccept && esDecline, 'Spanish translation tokens must be populated');
assert.strictEqual(esAccept, 'ACEPTAR TODO');
assert.strictEqual(esDecline, 'RECHAZAR');
console.log('✓ Test 5 Passed: Bilingual i18n dictionary supports cookie consent and settings copy');

// Test 6: Verify index.html & es/index.html & templates contain Consent Mode v2 snippet
const indexHtml = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
const esIndexHtml = fs.readFileSync(path.join(__dirname, '../es/index.html'), 'utf8');
const privacyHtml = fs.readFileSync(path.join(__dirname, '../privacy.html'), 'utf8');
const termsHtml = fs.readFileSync(path.join(__dirname, '../terms.html'), 'utf8');

assert.ok(indexHtml.includes("gtag('consent', 'default'"), 'index.html must include consent default');
assert.ok(indexHtml.includes('data-action="open-cookie-settings"'), 'index.html footer must have cookie settings link');

assert.ok(esIndexHtml.includes("gtag('consent', 'default'"), 'es/index.html must include consent default');
assert.ok(esIndexHtml.includes('data-action="open-cookie-settings"'), 'es/index.html footer must have cookie settings link');

assert.ok(privacyHtml.includes("gtag('consent', 'default'"), 'privacy.html must include consent default');
assert.ok(privacyHtml.includes('data-action="open-cookie-settings"'), 'privacy.html footer must have cookie settings link');

assert.ok(termsHtml.includes("gtag('consent', 'default'"), 'terms.html must include consent default');
assert.ok(termsHtml.includes('data-action="open-cookie-settings"'), 'terms.html footer must have cookie settings link');
console.log('✓ Test 6 Passed: Main static pages contain Consent Mode v2 default setup & footer triggers');

// Test 7: Verify all 7 compiled daily games in English and Spanish contain Consent Mode v2
const games = ['top_transfers', 'top_scorers', 'club_connect', 'transfer_destination', 'player_chain', 'played_with', 'passport_fc'];
for (const g of games) {
    const enGameHtml = fs.readFileSync(path.join(__dirname, `../games/${g}.html`), 'utf8');
    const esGameHtml = fs.readFileSync(path.join(__dirname, `../es/games/${g}.html`), 'utf8');
    
    assert.ok(enGameHtml.includes("gtag('consent', 'default'"), `games/${g}.html must include consent default`);
    assert.ok(enGameHtml.includes('data-action="open-cookie-settings"'), `games/${g}.html must include cookie settings link`);
    
    assert.ok(esGameHtml.includes("gtag('consent', 'default'"), `es/games/${g}.html must include consent default`);
    assert.ok(esGameHtml.includes('data-action="open-cookie-settings"'), `es/games/${g}.html must include cookie settings link`);
}
console.log('✓ Test 7 Passed: All 7 daily games across EN and ES contain Consent Mode v2 & footer trigger');

console.log('\n🎉 ALL 7 GDPR COOKIE CONSENT & GOOGLE CONSENT MODE V2 TESTS PASSED!\n');
