"""LanguageTool-backed spelling and grammar checks for RU, UK and EN.

Text is sent to LanguageTool's public API only when the user presses Check.
"""
import json
import urllib.parse
import urllib.request

API_URL = "https://api.languagetool.org/v2/check"
LANGUAGES = {"ru": "ru-RU", "ua": "uk-UA", "en": "en-US"}

class GrammarServiceError(RuntimeError):
    pass

def check_text(text, language, timeout=12):
    """Return LanguageTool matches; never silently changes the user's text."""
    if language not in LANGUAGES:
        raise ValueError("language must be ru, ua or en")
    if not text or not text.strip():
        return []
    payload = urllib.parse.urlencode({
        "text": text,
        "language": LANGUAGES[language],
        "enabledOnly": "false",
    }).encode("utf-8")
    request = urllib.request.Request(
        API_URL, data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "MySwitcher/0.3"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise GrammarServiceError(
            "Не удалось связаться с сервисом проверки. Проверьте интернет и попробуйте позже."
        ) from exc
    results = []
    for match in data.get("matches", []):
        replacements = [r.get("value", "") for r in match.get("replacements", [])[:5]]
        results.append({
            "offset": int(match.get("offset", 0)),
            "length": int(match.get("length", 0)),
            "message": str(match.get("message", "")),
            "short_message": str(match.get("shortMessage", "")),
            "replacements": replacements,
            "rule_id": str(match.get("rule", {}).get("id", "")),
            "category": str(match.get("rule", {}).get("category", {}).get("name", "")),
        })
    return results
