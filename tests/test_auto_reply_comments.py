import unittest
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.auto_reply_comments import (
    normalize_text,
    match_comment_to_pool,
    extract_pool_from_caption
)

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

if __name__ == "__main__":
    unittest.main()
