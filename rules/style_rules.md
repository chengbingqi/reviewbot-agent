# Style Rules

## Naming Convention

Use clear snake_case names for Python functions and variables. Avoid ambiguous
short names except for narrow loop variables.

## Exception Handling

Catch specific exceptions, keep error messages actionable, and avoid swallowing
exceptions silently. Log recoverable failures with enough context to debug.

## Function Size

Keep functions focused on one responsibility. Extract helper functions when a
block mixes parsing, I/O, business logic, and formatting.
