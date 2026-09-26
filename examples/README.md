# NexLang Examples

`hello.nex`, `variables.nex`, `conditions.nex`, `loops.nex`, and
`calculator.nex` cover Phase 1. `functions.nex`, `collections.nex`,
`exceptions.nex`, and `files.nex` demonstrate Phase 2 "POWER" (user-defined
functions, lists, TRY/CATCH/FINALLY, and file I/O). `maps_and_more.nex`
demonstrates Phase 3 collections (maps, sets, tuples, slicing).
`types.nex` demonstrates Phase 3b type annotations - try
`nex check examples/types.nex` as well as `nex run` to see the static
checks in action. `errors.nex` is the one exception to "runs cleanly" -
it's designed to fail and demonstrate diagnostic output.

Run any example with:

    nex run examples/<name>.nex

Or check it (syntax + semantic analysis, without running it) with:

    nex check examples/<name>.nex

See `../tests/language/test_examples.py` for the automated checks that keep
these examples honest (they're run as part of `python3 tools/run_tests.py`).
