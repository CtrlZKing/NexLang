# NexLang Grammar (Phase 1)

This documents exactly what `compiler/parser/parser.py` implements today.
EBNF-ish notation: `|` = alternation, `[]` = optional, `{}` = zero-or-more,
`NEWLINE` = a statement-terminating newline.

```
program        := { statement }

statement      := var_declaration
                | assignment
                | compound_assignment
                | say_statement
                | ask_statement
                | if_statement
                | while_statement
                | repeat_statement
                | "BREAK" NEWLINE
                | "CONTINUE" NEWLINE
                | increase_decrease
                | expression_statement

var_declaration := "SET" IDENT { "," IDENT } "TO" expression { "," expression } NEWLINE

assignment      := IDENT "=" expression NEWLINE

compound_assignment := IDENT compound_op expression NEWLINE
compound_op     := "+=" | "-=" | "*=" | "/=" | "//=" | "%="

increase_decrease := ("INCREASE" | "DECREASE") IDENT "BY" expression NEWLINE

say_statement   := "SAY" expression NEWLINE

ask_statement   := "ASK" expression "INTO" IDENT NEWLINE

if_statement    := "IF" expression "THEN" NEWLINE block
                    { "ELSE" "IF" expression "THEN" NEWLINE block }
                    [ "OTHERWISE" NEWLINE block ]
                    "END"

while_statement := "WHILE" expression NEWLINE block "END"

repeat_statement := "REPEAT" expression "TIMES" NEWLINE block "END"
                   | "REPEAT" "UNTIL" expression NEWLINE block "END"

expression_statement := expression NEWLINE

block           := { statement }

expression      := or_expr

or_expr         := and_expr { "OR" and_expr }
and_expr        := not_expr { "AND" not_expr }
not_expr        := "NOT" not_expr | comparison

comparison      := additive [ comparison_tail ]
comparison_tail := "==" additive | "!=" additive
                 | "<" additive  | ">" additive
                 | "<=" additive | ">=" additive
                 | "IS" "NOT" additive
                 | "IS" "AT" "LEAST" additive
                 | "IS" "AT" "MOST" additive
                 | "IS" "ABOVE" additive
                 | "IS" "BELOW" additive
                 | "IS" additive

additive        := multiplicative { ("+" | "-") multiplicative }
multiplicative  := unary { ("*" | "/" | "//" | "%") unary }
unary           := "-" unary | power
power           := primary [ "**" unary ]         # right-associative

primary         := NUMBER
                 | STRING                          # may contain {expr} interpolation
                 | "TRUE" | "FALSE" | "NOTHING"
                 | IDENT
                 | "(" expression ")"
```

## Notes

- Keywords are matched case-insensitively at the lexer level, but the
  formatter (Phase 5) will standardize on UPPERCASE.
- A statement ends at a `NEWLINE`, or at end-of-file. There is currently no
  explicit statement separator like `;`.
- Comparison operators are **not chainable** (`a < b < c` is not special-cased
  and will parse as `(a < b) < c`, which will usually be a NX204 type error
  since booleans aren't numeric). Chained comparisons may be reconsidered in
  a later phase.
- String interpolation is resolved at evaluation time, not parse time: the
  parser only detects that a string contains `{` and `}` and defers the
  actual sub-expression parsing to the interpreter (`InterpolatedString`
  node). This keeps the main grammar clean.

Not yet part of the grammar (planned - see docs/ROADMAP.md): function
declarations/calls, list/map/set/tuple literals, `FOR EACH`, `MATCH`/`CASE`,
`CLASS`, `TRY`/`CATCH`, `IMPORT`, decorators, pipelines, optional chaining.
