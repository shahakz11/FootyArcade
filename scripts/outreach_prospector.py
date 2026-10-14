#!/usr/bin/env python3
"""
Playmaker Outreach Prospector & Verifier
----------------------------------------
Automates finding and evaluating football prospects (apps, blogs, fantasy, creators) in English and Spanish,
extracts contact channels (emails, contact forms, social media), and can push them directly
into the Google Sheet outreach tabs.
"""

import sys
import re
import json
import csv
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from typing import Dict, List, Optional, Set

try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False


USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
DEPLOYED_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxqlsST0oCjrnbesl2n4eE4EBNtVekspWi7hPWwGdRtaHf6WA9gROf84TmyVdxQsuI89A/exec"

# Common email extraction regex
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

# Social media pattern matchers
SOCIAL_PATTERNS = {
    "twitter": re.compile(r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/([a-zA-Z0-9_]{1,30})', re.IGNORECASE),
    "linkedin": re.compile(r'(?:https?://)?(?:www\.)?linkedin\.com/(?:company|in)/([a-zA-Z0-9_-]+)', re.IGNORECASE),
    "instagram": re.compile(r'(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9_.-]{1,30})', re.IGNORECASE),
    "youtube": re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/(?:@|channel/|c/)?([a-zA-Z0-9_-]+)', re.IGNORECASE)
}


class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: Set[str] = set()

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for name, val in attrs:
                if name == "href" and val:
                    self.links.add(val.strip())


def fetch_url(url: str, timeout: int = 8) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" in content_type or "text/plain" in content_type:
                return response.read().decode("utf-8", errors="ignore")
    except Exception:
        pass
    return None


def verify_email_domain(email: str) -> bool:
    """Checks if the email domain has active DNS MX records."""
    if not DNS_AVAILABLE:
        return True
    try:
        domain = email.split("@")[1].strip()
        records = dns.resolver.resolve(domain, "MX")
        return len(records) > 0
    except Exception:
        return False


def extract_contacts_from_html(html: str, base_url: str) -> Dict[str, any]:
    """Scrapes emails, contact forms, and social media handles from page HTML."""
    contacts = {
        "emails": set(),
        "contact_forms": set(),
        "socials": {}
    }

    # Extract emails
    found_emails = EMAIL_REGEX.findall(html)
    for em in found_emails:
        clean = em.lower().strip()
        if not clean.endswith((".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".css", ".js")) and "example.com" not in clean:
            contacts["emails"].add(clean)

    # Extract links
    parser = LinkExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass

    for link in parser.links:
        full_url = urllib.parse.urljoin(base_url, link)
        lower_link = full_url.lower()

        if any(kw in lower_link for kw in ["contact", "contacto", "support", "help", "soporte", "advertise", "publicidad"]):
            if "mailto:" not in lower_link:
                contacts["contact_forms"].add(full_url)

        for platform, pattern in SOCIAL_PATTERNS.items():
            match = pattern.search(full_url)
            if match and platform not in contacts["socials"]:
                contacts["socials"][platform] = full_url

    contacts["emails"] = list(contacts["emails"])
    contacts["contact_forms"] = list(contacts["contact_forms"])[:3]
    return contacts


def scan_prospect_domain(domain: str) -> Dict[str, any]:
    """Scrapes root and potential contact pages of a candidate domain."""
    clean_domain = domain.strip().lower().replace("http://", "").replace("https://", "").split("/")[0]
    base_url = f"https://{clean_domain}"

    root_html = fetch_url(base_url)
    all_emails = set()
    all_forms = set()
    all_socials = {}
    title = clean_domain

    if root_html:
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', root_html, re.I)
        if title_match:
            title = re.split(r'[-–|:•]', title_match.group(1))[0].strip()

        extracted = extract_contacts_from_html(root_html, base_url)
        all_emails.update(extracted["emails"])
        all_forms.update(extracted["contact_forms"])
        all_socials.update(extracted["socials"])

    # Try common contact subpaths if no emails found
    if not all_emails:
        for sub in ["contact", "contacto", "contact-us", "about", "acerca", "advertise", "publicidad"]:
            sub_url = urllib.parse.urljoin(base_url, f"/{sub}")
            sub_html = fetch_url(sub_url)
            if sub_html:
                sub_extracted = extract_contacts_from_html(sub_html, sub_url)
                all_emails.update(sub_extracted["emails"])
                all_forms.update(sub_extracted["contact_forms"])
                for k, v in sub_extracted["socials"].items():
                    if k not in all_socials:
                        all_socials[k] = v
                if all_emails:
                    break

    # Validate emails via DNS MX
    verified_emails = []
    for em in all_emails:
        if verify_email_domain(em):
            verified_emails.append(em)

    return {
        "domain": clean_domain,
        "company": title or clean_domain,
        "verified_emails": verified_emails,
        "contact_forms": list(all_forms),
        "socials": all_socials
    }


def push_to_google_sheet(domain: str, is_spanish: bool = True, webapp_url: str = DEPLOYED_WEBAPP_URL) -> bool:
    """Sends a prospect domain directly into the bound Google Sheet via deployed Web App."""
    payload = {
        "action": "prospect_domain",
        "domain": domain,
        "isSpanish": is_spanish
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(webapp_url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json.get("status") == "ok"
    except Exception as e:
        print(f"Error pushing {domain} to Google Sheet Web App: {e}")
        return False


if __name__ == "__main__":
    args = sys.argv[1:]
    is_spanish = True
    push = False

    if "--en" in args:
        is_spanish = False
        args.remove("--en")
    if "--es" in args:
        is_spanish = True
        args.remove("--es")
    if "--push" in args:
        push = True
        args.remove("--push")

    test_domains = args if args else ["fotmob.com", "biwenger.com", "whoareya.com"]

    print(f"🚀 Scanning {len(test_domains)} domains (Language: {'ES' if is_spanish else 'EN'})...")
    for d in test_domains:
        result = scan_prospect_domain(d)
        print("\n" + "="*50)
        print(f"Domain: {result['domain']} ({result['company']})")
        print(f"Emails: {result['verified_emails']}")
        print(f"Contact Forms: {result['contact_forms']}")
        print(f"Social Links: {result['socials']}")

        if push:
            print(f"Pushing {d} to Google Sheet...")
            ok = push_to_google_sheet(d, is_spanish=is_spanish)
            print(f"-> Result: {'SUCCESS' if ok else 'FAILED'}")
