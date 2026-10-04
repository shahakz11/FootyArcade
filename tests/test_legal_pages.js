/**
 * Test Suite: Legal Disclosures & Compliance Verification (Task #50)
 * Validates privacy.html and terms.html content, script setups,
 * Google Consent Mode v2, and nominative fair use disclaimers.
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log("=== Running Legal Disclosures & Compliance Tests ===");

const privacyPath = path.join(__dirname, '..', 'privacy.html');
const termsPath = path.join(__dirname, '..', 'terms.html');

assert(fs.existsSync(privacyPath), "privacy.html must exist in project root");
assert(fs.existsSync(termsPath), "terms.html must exist in project root");

const privacyHtml = fs.readFileSync(privacyPath, 'utf8');
const termsHtml = fs.readFileSync(termsPath, 'utf8');

// 1. Google Consent Mode v2 Header Script Verification
console.log("\n[1] Verifying Consent Mode v2 Head Scripts...");
assert(privacyHtml.includes('G-8BC1041NX3'), "privacy.html head script must include measurement tag");
assert(termsHtml.includes('G-8BC1041NX3'), "terms.html head script must include measurement tag");
assert(privacyHtml.includes("'analytics_storage': 'denied'"), "privacy.html must set default denied consent");
assert(termsHtml.includes("'analytics_storage': 'denied'"), "terms.html must set default denied consent");
assert(privacyHtml.includes("'wait_for_update': 500"), "privacy.html must include wait_for_update");
assert(termsHtml.includes("'wait_for_update': 500"), "terms.html must include wait_for_update");
console.log("✓ Test 1 Passed: Head script Consent Mode v2 and GA4 loader verified");

// 2. Privacy Policy Content & Disclosures (Human-Readable)
console.log("\n[2] Verifying Privacy Policy Disclosures...");
assert(privacyHtml.includes('Local Storage'), "privacy.html must document local browser storage");
assert(privacyHtml.includes('Gameplay Records &amp; Streaks') || privacyHtml.includes('Gameplay Records'), "privacy.html must describe gameplay records");
assert(privacyHtml.includes('Active Session Progress'), "privacy.html must describe active session progress");
assert(privacyHtml.includes('Cookie Preferences'), "privacy.html must describe cookie preference state");
assert(privacyHtml.includes('Google Analytics'), "privacy.html must document Google Analytics");
assert(privacyHtml.includes('Google Consent Mode'), "privacy.html must document Google Consent Mode");
assert(privacyHtml.includes('GDPR') && privacyHtml.includes('CCPA/CPRA'), "privacy.html must document GDPR and CCPA/CPRA rights");
assert(privacyHtml.includes('data-action="open-cookie-settings"'), "privacy.html must have cookie preferences modal trigger");
console.log("✓ Test 2 Passed: Privacy policy storage, analytics, and privacy rights clauses verified");

// 3. Terms of Service & Nominative Fair Use
console.log("\n[3] Verifying Terms of Service Disclosures...");
assert(termsHtml.includes('Nominative Fair Use'), "terms.html must contain Nominative Fair Use clause");
assert(termsHtml.includes('not affiliated with, associated with, sponsored by, or endorsed by'), "terms.html must contain non-affiliation disclaimer");
assert(termsHtml.includes('FIFA') && termsHtml.includes('UEFA'), "terms.html must disclaim FIFA/UEFA affiliation");
assert(termsHtml.includes('Acceptable Use &amp; Fair Play') || termsHtml.includes('Acceptable Use'), "terms.html must have Acceptable Use clause");
assert(termsHtml.includes('Statistical Datasets &amp; Accuracy') || termsHtml.includes('Statistical Datasets'), "terms.html must have Data Accuracy clause");
assert(termsHtml.includes('data-action="open-cookie-settings"'), "terms.html must have cookie preferences modal trigger");
console.log("✓ Test 3 Passed: Terms of service IP, fair use, and accuracy clauses verified");

// 4. Canonical Links & SEO Metadata
console.log("\n[4] Verifying SEO Metadata & Canonical Links...");
assert(privacyHtml.includes('<link rel="canonical" href="https://playmaker.best/privacy.html"'), "privacy.html must have canonical link");
assert(termsHtml.includes('<link rel="canonical" href="https://playmaker.best/terms.html"'), "terms.html must have canonical link");
assert(privacyHtml.includes('BreadcrumbList'), "privacy.html must include BreadcrumbList JSON-LD schema");
assert(termsHtml.includes('BreadcrumbList'), "terms.html must include BreadcrumbList JSON-LD schema");
console.log("✓ Test 4 Passed: Canonical links and schema structured data verified");

console.log("\n🎉 ALL LEGAL & COMPLIANCE TESTS PASSED SUCCESSFULLY!\n");
