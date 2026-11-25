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

`feat/12-single-model-router` · `fix/34-role-mapping` · `docs/8-architecture` · `chore/…` · `refactor/…`

Never commit directly to `main`.

## Commits

- Small and atomic: one logical change per commit.
- Imperative, lowercase summary, like the existing history:
  `README: document the ctf-docker link` — not "updated readme".
- Never commit `.env`, model files (`*.gguf` / `*.bin`), or `runtime/` state.

## Keep docs and API in sync

A change is not done until its docs are. In the same PR, update:

- **README** (`README.md` + `README.it.md`) — new/changed commands, roles, ports, add-ons, requirements.
- **`docs/`** — architecture, models, upgrading, troubleshooting: keep them true to reality.
- **API surface** — endpoints (`/v1`, `/router/status`), headers, ports, and the MCP config
  (`config/opencode/opencode.jsonc`, `.env.example`): if you add or change one, document it.
- **`CLAUDE.md`** and any vendored skill you touched.

## Pull requests

- Push your branch and open a PR against `main`.
- Reference the issue in the body with `Closes #<n>`.
- One PR per issue, kept small and reviewable.
- Run the checks below before opening the PR.

### When it passes: merge it yourself

Once the workflow is green, **merge the PR yourself** — the author (human or
agent) accepts the PR and merges it into `main`, no need to wait for anyone:

```bash
gh pr merge <PR>        # accept + merge with main
```

A human can still request changes on anything non-trivial, but a green workflow
is enough to merge.

### Model-dependent changes need a local gate

CI can only run the pure-Python checks (`ci.yml`: unit tests, `router-check`,
keyword eval). For anything that changes model behaviour — add-ons, agent tools,
the router — open a `[verify]` issue with a checklist and run it on a machine
that has `llama-server` + a GGUF **before merging**; that is the only way to see
the add-on fire and the model produce decent output.

### After the merge: delete the branch

Once merged (the issue closes by itself via `Closes #<n>`), **delete the branch**
so everyone always branches from the latest `main`:

```bash
git push origin --delete <branch>   # remote
git branch -D <branch>              # local
```

## Checks before a PR

```bash
bash -n scripts/*.sh scripts/ai           # shell syntax
python3 -m unittest discover -s tests     # router unit tests (no models needed)
./ai router-check                         # add-on registry + sizes
./ai test --skills-only                   # skills + config sanity (no models needed)
```

## Red lines

- No secrets or API keys in code or commits — use `.env` (git-ignored).
- No model files in the repo (they live outside, in `MODELS_DIR`).
- Don't touch real/production systems.

## Questions?

Open an issue — even for questions.
