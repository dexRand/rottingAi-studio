# Add-on: Git

## Daily flow
`git status` → `git diff` (unstaged) / `git diff --staged` → `git add -p`
→ `git commit -m "type: message"` → `git push`. `git pull --rebase` before
pushing on a shared branch.

## Branches
`git switch -c feat/x` or `git checkout -b feat/x` to create and move;
`git switch main` to go back; `git branch -d x` once merged.
Merge keeps history and adds a merge commit; rebase replays your commits on a
new base for a linear history: `git rebase main` only on your own unpushed branch.
`git cherry-pick <sha>` copies one commit; `git bisect start` +
`git bisect good/bad` finds the breaking commit.

## Undo
- `git restore file` discards unstaged changes; `git restore --staged file`
  unstages. Older form: `git checkout -- file`.
- `git reset --soft HEAD~1` keeps changes staged; `--mixed` keeps them unstaged;
  `--hard` deletes them (irreversible).
- `git revert <sha>` undoes a pushed commit with a new commit, safe on shared branches.
- `git stash push -m "wip"` / `git stash pop`.

## Remotes
`git remote -v`; `git fetch --all --prune`; `git push -u origin <branch>`;
`git log --oneline --graph --all`.

## Rules
- Atomic commits: one logical change; the message says why, not only what.
- Never rewrite pushed history (`reset --hard`, `rebase`, `push --force`):
  use `revert`. `--force-with-lease` only on your own branch, after a fetch.
- Never `git add .` blindly: stage what you touched (`git add -p`) and read
  `git status` before committing. Never commit secrets or large binaries.
