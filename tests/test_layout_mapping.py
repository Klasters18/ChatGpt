import unittest
from layout_engine import convert


class LayoutMappingTests(unittest.TestCase):
    def test_all_six_layout_directions(self):
        self.assertEqual(convert("ghbdtn", "en", "ru"), "привет")
        self.assertEqual(convert("ghbdtn", "en", "ua"), "привет")
        self.assertEqual(convert("руддщ", "ru", "en"), "hello")
        self.assertEqual(convert("руддщ", "ua", "en"), "hello")
        self.assertEqual(convert("руддщ", "ru", "ua"), "руддщ")
        self.assertEqual(convert("руддщ", "ua", "ru"), "руддщ")
        self.assertEqual(convert("хъ", "ru", "ua"), "їх")
        self.assertEqual(convert("їх", "ua", "ru"), "хъ")
        self.assertEqual(convert("привыт", "ru", "ua"), "привіт")

    def test_punctuation_key_can_be_a_letter(self):
        self.assertEqual(convert("hf,jns", "en", "ru"), "работы")

    def test_case_is_preserved_by_mapping(self):
        self.assertEqual(convert("Ghbdtn", "en", "ru"), "Привет")


if __name__ == "__main__":
    unittest.main()
