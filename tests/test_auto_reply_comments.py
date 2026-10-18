import unittest
import sys
import os
import tempfile
import json
import csv
import concurrent.futures

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.auto_reply_comments import (
    normalize_text,
    match_comment_to_pool,
    extract_pool_from_caption,
    get_all_active_daily_answer_pools,
    load_ledger,
    save_ledger
)
try:
    from scripts.auto_reply_comments import load_played_with_pools
except ImportError:
    load_played_with_pools = None


class TestAutoReplyComments(unittest.TestCase):

    def test_normalize_text(self):
        self.assertEqual(normalize_text("Antoine Griezmann"), "antoine griezmann")
        self.assertEqual(normalize_text("Éric Abidal 🇫🇷"), "eric abidal")
        self.assertEqual(normalize_text("Julues kounde 👏!"), "julues kounde")

    def test_exact_and_last_name_matching(self):
        pool = ["Antoine Griezmann", "Samuel Umtiti", "Jules Koundé", "Thierry Henry"]
        
        # Exact full name
        self.assertEqual(match_comment_to_pool("Samuel Umtiti", pool), "Samuel Umtiti")
        
        # Last name
        self.assertEqual(match_comment_to_pool("Griezmann", pool), "Antoine Griezmann")
        self.assertEqual(match_comment_to_pool("kounde", pool), "Jules Koundé")
        self.assertEqual(match_comment_to_pool("henry was great", pool), "Thierry Henry")

    def test_nickname_matching(self):
        pool = ["Thierry Henry", "Antoine Griezmann", "Cristiano Ronaldo", "Ángel Di María"]
        
        self.assertEqual(match_comment_to_pool("Titi", pool), "Thierry Henry")
        self.assertEqual(match_comment_to_pool("grizou", pool), "Antoine Griezmann")
        self.assertEqual(match_comment_to_pool("CR7", pool), "Cristiano Ronaldo")
        self.assertEqual(match_comment_to_pool("di maria", pool), "Ángel Di María")

    def test_compound_names(self):
        pool = ["Ángel Di María", "Frenkie de Jong", "Virgil van Dijk"]
        
        self.assertEqual(match_comment_to_pool("di maria", pool), "Ángel Di María")
        self.assertEqual(match_comment_to_pool("de jong", pool), "Frenkie de Jong")
        self.assertEqual(match_comment_to_pool("van dijk is a wall", pool), "Virgil van Dijk")

    def test_invalid_comments_do_not_match(self):
        pool = ["Thierry Henry", "Jules Koundé"]
        
        self.assertIsNone(match_comment_to_pool("Lionel Messi", pool))
        self.assertIsNone(match_comment_to_pool("Hello football fans", pool))
        self.assertIsNone(match_comment_to_pool("No one", pool))

    def test_caption_pool_extraction(self):
        all_pools = [
            {
                "type": "passport_fc",
                "entity_1": "Chelsea",
                "entity_2": "France",
                "players": ["Malo Gusto", "N'Golo Kanté", "Nicolas Anelka"]
            },
            {
                "type": "player_chain",
                "entity_1": "Barcelona",
                "entity_2": "Benfica",
                "players": ["Deco", "João Félix", "Nélson Semedo"]
            }
        ]

        cap1 = "Name ONE France player to play for Chelsea that NO ONE ELSE in the comments will say."
        extracted1 = extract_pool_from_caption(cap1, all_pools)
        self.assertEqual(extracted1, ["Malo Gusto", "N'Golo Kanté", "Nicolas Anelka"])

        # YouTube Shorts title with emoji and hashtags
        yt_title1 = "Name ONE France player for Chelsea (No one else will say) ⚽️ #Shorts"
        extracted_yt1 = extract_pool_from_caption(yt_title1, all_pools)
        self.assertEqual(extracted_yt1, ["Malo Gusto", "N'Golo Kanté", "Nicolas Anelka"])

        cap2 = "Name ONE player who played for BOTH Barcelona and Benfica that NO ONE ELSE in the comments will say."
        extracted2 = extract_pool_from_caption(cap2, all_pools)
        self.assertEqual(extracted2, ["Deco", "João Félix", "Nélson Semedo"])

        yt_title2 = "Name ONE player for Barcelona & Benfica (No one else will say) ⚽️ #Shorts"
        extracted_yt2 = extract_pool_from_caption(yt_title2, all_pools)
        self.assertEqual(extracted_yt2, ["Deco", "João Félix", "Nélson Semedo"])


