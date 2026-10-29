import unittest
from unittest.mock import patch

import my_switcher
from my_switcher import convert, suggest_correction


class LayoutMappingTests(unittest.TestCase):
    def test_english_layout_to_russian_with_comma_letter(self):
        self.assertEqual(convert("hf,jns", "en", "ru"), "работы")

    def test_english_layout_to_russian_hello(self):
        self.assertEqual(convert("ghbdtn", "en", "ru"), "привет")

    def test_english_layout_to_english_is_identity_for_test(self):
        self.assertEqual(convert("test", "en", "en"), "test")

    def test_known_dictionary_word_fixes_layout_even_with_low_frequency_score(self):
        words = {k: set(v) for k, v in my_switcher.DEFAULT.items()}
        with patch("my_switcher.zipf_frequency", return_value=0.0):
            my_switcher._word_score.cache_clear()
            self.assertEqual(suggest_correction("ghbdtn", words)[0:2], ("привет", "ru"))
        my_switcher._word_score.cache_clear()

    def test_valid_english_word_is_not_replaced_by_dictionary_fallback(self):
        words = {k: set(v) for k, v in my_switcher.DEFAULT.items()}
        with patch("my_switcher.zipf_frequency", return_value=0.0):
            my_switcher._word_score.cache_clear()
            self.assertIsNone(suggest_correction("hello", words))
        my_switcher._word_score.cache_clear()


    def test_single_letter_english_token_can_be_corrected_to_russian(self):
        words = {k: set(v) for k, v in my_switcher.DEFAULT.items()}
        with patch("my_switcher.zipf_frequency", return_value=0.0):
            my_switcher._word_score.cache_clear()
            self.assertEqual(suggest_correction("b", words)[0:2], ("и", "ru"))
        my_switcher._word_score.cache_clear()

    def test_all_six_layout_directions_map_letters(self):
        self.assertEqual(convert("ghbdtn", "en", "ru"), "привет")
        self.assertEqual(convert("ghbdtn", "en", "ua"), "привет")
        self.assertEqual(convert("руддщ", "ru", "en"), "hello")
        self.assertEqual(convert("руддщ", "ua", "en"), "hello")
        self.assertEqual(convert("руддщ", "ru", "ua"), "руддщ")
        self.assertEqual(convert("руддщ", "ua", "ru"), "руддщ")


if __name__ == "__main__":
    unittest.main()
