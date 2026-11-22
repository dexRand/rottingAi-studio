# Add-on: Regular expressions

## Syntax
| Need | Write |
|---|---|
| digit / word / space | `\d` `\w` `\s` (negated `\D` `\W` `\S`) |
| class | `[abc]`, `[a-z0-9_]`, `[^abc]` |
| quantifier | `*` 0+, `+` 1+, `?` 0-1, `{2,5}` |
| anchor | `^` start, `$` end, `(?m)` per line |
| group / alternation | `(a|b)` captures, `(?:a|b)` does not |

## Greedy vs lazy
`.*` takes as much as possible then backtracks; `.*?` as little as possible.
Prefer a negated class: `"([^"]*)"` beats `".*?"`.

## Groups
`(...)` captures (numbered); `(?:...)` only groups; Python names `(?P<n>...)`.
Lookaround is zero-width: `(?=x)` `(?!x)` ahead, `(?<=x)` `(?<!x)` behind
(Python/PCRE2: fixed width).

## Escaping
Escape `\. \* \+ \? \( \) \[ \] \{ \} \| \^ \$`.
Shell: single quotes `'^\d+$'`; Python: raw strings `r"\d+"`; `re.escape()` untrusted input.

## Patterns
email `[\w.+-]+@[\w-]+\.[\w.]+`; IPv4 `\b(?:\d{1,3}\.){3}\d{1,3}\b`;
date `\d{4}-\d{2}-\d{2}`.

## Tools
`rg -P` PCRE2 (lookarounds), `rg -F` literal, `rg -w` word; `grep -E` ERE,
`grep -P` PCRE2; Python `re.search/findall/sub/fullmatch`, compile once;
`sed -E 's/pat/repl/g'` on a copy; `-n` for line numbers.