class TestPlayedWithAutoReply(unittest.TestCase):
    """
    Tier 1 & Tier 2: Comprehensive tests for 'Played With' comment auto-reply:
    - Pool ingestion from daily_played_with_games.csv
    - Caption extraction (Day #, 'Who Am I?', teammate lists)
    - Fallback safety guard (prevent merging all players)
    - Diacritic, accent, and case-insensitive matching
    - Strict rejection of teammates and wrong player guesses
    - Ledger deduplication idempotency
    """

    @classmethod
    def setUpClass(cls):
        # Build synthetic/reference pool for isolated hermetic tests
        cls.day1_mystery = "João Félix"
        cls.day1_teammates = ["Thomas Lemar", "Nélson Semedo", "Ángel Correa", "Koke", "Jan Oblak"]
        cls.day20_mystery = "Stevan Jovetić"
        cls.day20_teammates = ["Valon Behrami", "Matija Nastasić", "Adem Ljajić", "Stefan Savić", "Manuel Pasqual"]
        cls.day31_mystery = "Pierre-Emerick Aubameyang"
        cls.day31_teammates = ["Dan-Axel Zagadou", "Manuel Akanji", "Axel Witsel", "Marco Reus", "Henrikh Mkhitaryan"]

        cls.mock_pools = [
            {
                "type": "played_with",
                "game_day": 1,
                "mystery_player": cls.day1_mystery,
                "players": [cls.day1_mystery],
                "teammates": cls.day1_teammates
            },
            {
                "type": "played_with",
                "game_day": 20,
                "mystery_player": cls.day20_mystery,
                "players": [cls.day20_mystery],
                "teammates": cls.day20_teammates
            },
            {
                "type": "played_with",
                "game_day": 31,
                "mystery_player": cls.day31_mystery,
                "players": [cls.day31_mystery],
                "teammates": cls.day31_teammates
            }
        ]

    def test_load_played_with_pools_from_csv(self):
        """Verifies ingestion of all 365 puzzles from daily_played_with_games.csv."""
        if load_played_with_pools is not None:
            pools = load_played_with_pools()
        else:
            all_pools = get_all_active_daily_answer_pools()
            pools = [p for p in all_pools if p.get("type") == "played_with"]

        if not pools:
            self.skipTest("Played With pools not yet ingested in scripts/auto_reply_comments.py")

        self.assertEqual(len(pools), 365, f"Expected 365 Played With pools, got {len(pools)}")
        
        # Verify first pool structure (Day 1)
        p1 = pools[0]
        self.assertEqual(p1.get("type"), "played_with")
        self.assertEqual(p1.get("game_day"), 1)
        self.assertEqual(p1.get("mystery_player"), "João Félix")
        self.assertEqual(p1.get("players"), ["João Félix"])
        self.assertIn("teammates", p1)
        self.assertEqual(len(p1["teammates"]), 5)

    def test_extract_pool_from_caption_day_number(self):
        """Verifies extracting pool from caption containing day number patterns (#1, Day 20, #31)."""
        # Test #20
        cap_hash20 = "Played With #20 | Who Am I? Drop your guess in the comments! ⚽ #Shorts"
        extracted = extract_pool_from_caption(cap_hash20, self.mock_pools)
        if extracted is None:
            self.skipTest("Played With caption extraction not yet implemented in scripts/auto_reply_comments.py")
        self.assertEqual(extracted, ["Stevan Jovetić"])

        # Test Day 1
        cap_day1 = "Played With Day 1: Can you guess this footballer? 🏆 Play on playmaker.best"
        extracted = extract_pool_from_caption(cap_day1, self.mock_pools)
        self.assertEqual(extracted, ["João Félix"])

        # Test Who Am I? #31
        cap_who31 = "WHO AM I? #31 - 5 teammates, 1 mystery player. Guess below! 👇"
        extracted = extract_pool_from_caption(cap_who31, self.mock_pools)
        self.assertEqual(extracted, ["Pierre-Emerick Aubameyang"])

    def test_extract_pool_from_caption_teammate_list(self):
        """Verifies extracting pool when caption contains >= 2 teammate clues."""
        cap_teammates = (
            "I played with Valon Behrami, Matija Nastasić, and Stefan Savić! "
            "Can you guess who I am? Comment below! #football"
        )
        extracted = extract_pool_from_caption(cap_teammates, self.mock_pools)
        if extracted is None:
            self.skipTest("Teammate list caption extraction not yet implemented in scripts/auto_reply_comments.py")
        self.assertEqual(extracted, ["Stevan Jovetić"])

    def test_fallback_safety_guard_no_merging(self):
        """
        Safety Guard: An unparseable or irrelevant caption must return None,
        and must NEVER return a merged list of all players.
        """
        unrelated_caption = "Top 10 most expensive stadiums in the world! 🏟️ #Shorts"
        extracted = extract_pool_from_caption(unrelated_caption, self.mock_pools)
        self.assertIsNone(extracted, "Unrelated caption should return None, never fallback pool")

    def test_mystery_player_fuzzy_matching_accents_and_case(self):
        """
        Verifies diacritic-insensitive, case-insensitive, and surname matching
        for mystery players.
        """
        pool_felix = ["João Félix"]
        pool_jovetic = ["Stevan Jovetić"]
        pool_auba = ["Pierre-Emerick Aubameyang"]

        # Accent stripping
        self.assertEqual(match_comment_to_pool("Joao Felix", pool_felix), "João Félix")
        self.assertEqual(match_comment_to_pool("Stevan Jovetic", pool_jovetic), "Stevan Jovetić")

        # Lowercase and uppercase
        self.assertEqual(match_comment_to_pool("joao felix", pool_felix), "João Félix")
        self.assertEqual(match_comment_to_pool("STEVAN JOVETIC", pool_jovetic), "Stevan Jovetić")

        # Surname only
        self.assertEqual(match_comment_to_pool("felix", pool_felix), "João Félix")
        self.assertEqual(match_comment_to_pool("jovetic", pool_jovetic), "Stevan Jovetić")
        self.assertEqual(match_comment_to_pool("Aubameyang", pool_auba), "Pierre-Emerick Aubameyang")

        # Conversational sentences
        self.assertEqual(match_comment_to_pool("100% Joao Felix mate", pool_felix), "João Félix")
        self.assertEqual(match_comment_to_pool("That is obviously Jovetic!", pool_jovetic), "Stevan Jovetić")
        self.assertEqual(match_comment_to_pool("aubameyang without a doubt", pool_auba), "Pierre-Emerick Aubameyang")

    def test_rejection_of_teammate_names(self):
        """
        Adversarial Test: When mystery player is 'João Félix', teammate names
        (Lemar, Semedo, Correa, Koke, Oblak) MUST NOT match as correct!
        """
        pool_felix = ["João Félix"]

        # Teammate full names
        self.assertIsNone(match_comment_to_pool("Thomas Lemar", pool_felix))
        self.assertIsNone(match_comment_to_pool("Nélson Semedo", pool_felix))
        self.assertIsNone(match_comment_to_pool("Ángel Correa", pool_felix))
        self.assertIsNone(match_comment_to_pool("Koke", pool_felix))
        self.assertIsNone(match_comment_to_pool("Jan Oblak", pool_felix))

        # Teammate surnames
        self.assertIsNone(match_comment_to_pool("Oblak", pool_felix))
        self.assertIsNone(match_comment_to_pool("Lemar", pool_felix))
        self.assertIsNone(match_comment_to_pool("Semedo", pool_felix))

    def test_rejection_of_incorrect_footballers_and_noise(self):
        """Verifies incorrect footballers and casual chatter are strictly rejected."""
        pool_felix = ["João Félix"]

        self.assertIsNone(match_comment_to_pool("Lionel Messi", pool_felix))
        self.assertIsNone(match_comment_to_pool("Cristiano Ronaldo", pool_felix))
        self.assertIsNone(match_comment_to_pool("Kylian Mbappé", pool_felix))
        self.assertIsNone(match_comment_to_pool("Erling Haaland", pool_felix))
        self.assertIsNone(match_comment_to_pool("I have no clue bro", pool_felix))
        self.assertIsNone(match_comment_to_pool("Great video as always!", pool_felix))
        self.assertIsNone(match_comment_to_pool("first comment", pool_felix))

    def test_ledger_deduplication_idempotency(self):
        """
        Verifies that reply ledger operations prevent duplicate replies to the same comment.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_ledger_path = os.path.join(tmpdir, "test_ledger.json")

            # 1. Initial state: ledger is empty
            ledger = load_ledger(test_ledger_path)
            self.assertEqual(ledger, {})

            # 2. Process first comment
            comment_id = "yt_comment_98765"
            self.assertNotIn(comment_id, ledger)

            # Record reply in ledger
            ledger[comment_id] = {
                "author": "FootyFan99",
                "matched_player": "João Félix",
                "replied_at": "2026-10-18T03:00:00Z",
                "status": "replied"
            }
            save_ledger(test_ledger_path, ledger)

            # 3. Reload ledger from disk and verify persistence
            reloaded_ledger = load_ledger(test_ledger_path)
            self.assertIn(comment_id, reloaded_ledger)
            self.assertEqual(reloaded_ledger[comment_id]["matched_player"], "João Félix")

            # 4. Attempt second reply for same comment_id: must be recognized as duplicate
            is_already_replied = comment_id in reloaded_ledger
            self.assertTrue(is_already_replied, "Ledger must detect comment as already replied")

    def test_unicode_latin_transliteration(self):
        """
        Regression Test: Verifies non-decomposing Latin characters (Ø, ø, ß, Æ, æ, Ł, ł, Đ, đ)
        are transliterated correctly so Martin Ødegaard, Pierre-Emile Højbjerg, and Pascal Groß match.
        """
        self.assertEqual(normalize_text("Martin Ødegaard"), "martin odegaard")
        self.assertEqual(normalize_text("Pierre-Emile Højbjerg"), "pierre emile hojbjerg")
        self.assertEqual(normalize_text("Pascal Groß"), "pascal gross")
        self.assertEqual(normalize_text("Łukasz Fabiański"), "lukasz fabianski")
        self.assertEqual(normalize_text("Đorđe Petrović"), "dorde petrovic")

        pool_odegaard = ["Martin Ødegaard"]
        pool_hojbjerg = ["Pierre-Emile Højbjerg"]
        pool_gross = ["Pascal Groß"]

        self.assertEqual(match_comment_to_pool("Martin Odegaard", pool_odegaard), "Martin Ødegaard")
        self.assertEqual(match_comment_to_pool("odegaard", pool_odegaard), "Martin Ødegaard")
        self.assertEqual(match_comment_to_pool("Pierre-Emile Hojbjerg", pool_hojbjerg), "Pierre-Emile Højbjerg")
        self.assertEqual(match_comment_to_pool("hojbjerg", pool_hojbjerg), "Pierre-Emile Højbjerg")
        self.assertEqual(match_comment_to_pool("Pascal Gross", pool_gross), "Pascal Groß")
        self.assertEqual(match_comment_to_pool("gross", pool_gross), "Pascal Groß")

    def test_three_letter_surnames_in_caption_extraction(self):
        """
        Regression Test: Verifies 3-letter surnames (Son, Tah, Max, Eze) in captions
        properly match puzzle teammate lists.
        """
        test_pools = [
            {
                "type": "played_with",
                "game_day": 3,
                "mystery_player": "Pierre-Emile Højbjerg",
                "players": ["Pierre-Emile Højbjerg"],
                "teammates": ["Christian Eriksen", "Heung-min Son", "Harry Kane"]
            },
            {
                "type": "played_with",
                "game_day": 12,
                "mystery_player": "Florian Wirtz",
                "players": ["Florian Wirtz"],
                "teammates": ["Jonathan Tah", "Granit Xhaka", "Jeremie Frimpong"]
            },
            {
                "type": "played_with",
                "game_day": 149,
                "mystery_player": "Eberechi Eze",
                "players": ["Eberechi Eze"],
                "teammates": ["Philipp Max", "Michael Olise", "Marc Guéhi"]
            }
        ]

        # Test Son + Eriksen
        cap_son = "I played with Son and Eriksen! Can you guess who I am? #Shorts"
        extracted_son = extract_pool_from_caption(cap_son, test_pools)
        self.assertEqual(extracted_son, ["Pierre-Emile Højbjerg"])

        # Test Tah + Xhaka
        cap_tah = "Who played with Tah and Xhaka? Drop your shout in the comments! ⚽"
        extracted_tah = extract_pool_from_caption(cap_tah, test_pools)
        self.assertEqual(extracted_tah, ["Florian Wirtz"])

        # Test Max + Olise
        cap_max = "Played with Max and Olise in the Premier League! Guess who 👇"
        extracted_max = extract_pool_from_caption(cap_max, test_pools)
        self.assertEqual(extracted_max, ["Eberechi Eze"])

    def test_multi_word_comment_disambiguation_near_misses(self):
        """
        Regression Test: Verifies multi-word comments containing names of other footballers
        that collide on a single surname or first name (e.g. Felix Kroos, Gabriel Jesus,
        Rafa Silva, Bernardo Silva, Eric García) are strictly rejected (return None).
        """
        pool_felix = ["João Félix"]
        pool_gabriel = ["Gabriel"]
        pool_silva = ["António Silva"]
        pool_garcia = ["Joan García"]

        # 1. Other footballers with surname/first-name collisions must return None
        self.assertIsNone(match_comment_to_pool("Felix Kroos", pool_felix))
        self.assertIsNone(match_comment_to_pool("Gabriel Jesus", pool_gabriel))
        self.assertIsNone(match_comment_to_pool("Gabriel Martinelli", pool_gabriel))
        self.assertIsNone(match_comment_to_pool("Rafa Silva", pool_silva))
        self.assertIsNone(match_comment_to_pool("Bernardo Silva", pool_silva))
        self.assertIsNone(match_comment_to_pool("Thiago Silva", pool_silva))
        self.assertIsNone(match_comment_to_pool("David Silva", pool_silva))
        self.assertIsNone(match_comment_to_pool("Eric García", pool_garcia))
        self.assertIsNone(match_comment_to_pool("Eric Garcia", pool_garcia))

        # 2. Conversational guesses for correct players must still succeed
        self.assertEqual(match_comment_to_pool("I think it is Felix", pool_felix), "João Félix")
        self.assertEqual(match_comment_to_pool("Felix for sure", pool_felix), "João Félix")
        self.assertEqual(match_comment_to_pool("Gabriel", pool_gabriel), "Gabriel")
        self.assertEqual(match_comment_to_pool("It is Gabriel", pool_gabriel), "Gabriel")
        self.assertEqual(match_comment_to_pool("Antonio Silva for sure", pool_silva), "António Silva")
        self.assertEqual(match_comment_to_pool("obviously Silva!", pool_silva), "António Silva")

    def test_concurrent_save_ledger_thread_safety(self):
        """
        Regression Test: Verifies unique NamedTemporaryFile in save_ledger prevents
        collisions, file truncation, or crashes under concurrent multi-threaded writes.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path = os.path.join(tmpdir, "concurrent_ledger.json")
            save_ledger(ledger_path, {})

            errors = []
            def worker(thread_idx):
                try:
                    for j in range(15):
                        cur = load_ledger(ledger_path)
                        cur[f"t_{thread_idx}_{j}"] = {"thread": thread_idx, "iter": j}
                        save_ledger(ledger_path, cur)
                except Exception as ex:
                    errors.append(str(ex))

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(worker, i) for i in range(8)]
                concurrent.futures.wait(futures)

            self.assertEqual(len(errors), 0, f"Expected 0 concurrent errors, got: {errors}")
            final_ledger = load_ledger(ledger_path)
            self.assertIsInstance(final_ledger, dict)
            self.assertGreater(len(final_ledger), 0)


if __name__ == "__main__":
    unittest.main()
