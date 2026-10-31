import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from layout_engine import LayoutEngine, convert


class LayoutEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.engine = LayoutEngine(Path(self.temp.name))

    def tearDown(self):
        self.temp.cleanup()

    def score(self, word, lang):
        ru = {"и": 5.5, "сделай": 4.4, "чтобы": 4.7, "к": 5.0,
              "примеру": 3.8, "главное": 4.1, "правильно": 4.2,
              "написать": 4.3, "привет": 5.2, "проверим": 4.0}
        ua = {"і": 5.5, "зроби": 4.4, "щоб": 4.7, "до": 5.0,
              "прикладу": 3.8, "головне": 4.1, "правильно": 4.2,
              "написати": 4.3, "привіт": 5.2}
        if lang == "ru":
            return ru.get(word.lower(), 0.1)
        if lang == "ua":
            return ua.get(word.lower(), 0.1)
        return {"this": 5.0, "is": 5.0, "a": 5.0, "test": 5.0,
                "hello": 5.0, "world": 4.8, "b": 3.2}.get(word.lower(), 0.1)

    def test_all_six_layout_directions(self):
        self.assertEqual(convert("ghbdtn", "en", "ru"), "привет")
        self.assertEqual(convert("ghbdtn", "en", "ua"), "привет")
        self.assertEqual(convert("руддщ", "ru", "en"), "hello")
        self.assertEqual(convert("руддщ", "ua", "en"), "hello")
        self.assertEqual(convert("руддщ", "ru", "ua"), "руддщ")
        self.assertEqual(convert("руддщ", "ua", "ru"), "руддщ")

    def test_cyjdf_maps_to_russian_snova(self):
        self.assertEqual(convert("cyjdf", "en", "ru"), "снова")

    def test_russian_ukrainian_distinguishing_keys(self):
        self.assertEqual(convert("ы", "ru", "ua"), "і")
        self.assertEqual(convert("і", "ua", "ru"), "ы")

    def test_recovers_phrase_instead_of_isolated_tokens(self):
        with patch.object(self.engine, "word_score", side_effect=self.score):
            result = self.engine.suggest_phrase("b cltkfq xnj,s r ghbvthe")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "и сделай чтобы к примеру")
        self.assertEqual(result[1], "ru")

    def test_recovers_second_phrase(self):
        with patch.object(self.engine, "word_score", side_effect=self.score):
            result = self.engine.suggest_phrase("b ukfdyjt ghfdbkmyj yfgbcfnm")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "и главное правильно написать")

    def test_all_six_directions_with_language_evidence(self):
        cases = [
            ("ghbdtn", "ru", "привет"),
            ("csv", "ua", "сім"),
            ("руддщ", "en", "hello"),
            ("сім", "en", "csv"),
            ("сым", "ua", "сім"),
            ("мі", "ru", "мы"),
        ]
        for raw, target, expected in cases:
            with self.subTest(raw=raw, target=target):
                def score(word, lang, target=target, expected=expected):
                    return 5.0 if lang == target and word.lower() == expected else 0.1
                with patch.object(self.engine, "word_score", side_effect=score):
                    result = self.engine.suggest_phrase(raw)
                self.assertIsNotNone(result)
                self.assertEqual(result[0].lower(), expected)
                self.assertEqual(result[1], target)

    def test_recovers_cyjdf_as_russian_snova(self):
        def score(word, lang):
            return 4.8 if word.lower() == "снова" and lang == "ru" else 0.1
        with patch.object(self.engine, "word_score", side_effect=score):
            result = self.engine.suggest_phrase("cyjdf")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "снова")
        self.assertEqual(result[1], "ru")

    def test_recovers_single_word_with_strong_lexical_evidence(self):
        with patch.object(self.engine, "word_score", side_effect=self.score):
            result = self.engine.suggest_phrase("ghbdtn")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "привет")

    def test_does_not_guess_single_letter_without_context(self):
        with patch.object(self.engine, "word_score", side_effect=self.score):
            self.assertIsNone(self.engine.suggest_phrase("b"))

    def test_does_not_change_valid_english_phrase(self):
        with patch.object(self.engine, "word_score", side_effect=self.score):
            self.assertIsNone(self.engine.suggest_phrase("this is a test"))

    def test_bigram_context_changes_phrase_score(self):
        model = self.engine.models["en"]
        model.counts[("good", "morning")] = 90
        model.outgoing["good"] = 100
        with patch.object(self.engine, "word_score", side_effect=lambda w, l: 4.0):
            self.assertGreater(
                self.engine.phrase_score(["good", "morning"], "en"),
                self.engine.phrase_score(["morning", "good"], "en"),
            )


if __name__ == "__main__":
    unittest.main()
