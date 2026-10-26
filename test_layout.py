import unittest
from my_switcher import convert
class LayoutTests(unittest.TestCase):
    def test_en_ru(self): self.assertEqual(convert("ghbdtn","en","ru").lower(),"привет")
    def test_ru_en(self): self.assertEqual(convert("руддщ","ru","en").lower(),"hello")
    def test_same(self): self.assertEqual(convert("hello","en","en"),"hello")
if __name__=="__main__": unittest.main()
