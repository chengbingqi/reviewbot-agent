# Security Rules

## Hard-coded Secret Risk

Do not hard-code API keys, tokens, passwords, or database connection strings in
source code. Read secrets from environment variables or a secret manager.

## SQL Injection Risk

Do not build SQL statements by concatenating user input or interpolating raw
strings. Use parameterized queries provided by the database driver.

## Dangerous Function Calls

Avoid unsafe calls such as `eval`, `exec`, unsafe deserialization, and shell
execution with untrusted input. Prefer explicit parsing and constrained command
arguments.
