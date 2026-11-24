# Add-on: Bash scripting

## Skeleton
```bash
#!/usr/bin/env bash
set -euo pipefail
cleanup() { rm -f "$tmp"; }
tmp=$(mktemp)
trap cleanup EXIT
main() { ...; }
main "$@"
```

## Quoting
Double-quote expansions: `"$var"`, `"$@"`, `"${arr[@]}"`. Use `"$@"`, never
`"$*"`. Prefer `$(...)` over backticks; keep `local x="$(cmd)"` on its own
line so failures are not masked.

## Tests
Use `[[ ... ]]`, not `[ ... ]`: no word splitting, supports `&&`, `=~`, `-f`.
Quote the right side of `=`; numbers with `-eq`, strings with `==`.

## Errors and exit codes
`-e` exits on failure, `-u` on unset variables, `-o pipefail` catches pipe
failures. Exit 0 = success, 1 = generic, 2 = misuse. Handle errors: `cmd ||
{ echo "failed" >&2; exit 1; }`. Errors go to stderr. `trap` on EXIT always
cleans up, even on failure.

## Functions
Small functions with `local` variables; validate `$#` and arguments; return
status with `return`, data via stdout. End with `main "$@"`.

## Shellcheck
Run `shellcheck script.sh`, fix every warning; silence one only with a
justified `# shellcheck disable=...`.
