# Add-on: HTTP / REST API

## Verbs
`GET` reads, `POST` creates, `PUT` replaces, `PATCH` partially updates,
`DELETE` removes. `GET`/`PUT`/`DELETE` are idempotent; `POST` is not.

## Status
`2xx` success: 200/201/204. `3xx` redirect: 301/302/307/308.
`4xx` client error: 400/401/403/404/409/422/429. `5xx` server error:
500/502/503.

## Headers
`Content-Type` = body format (`application/json` or
`application/x-www-form-urlencoded`), `Accept` = response format,
`Authorization` = credentials.

## Auth
Prefer `Authorization: Bearer <token>`; Basic
`Authorization: Basic <base64(user:pass)>` only over HTTPS.
Never log, commit or hardcode secrets: read them from the environment.

## JSON
`curl -sS URL | jq '.'` pretty-prints, `jq '.field'` picks a field,
`jq '.[] | .field'` walks a list. POST:
`curl -sS -X POST URL -H "Content-Type: application/json" -d '{"k":"v"}'`.

## Options
`-L` follows redirects; `-f` fails on HTTP >= 400 so scripts stop;
`-m 10` / `--max-time 10` sets a timeout; `-sS` silent but shows errors.

## Read before write (non-negotiable)
Before a state-changing call (`POST`/`PUT`/`PATCH`/`DELETE`), `GET` the
resource first and confirm the current state. Check status and body, then
write. Never blind-write.
