# Contributing to rottingAi-studio

Thanks for helping out. This repo runs on a small, strict workflow so the
history stays clean and every change traces back to a reason.

## The one rule: everything starts with an issue

1. **Open an issue first.** Every change — bug, feature, doc tweak — starts as an
   issue that states *what*, *why*, and *when it is done*.
2. **One issue = one change = one branch = one PR.** Don't bundle unrelated work.
3. **Assign yourself** before starting, so two people don't pick the same thing.

## Branch naming

Branch off `main` for every issue:

```text
<type>/<issue-number>-<short-slug>
```

`feat/12-add-colibri` · `fix/34-role-mapping` · `docs/8-architecture` · `chore/…` · `refactor/…`

Never commit directly to `main`.

## Commits

- Small and atomic: one logical change per commit.
- Imperative, lowercase summary, like the existing history:
  `README: document the ctf-docker link` — not "updated readme".
- Never commit `.env`, model files (`*.gguf` / `*.bin`), or `runtime/` state.

## Pull requests

- Push your branch and open a PR against `main`.
- Reference the issue in the body with `Closes #<n>`.
- One PR per issue, kept small and reviewable.
- Run the checks below before asking for review.
- A maintainer reviews and merges — don't self-merge.

## Checks before a PR

```bash
bash -n scripts/*.sh scripts/ai           # shell syntax
./scripts/orchestrate.py --skills-only    # skills + config sanity (no models needed)
```

## Red lines

- No secrets or API keys in code or commits — use `.env` (git-ignored).
- No model files in the repo (they live outside, in `MODELS_DIR`).
- Don't touch real/production systems.

## Questions?

Open an issue — even for questions.
