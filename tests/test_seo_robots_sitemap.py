"""
test_seo_robots_sitemap.py — SEO Verification Suite for Task #31
================================================================
Validates:
1. robots.txt rules using RFC 9309 / Googlebot specification (longest-match, wildcard, and end-of-path support).
2. https://playmaker.best/games/transfer_destination.html is 100% crawlable (Allowed).
3. All canonical English and Spanish game URLs are crawlable.
4. Back-in-time day variant archives (_d1.html ... _d180.html) are blocked in robots.txt.
5. Internal build files (.json, .csv, .py, /templates/) are blocked, while manifest.json and games.json are allowed.
6. sitemap.xml validity, existence of referenced paths on disk, and crawlability.
"""

import os
import re
import unittest
import xml.etree.ElementTree as ET


class RFC9309RobotsParser:
    """RFC 9309 & Googlebot robots.txt parser supporting *, $, and longest-match precedence."""

    def __init__(self, robots_txt: str):
        self.rules = []
        for line in robots_txt.splitlines():
            line = line.split("#")[0].strip()
            if not line:
                continue
            if line.lower().startswith("allow:"):
                pattern = line[6:].strip()
                if pattern:
                    self.rules.append((pattern, True))
            elif line.lower().startswith("disallow:"):
                pattern = line[9:].strip()
                if pattern:
                    self.rules.append((pattern, False))

    def can_fetch(self, url_or_path: str) -> bool:
        if "://" in url_or_path:
            path = "/" + url_or_path.split("://", 1)[1].split("/", 1)[1] if "/" in url_or_path.split("://", 1)[1] else "/"
        else:
            path = url_or_path if url_or_path.startswith("/") else "/" + url_or_path

        matches = []
        for pattern, allow in self.rules:
            pat = pattern
            has_end = pat.endswith("$")
            if has_end:
                pat = pat[:-1]
            regex_str = "^" + ".*".join(re.escape(part) for part in pat.split("*"))
            if has_end:
                regex_str += "$"
            if re.search(regex_str, path):
                matches.append((len(pattern), allow, pattern))

        if not matches:
            return True

        # Sort by longest pattern match length descending, then Allow (True > False)
        matches.sort(key=lambda m: (m[0], 1 if m[1] else 0), reverse=True)
        return matches[0][1]


