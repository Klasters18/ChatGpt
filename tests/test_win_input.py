import unittest
from unittest.mock import patch

import win_input


class UnicodeInputTests(unittest.TestCase):
    def test_unicode_text_uses_unicode_packets_not_caps_lock_or_shift(self):
        with patch.object(win_input, "_send", return_value=4) as send:
            result = win_input.send_unicode_text("снова")
        self.assertEqual(result, 4)
        events = send.call_args.args[0]
        self.assertEqual(len(events), 10)
        self.assertTrue(all(event.type == win_input.INPUT_KEYBOARD for event in events))
        self.assertTrue(all(event.ki.wVk == 0 for event in events))
        self.assertTrue(all(event.ki.dwFlags & win_input.KEYEVENTF_UNICODE for event in events))
        self.assertFalse(any(event.ki.wVk == 0x14 for event in events))

    def test_backspace_uses_only_backspace_key_events(self):
        with patch.object(win_input, "_send", return_value=4) as send:
            result = win_input.send_backspaces(2)
        self.assertEqual(result, 4)
        events = send.call_args.args[0]
        self.assertEqual(len(events), 4)
        self.assertTrue(all(event.ki.wVk == win_input.VK_BACK for event in events))
        self.assertFalse(any(event.ki.wVk == 0x14 for event in events))

    def test_supplementary_unicode_uses_surrogate_pair(self):
        with patch.object(win_input, "_send", return_value=4) as send:
            win_input.send_unicode_text("😀")
        events = send.call_args.args[0]
        self.assertEqual([e.ki.wScan for e in events], [0xD83D, 0xD83D, 0xDE00, 0xDE00])


if __name__ == "__main__":
    unittest.main()
