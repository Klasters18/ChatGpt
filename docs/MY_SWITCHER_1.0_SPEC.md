# My Switcher 1.0 — Engineering Specification

Status: implementation baseline / acceptance contract  
Target: Windows 10 and Windows 11, RU / UA / EN  
Principle: layout correction only. Never perform automatic spelling, grammar, or style correction.

## 1. Product requirements

- Support all six layout directions: EN↔RU, EN↔UA, RU↔UA.
- Run locally for layout detection and correction; no network dependency for this function.
- Operate in ordinary editable controls across desktop apps and browsers, subject to documented OS/app security restrictions.
- Preserve correctly typed words, punctuation, whitespace, casing, and mixed-language text.
- Use phrase context and language evidence, not a growing hard-coded word list.
- Support short function words in context (e.g. RU и/к/в/с, UA і/в/у/з). Avoid guessing isolated ambiguous one-character tokens.
- Keep manual grammar/spelling review separate from automatic layout correction.
- Retain tray, enable/disable, startup, exclusions, personal dictionary, undo, and settings persistence.

## 2. Correctness and safety invariants

1. A correction is a transaction: capture target window/thread, source text and delimiter; validate target is still eligible; perform replacement; verify where the control permits; commit history only on success.
2. Never report “replacement completed” merely because input injection returned without raising.
3. Never send Caps Lock as part of a correction. Preserve the user's pre-existing Caps Lock state.
4. Do not synthesize Shift/Caps Lock combinations to change casing. Preserve casing by transforming text before injection.
5. Never change content in password/secure controls, excluded applications, or when focus has moved.
6. On uncertain detection, do nothing.
7. On partial failure, do not blindly retry destructive Backspace operations. Log the state and stop safely.
8. Do not claim universal compatibility: document controls that Windows does not expose or that intercept synthetic input.

## 3. Detection engine

- Evaluate the current token and a bounded context window independently; a bad prior token must not prevent correction of a clearly recoverable current token.
- Score unchanged-language baseline against candidate keyboard mappings for all supported targets.
- Use word frequency, language-specific bigrams, script evidence, keyboard mapping evidence, and user dictionary.
- Make RU/UA discrimination explicit; do not treat all Cyrillic as Russian.
- Support mixed-language sentences by evaluating token-level candidates while retaining phrase context.
- Handle punctuation as separators without feeding punctuation into lexical scoring.
- Keep one-letter tokens context-dependent; never auto-convert an isolated ambiguous one-letter token.
- Add explainable decisions: candidate text, score components, margin, rejection reason.
- Regression tests must cover valid words that happen to resemble another layout.

## 4. Keyboard event and replacement architecture

- Separate physical keyboard observation from injected events; injected events must be tagged/guarded so they cannot re-enter the input buffer.
- Serialize correction transactions. No concurrent listener callbacks may mutate one target control.
- Capture foreground HWND, thread ID, process name, keyboard layout and Caps Lock state at the boundary.
- Recheck foreground target immediately before destructive actions.
- Define and test event ordering for delimiter, deletion, replacement, delimiter restoration, and layout activation.
- Prefer Unicode text injection for corrected text so the target keyboard layout cannot reinterpret characters. Use a Windows SendInput Unicode path or another verified Unicode-capable mechanism; do not assume pynput Controller.type is layout-independent.
- Keep the target layout activation separate from Unicode text injection.
- Preserve the original delimiter exactly (space, tab, enter, punctuation).
- Use a safe fallback when the target control does not accept the selected injection method.
- Undo must reverse only the last verified transaction and must not delete unrelated subsequent user input.

## 5. Caps Lock / Shift

- Sample GetKeyState / GetKeyboardState at key boundaries and immediately before/after injection.
- Record physical Caps Lock key-down/up and synthetic injected key events with an origin marker.
- Record Shift left/right state, modifier combinations, and Caps Lock toggle state.
- Ensure replacement code never emits VK_CAPITAL and does not depend on Caps Lock for case preservation.
- If Caps Lock state changes during a correction and no physical Caps Lock event explains it, flag a programmatic or external state change.
- Do not automatically toggle Caps Lock back without proving the application caused the change; avoid fighting intentional user input.
- Test Caps Lock off/on, Shift, Shift+Caps Lock, rapid typing, and all delimiters.

## 6. App compatibility

Required manual test matrix:
- Telegram Desktop
- Chrome and Edge text inputs / contenteditable
- Firefox text inputs / contenteditable
- Microsoft Word
- Windows Notepad
- Notepad++
- common native Windows edit controls

Test normal text fields, rich-text/contenteditable, multiline controls, and browser forms separately. Respect protected/secure controls and per-app exclusions. Maintain a documented compatibility matrix with observed results rather than claiming every application works.

## 7. Settings and user data

- Preserve %APPDATA%\MySwitcher\settings.json and dictionary.txt across upgrades.
- Back up both before migration or schema changes.
- Migrations must be additive, versioned, and reversible where practical.
- Preserve current exclusions and startup preference.
- Never overwrite the personal dictionary during install or upgrade.

## 8. Diagnostics and privacy

Local debug log should include:
- timestamp, app/process, HWND/thread identifier (avoid storing full sensitive content by default);
- token length and optional redacted/hash identifier;
- candidate language/score breakdown and decision reason;
- correction transaction ID and each stage result;
- focus/layout/Caps Lock/Shift snapshots before and after;
- physical vs injected Caps Lock events;
- exceptions and Win32 error codes.

Do not log passwords, secure-field contents, or full text from protected controls. Detailed text logging must be opt-in and visibly enabled by the user.

## 9. Test strategy

### Unit tests
- All six mapping directions, including punctuation and case preservation.
- Known recoverable words and phrases, including `cyjdf` → `снова`.
- RU/UA distinctions and mixed-language token boundaries.
- One-letter words in context and isolated ambiguity.
- Correctly typed RU/UA/EN text remains unchanged.
- Ordinary typos are not “fixed” by layout conversion.
- Punctuation, repeated spaces, tabs, newline, casing.
- Context reset and focus-change behavior.

### Integration tests
- Keyboard event ordering and injected-event suppression.
- Transaction cancellation when focus changes.
- Unicode injection independent of active layout.
- Undo after verified correction.
- Caps Lock state unchanged by synthetic correction.
- Concurrent rapid boundaries are serialized.

### Manual acceptance tests
- Repeat the same scripted corpus in Telegram, Chrome, Edge, Firefox, Word, Notepad, and Notepad++.
- Include all six directions, mixed text, punctuation, uppercase, Caps Lock on/off, Shift, and rapid typing.
- Record OS build, app version, target control type, result, and log correlation ID.

## 10. Release gates

Do not call 1.0 ready until:
- syntax checks and all automated tests pass;
- regression tests prove no false correction on valid RU/UA/EN samples;
- replacement transaction tests pass;
- Caps Lock remains unchanged during injected corrections;
- user settings and dictionary survive install/upgrade;
- installer and startup/tray behavior are verified;
- manual app matrix is completed on the actual Windows machine;
- known limitations are documented.

Build success alone is not acceptance. A passing unit suite alone is not universal app compatibility.
