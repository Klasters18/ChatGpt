import io
import json
import unittest
from unittest.mock import patch

import grammar_check


class GrammarCheckTests(unittest.TestCase):
    def test_language_codes_are_supported(self):
        self.assertEqual(grammar_check.LANGUAGES, {
            "ru": "ru-RU", "ua": "uk-UA", "en": "en-US"
        })

    def test_empty_text_does_not_make_network_request(self):
        with patch("grammar_check.urllib.request.urlopen") as urlopen:
            self.assertEqual(grammar_check.check_text("  ", "ru"), [])
            urlopen.assert_not_called()

    def test_rejects_unknown_language(self):
        with self.assertRaises(ValueError):
            grammar_check.check_text("hello", "fr")

    def test_parses_language_tool_response(self):
        payload = {
            "matches": [{
                "offset": 0,
                "length": 5,
                "message": "Possible spelling mistake",
                "shortMessage": "Spelling",
                "replacements": [{"value": "hello"}, {"value": "hullo"}],
                "rule": {
                    "id": "MORFOLOGIK_RULE_EN_US",
                    "category": {"name": "Possible Typo"}
                }
            }]
        }
        response = io.BytesIO(json.dumps(payload).encode("utf-8"))
        with patch("grammar_check.urllib.request.urlopen", return_value=response) as urlopen:
            result = grammar_check.check_text("helo", "en")
        self.assertEqual(result[0]["replacements"], ["hello", "hullo"])
        self.assertEqual(result[0]["offset"], 0)
        request = urlopen.call_args.args[0]
        self.assertIn(b"language=en-US", request.data)

    def test_network_error_is_friendly(self):
        with patch("grammar_check.urllib.request.urlopen", side_effect=TimeoutError):
            with self.assertRaises(grammar_check.GrammarServiceError):
                grammar_check.check_text("This are wrong.", "en")


if __name__ == "__main__":
    unittest.main()
