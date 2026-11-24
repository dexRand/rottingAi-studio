# Add-on: GitHub Actions / CI

## Workflow file
`.github/workflows/<name>.yml` (YAML). Top-level keys: `name`, `on`, `jobs`,
plus `permissions`, `env`, `concurrency`.

## Events (`on`)
`push` (filter with `branches`/`tags`), `pull_request`, `schedule` (cron),
`workflow_dispatch` (manual run). Combine: `on: [push, pull_request]`.

## Jobs and steps
`jobs.<id>` needs `runs-on` (e.g. `ubuntu-latest`) and `steps`. Each step has
`name`, then `run` (shell) or `uses` (an action). Start with
`uses: actions/checkout@v4` to get the repo. Read outputs with
`${{ steps.<id>.outputs.<key> }}`; read secrets with `${{ secrets.NAME }}`.

## Env
`env:` at workflow, job or step scope; narrower wins. Use
`${{ env.NAME }}`, or `$NAME` inside `run`.

## Matrix
`strategy.matrix` runs the job once per combination:
`matrix: { python: ["3.11", "3.12"], os: [ubuntu-latest] }`, read with
`${{ matrix.python }}`. `fail-fast: false` keeps other jobs running.

## Concurrency and cache
`concurrency: { group: ${{ github.ref }}, cancel-in-progress: true }` cancels
superseded runs. `actions/cache` avoids re-downloading dependencies; key on the
lockfile hash.

## Permissions
`permissions:` defaults are broad. Set least privilege, e.g.
`permissions: { contents: read }`; grant `write` only to the job that needs it.

## Rules
- Never hard-code secrets in YAML: use repository/environment secrets.
- Pin third-party actions to a tag or SHA.
