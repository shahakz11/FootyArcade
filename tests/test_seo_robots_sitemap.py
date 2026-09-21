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


if __name__ == "__main__":
    unittest.main()
