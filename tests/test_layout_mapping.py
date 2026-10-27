import unittest

from my_switcher import convert


class LayoutMappingTests(unittest.TestCase):
    def test_english_layout_to_russian_with_comma_letter(self):
        self.assertEqual(convert("hf,jns", "en", "ru"), "работы")

    def test_english_layout_to_russian_hello(self):
        self.assertEqual(convert("ghbdtn", "en", "ru"), "привет")

    def test_english_layout_to_english_is_identity_for_test(self):
        self.assertEqual(convert("test", "en", "en"), "test")


if __name__ == "__main__":
    unittest.main()
