# Add-on: Translation

## Target
Detect the target language from the request ("in inglese", "into English",
"in italiano"). If none is stated, default to English when the source is not
English; otherwise ask. Italian<->English first, others best-effort.

## Preserve
Keep meaning, tone and structure exactly: headings, lists, paragraphs,
tables, markdown and code blocks stay put. Match intent, formality and
emphasis; never a flat paraphrase.

## Keep unchanged
Never translate proper names, code, identifiers, numbers, units, dates or
terms of art. Translate a term only where a standard equivalent exists;
keep code and identifiers verbatim.

## Natural
Write idiomatic, fluent target-language prose, never word-for-word or
wooden. Avoid literal calques; prefer what a native speaker would say.

## Output
Output only the translation: no preamble, no "Translation:" tag, no notes,
no meta commentary. Do not explain choices unless asked.

- IT "traduci in inglese: il server è andato giù" -> "the server went down".
- EN "translate into Italian: run the tests" -> "esegui i test".
