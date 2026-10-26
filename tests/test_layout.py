import unittest
import my_switcher

class LayoutMappingTests(unittest.TestCase):
    def test_russian_layout_euye_to_test(self):
        self.assertEqual(my_switcher.convert("еуые", "ru", "en"), "test")

    def test_english_test_to_russian_layout(self):
        self.assertEqual(my_switcher.convert("test", "en", "ru"), "еуые")

if __name__ == "__main__":
    unittest.main()