class TestSeoRobotsAndSitemap(unittest.TestCase):

    def setUp(self):
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.robots_txt_path = os.path.join(self.root_dir, "robots.txt")
        self.sitemap_xml_path = os.path.join(self.root_dir, "sitemap.xml")

        self.assertTrue(os.path.exists(self.robots_txt_path), "robots.txt must exist")
        self.assertTrue(os.path.exists(self.sitemap_xml_path), "sitemap.xml must exist")

        with open(self.robots_txt_path, "r", encoding="utf-8") as f:
            self.robots_content = f.read()

        self.parser = RFC9309RobotsParser(self.robots_content)

    def test_transfer_destination_is_allowed(self):
        """Verify primary bug: transfer_destination.html must NOT be blocked by robots.txt."""
        target_urls = [
            "https://playmaker.best/games/transfer_destination.html",
            "https://playmaker.best/es/games/transfer_destination.html",
        ]
        for url in target_urls:
            can_fetch = self.parser.can_fetch(url)
            self.assertTrue(can_fetch, f"URL must be allowed by robots.txt: {url}")

    def test_all_canonical_games_allowed(self):
        """Verify all canonical game modes are crawlable in English and Spanish."""
        game_slugs = [
            "club_connect",
            "top_transfers",
            "transfer_destination",
            "top_scorers",
            "player_chain",
            "passport_fc",
        ]
        for slug in game_slugs:
            en_url = f"https://playmaker.best/games/{slug}.html"
            es_url = f"https://playmaker.best/es/games/{slug}.html"

            self.assertTrue(self.parser.can_fetch(en_url), f"EN game must be allowed: {en_url}")
            self.assertTrue(self.parser.can_fetch(es_url), f"ES game must be allowed: {es_url}")

        # Home & landing pages
        self.assertTrue(self.parser.can_fetch("https://playmaker.best/"))
        self.assertTrue(self.parser.can_fetch("https://playmaker.best/es/"))
        self.assertTrue(self.parser.can_fetch("https://playmaker.best/privacy.html"))
        self.assertTrue(self.parser.can_fetch("https://playmaker.best/terms.html"))

    def test_back_in_time_variants_are_blocked(self):
        """Verify day archive pages (_d1.html ... _d180.html) are disallowed."""
        game_slugs = [
            "club_connect",
            "top_transfers",
            "transfer_destination",
            "top_scorers",
            "player_chain",
            "passport_fc",
        ]
        test_days = [1, 2, 10, 50, 180]

        for slug in game_slugs:
            for day in test_days:
                en_variant = f"https://playmaker.best/games/{slug}_d{day}.html"
                es_variant = f"https://playmaker.best/es/games/{slug}_d{day}.html"

                self.assertFalse(
                    self.parser.can_fetch(en_variant),
                    f"EN archive variant must be disallowed: {en_variant}"
                )
                self.assertFalse(
                    self.parser.can_fetch(es_variant),
                    f"ES archive variant must be disallowed: {es_variant}"
                )

    def test_internal_assets_and_data_files(self):
        """Verify raw data files are blocked, while JSON endpoints needed by PWA/Lobby are allowed."""
        # Allowed JSON / public configs
        self.assertTrue(self.parser.can_fetch("https://playmaker.best/manifest.json"))
        self.assertTrue(self.parser.can_fetch("https://playmaker.best/games.json"))
        self.assertTrue(self.parser.can_fetch("https://playmaker.best/games.json?v=123"))

        # Blocked sensitive/build paths
        self.assertFalse(self.parser.can_fetch("https://playmaker.best/templates/top_transfers_template.html"))
        self.assertFalse(self.parser.can_fetch("https://playmaker.best/data/daily_transfers.csv"))
        self.assertFalse(self.parser.can_fetch("https://playmaker.best/fetch_daily.py"))

    def test_sitemap_xml_structure_and_completeness(self):
        """Verify sitemap.xml is valid XML and contains all canonical pages."""
        tree = ET.parse(self.sitemap_xml_path)
        root = tree.getroot()

        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [loc.text for loc in root.findall("sm:url/sm:loc", ns)]

        self.assertGreater(len(urls), 10, "Sitemap should contain all primary and localized pages")

        expected_pages = [
            "https://playmaker.best/",
            "https://playmaker.best/games/club_connect.html",
            "https://playmaker.best/games/top_transfers.html",
            "https://playmaker.best/games/transfer_destination.html",
            "https://playmaker.best/games/top_scorers.html",
            "https://playmaker.best/games/player_chain.html",
            "https://playmaker.best/games/passport_fc.html",
            "https://playmaker.best/es/",
            "https://playmaker.best/es/games/club_connect.html",
            "https://playmaker.best/es/games/top_transfers.html",
            "https://playmaker.best/es/games/transfer_destination.html",
            "https://playmaker.best/es/games/top_scorers.html",
            "https://playmaker.best/es/games/player_chain.html",
            "https://playmaker.best/es/games/passport_fc.html",
            "https://playmaker.best/marketing.html",
            "https://playmaker.best/privacy.html",
            "https://playmaker.best/terms.html",
        ]

        for expected in expected_pages:
            self.assertIn(expected, urls, f"Sitemap missing canonical URL: {expected}")
            self.assertTrue(self.parser.can_fetch(expected), f"Sitemap URL must be crawlable: {expected}")

            # Verify local file exists on disk
            rel_path = expected.replace("https://playmaker.best/", "")
            if not rel_path or rel_path == "es/":
                local_file = os.path.join(self.root_dir, rel_path, "index.html")
            else:
                local_file = os.path.join(self.root_dir, rel_path)

            self.assertTrue(os.path.exists(local_file), f"Target file for sitemap URL must exist: {local_file}")

    def test_custom_404_seo_and_navigation(self):
        """Verify 404.html contains noindex, follow directive and back-to-arcade links."""
        four_o_four = os.path.join(self.root_dir, "404.html")
        self.assertTrue(os.path.exists(four_o_four), "404.html must exist")
        with open(four_o_four, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('content="noindex, follow"', content, "404 page must have noindex, follow")
        self.assertIn("dark", content, "404 page must match site dark theme")
        self.assertIn("games/top_transfers.html", content, "404 page should provide links to top game modes")

    def test_viewports_allow_user_zoom(self):
        """Verify no HTML templates or game modes disable accessibility zoom."""
        import glob
        html_files = glob.glob(os.path.join(self.root_dir, "templates", "*.html")) + [
            os.path.join(self.root_dir, "index.html"),
            os.path.join(self.root_dir, "es", "index.html"),
        ]

        for fpath in html_files:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn(
                "user-scalable=no",
                content,
                f"File {fpath} must not disable user-scalable for mobile SEO accessibility"
            )
            self.assertNotIn(
                "maximum-scale=1.0",
                content,
                f"File {fpath} must not restrict maximum-scale for mobile SEO accessibility"
            )

    def test_google_fonts_preconnect_hints(self):
        """Verify Google fonts preconnect tags are present on primary pages and templates."""
        import glob
        check_files = [
            os.path.join(self.root_dir, "index.html"),
            os.path.join(self.root_dir, "es", "index.html"),
            os.path.join(self.root_dir, "marketing.html"),
            os.path.join(self.root_dir, "privacy.html"),
            os.path.join(self.root_dir, "terms.html"),
        ] + glob.glob(os.path.join(self.root_dir, "templates", "*.html"))

        for fpath in check_files:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn(
                'rel="preconnect" href="https://fonts.googleapis.com"',
                content,
                f"File {fpath} missing preconnect for fonts.googleapis.com"
            )
            self.assertIn(
                'rel="preconnect" href="https://fonts.gstatic.com"',
                content,
                f"File {fpath} missing preconnect for fonts.gstatic.com"
            )

    def test_spanish_faq_schema_validity(self):
        """Verify es/index.html FAQPage schema has valid @type: Question entries."""
        import json
        es_index = os.path.join(self.root_dir, "es", "index.html")
        with open(es_index, "r", encoding="utf-8") as f:
            content = f.read()

        match = re.search(r'<script type="application/ld\+json">([\s\S]*?)</script>', content)
        self.assertIsNotNone(match, "JSON-LD script must exist in es/index.html")
        data = json.loads(match.group(1))

        faq_nodes = [item for item in data.get("@graph", []) if item.get("@type") == "FAQPage"]
        self.assertEqual(len(faq_nodes), 1, "Must contain exactly one FAQPage node")

        main_entities = faq_nodes[0].get("mainEntity", [])
        self.assertGreater(len(main_entities), 3, "FAQPage must contain question entities")
        for q in main_entities:
            self.assertEqual(q.get("@type"), "Question", f"Every FAQ entry must have @type: Question, got {q.get('@type')}")
            self.assertTrue(bool(q.get("name")), "Question name must not be empty")
            self.assertTrue(bool(q.get("acceptedAnswer", {}).get("text")), "Question acceptedAnswer must have text")


if __name__ == "__main__":
    unittest.main()

