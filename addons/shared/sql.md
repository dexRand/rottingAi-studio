# Add-on: SQL

## Statements
`SELECT col FROM t WHERE cond ORDER BY col DESC LIMIT 10;`
`INSERT INTO t (a, b) VALUES (?, ?);`
`UPDATE t SET a = ? WHERE id = ?;` / `DELETE FROM t WHERE id = ?;`
Always a `WHERE` on UPDATE/DELETE: run the matching `SELECT` first.

## Joins and aggregates
`INNER JOIN` keeps matching rows only; `LEFT JOIN` keeps every left row
(NULLs on the right); `RIGHT`/`FULL` are rarer.
Join on keys: `ON a.id = b.a_id`. `WHERE` filters rows before grouping,
`HAVING` filters groups after `GROUP BY`; then `ORDER BY` and `LIMIT`.
`COUNT(*)`, `SUM`, `AVG`, `MIN`, `MAX`; `DISTINCT` only when needed.

## Schema
Index the columns used by `WHERE`/`JOIN`/`ORDER BY` on large tables; indexes
cost writes and disk. `PRIMARY KEY`, `UNIQUE`, `NOT NULL`, `FOREIGN KEY` with
`ON DELETE`. Read `EXPLAIN` (or `EXPLAIN ANALYZE`) before optimizing.

## Transactions
`BEGIN; ... COMMIT;` or `ROLLBACK;`: all or nothing, keep them short.
Use `SELECT ... FOR UPDATE` to lock rows a writer will change.

## Security (non-negotiable)
- ALWAYS parameterized queries: `execute("... WHERE id = ?", (id,))` (sqlite3),
  `%s` (psycopg, MySQL), `:name` (SQLAlchemy). The driver escapes the values.
- NEVER build SQL with f-strings, `+`, `%` or `format` from user input: that is
  SQL injection. Also validate types and lengths at the boundary.
- Identifiers (table/column names) cannot be parameters: use an allow-list.
- Escape LIKE wildcards in user input (`\%`, `\_`) or use the driver's quoting.
