import unittest
import my_switcher

class LayoutMappingTests(unittest.TestCase):
    def test_russian_layout_euye_to_test(self):
        self.assertEqual(my_switcher.convert("еуые", "ru", "en"), "test")

    def test_english_test_to_russian_layout(self):
        self.assertEqual(my_switcher.convert("test", "en", "ru"), "еуые")

    def test_english_gibberish_corrects_to_russian_verb(self):
        result = my_switcher.suggest_correction("ghjdthbnm")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "проверить")
        self.assertEqual(result[1], "ru")

    def test_english_gibberish_corrects_to_russian_greeting(self):
        result = my_switcher.suggest_correction("ghbdtn")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "привет")
        self.assertEqual(result[1], "ru")

    def test_english_gibberish_corrects_to_ukrainian_greeting(self):
        result = my_switcher.suggest_correction("ghbdsn")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "привіт")
        self.assertEqual(result[1], "ua")

    def test_valid_english_is_not_changed(self):
        self.assertIsNone(my_switcher.suggest_correction("hello"))

    def test_valid_russian_is_not_changed(self):
        self.assertIsNone(my_switcher.suggest_correction("привет"))

    def test_mixed_script_is_not_changed(self):
        self.assertIsNone(my_switcher.suggest_correction("pyтhon"))

if __name__ == "__main__":
    unittest.main()
