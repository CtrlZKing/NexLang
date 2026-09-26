# TODO

See docs/PROJECT_STATUS.md for what's actually implemented vs. planned,
and docs/ROADMAP.md for the full phase-by-phase plan. This file is just
the short, prioritized "what's next" list.

## Immediate next candidates (Phase 4, per the project's own development order)

Phase 3's collections (maps/sets/tuples/slicing) and Phase 3b's type
annotations + static semantic analysis (undefined names, duplicate
declarations, arg-count/type mismatches, unreachable code - via `nex
check`) are both DONE - see docs/CHANGELOG.md. Next up:

- [ ] Classes/objects: `CLASS`, constructors, properties, methods, inheritance
- [ ] Enums
- [ ] Pattern matching (`MATCH`/`CASE`)

## Leftover from earlier phases (still not started)

- [ ] Comprehensions: `[x * x FOR x IN numbers]`
- [ ] `FROM ... IMPORT`, `IMPORT ... AS ...`, per-module namespacing *at
      runtime* for `IMPORT` (the static checker already resolves
      imported names for its own analysis - see docs/PROJECT_STATUS.md -
      but the interpreter still uses one flat global namespace)
- [ ] Keyword arguments and variadic parameters for functions (explicitly deferred in Phase 2)
- [ ] Lambdas/anonymous functions

## Housekeeping (do alongside any of the above, not instead of)

- [ ] Decide whether `TRY`/`CATCH` should let NX999 internal errors pass through uncaught (see docs/PROJECT_STATUS.md "Known limitations")
- [ ] Formatter and linter (directories exist, no logic yet)
- [ ] Reconsider whether a `{1, 2, 3}` set literal is worth a disambiguation rule against `{}` (currently `SET_OF([1,2,3])` only, by design)
- [ ] Widen the type checker's inference (currently: literals, simple arithmetic/comparisons, annotated names, calls to `RETURNS`-annotated functions only - see docs/PROJECT_STATUS.md)
- [ ] Make `IMPORT` resolution in the checker recurse into the imported file's own imports (currently one level deep only)
- [ ] Decide whether type annotations should ever be enforced at runtime, not just checked statically (currently an explicit non-goal - see docs/ROADMAP.md's Phase 3b entry)

## Explicitly not started (later phases - do not attempt before the above)

Bytecode/VM, async/concurrency, package manager, LSP, NexGame, NexWeb,
NexGUI, native compilation, self-hosting. See docs/ROADMAP.md.
