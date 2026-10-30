import unittest
from pathlib import Path

from layout_engine import LayoutEngine


class BundledLanguageDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = LayoutEngine(Path("models"))

    def test_all_three_bigram_tables_are_loaded(self):
        self.assertGreater(len(self.engine.models["en"].counts), 40000)
        self.assertGreater(len(self.engine.models["ru"].counts), 40000)
        self.assertGreater(len(self.engine.models["ua"].counts), 40000)

    def test_real_word_frequency_recovers_common_mistyped_word(self):
        result = self.engine.suggest_phrase("ghbdtn")
        self.assertIsNotNone(result)
        self.assertEqual(result[0].lower(), "привет")

    def test_real_word_frequency_recovers_full_user_phrase(self):
        result = self.engine.suggest_phrase("b cltkfq xnj,s r ghbvthe")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "и сделай чтобы к примеру")

    def test_real_word_frequency_recovers_second_user_phrase(self):
        result = self.engine.suggest_phrase("b ukfdyjt ghfdbkmyj yfgbcfnm")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "и главное правильно написать")

    def test_real_word_frequency_does_not_rewrite_valid_english(self):
        self.assertIsNone(self.engine.suggest_phrase("this is a test"))


if __name__ == "__main__":
    unittest.main()
