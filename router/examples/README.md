# Router examples

- `smoke.jsonl` — **illustrative**: hand-written cases matching the keyword
  rules. Its score is not independent evidence (same hand writes rules and
  cases), so it only guards against regressions.
- `real.jsonl` — **real user prompts**, the eval that matters. CTF cases come
  from the user's actual challenges (~/Downloads/CTF). `coding` and `sysadmin`
  cases must be filled in from real usage (5-10 each).

Run: `./ai route-eval router/examples/real.jsonl -v`
