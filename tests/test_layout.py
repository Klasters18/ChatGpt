import unittest
from layout_engine import convert


class LegacyLayoutRegressionTests(unittest.TestCase):
    def test_russian_layout_euye_to_test(self):
        self.assertEqual(convert("еуые", "ru", "en"), "test")

    def test_english_test_to_russian_layout(self):
        self.assertEqual(convert("test", "en", "ru"), "еуые")

    def test_mixed_script_is_detected_as_mixed(self):
        from layout_engine import script_of
        self.assertEqual(script_of("pyтhon"), "mixed")


if __name__ == "__main__":
    unittest.main()
