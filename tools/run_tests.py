"""
NexLang test runner (no external dependencies).

Runs every tests/**/test_*.py file with a minimal pytest-compatible
shim (tools/pytest_shim.py) installed as sys.modules['pytest']. This
exists only because this sandbox has no network access to `pip install
pytest`; the test files themselves are ordinary pytest tests and will
run unmodified under real pytest once it's available:

    pip install pytest
    pytest tests/

Usage:
    python3 tools/run_tests.py
"""
import os
import sys
import glob
import importlib.util
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pytest_shim
pytest_shim.install()
from pytest_shim import Skipped


def discover_test_functions(module):
    return [
        (name, getattr(module, name))
        for name in dir(module)
        if name.startswith("test_") and callable(getattr(module, name))
    ]


def _resolve_fixture(module, name, cache, teardowns):
    """Resolve a fixture by name (module-level function decorated with
    @pytest.fixture, or the built-in capsys/tmp_path), recursively
    resolving its own parameters, and remembering generator-based
    fixtures in `teardowns` so their post-yield code runs after the test."""
    if name in cache:
        return cache[name]

    if name == "capsys":
        cap = pytest_shim.make_capsys()
        cap.__enter__()
        teardowns.append(("capsys_exit", cap))
        cache[name] = cap
        return cache[name]

    if name == "tmp_path":
        import tempfile, pathlib
        d = tempfile.mkdtemp(prefix="nexlang_test_")
        teardowns.append(("rmtree", d))
        cache[name] = pathlib.Path(d)
        return cache[name]

    fixture_fn = getattr(module, name, None)
    if fixture_fn is None or not getattr(fixture_fn, "__is_fixture__", False):
        raise LookupError(f"no fixture named {name!r} found")

    import inspect
    sub_params = list(inspect.signature(fixture_fn).parameters)
    kwargs = {p: _resolve_fixture(module, p, cache, teardowns) for p in sub_params}

    if inspect.isgeneratorfunction(fixture_fn):
        gen = fixture_fn(**kwargs)
        value = next(gen)
        teardowns.append(("gen", gen))
    else:
        value = fixture_fn(**kwargs)

    cache[name] = value
    return value


def run_one(fn, module=None):
    """Run a single test function, expanding @pytest.mark.parametrize
    into one call per parameter set, honoring skipif markers, and
    resolving fixtures (capsys/tmp_path plus any @pytest.fixture defined
    in the test's own module) - including yield-based teardown."""
    import inspect
    skipif = getattr(fn, "__nex_skipif__", None)
    if skipif and skipif[0]:
        return "SKIP", skipif[1]

    params = list(inspect.signature(fn).parameters)
    parametrize = getattr(fn, "__nex_parametrize__", None)
    parametrize_names = set()
    if parametrize:
        argnames, _ = parametrize
        parametrize_names = {n.strip() for n in argnames.split(",")} if isinstance(argnames, str) else set(argnames)
    fixture_params = [p for p in params if p not in parametrize_names]

    def call(**extra_kwargs):
        cache = {}
        teardowns = []
        try:
            kwargs = dict(extra_kwargs)
            for p in fixture_params:
                if p not in kwargs:
                    kwargs[p] = _resolve_fixture(module, p, cache, teardowns)
            fn(**kwargs)
        finally:
            import shutil
            for kind, obj in reversed(teardowns):
                try:
                    if kind == "gen":
                        next(obj)
                    elif kind == "rmtree":
                        shutil.rmtree(obj, ignore_errors=True)
                    elif kind == "capsys_exit":
                        obj.__exit__(None, None, None)
                except StopIteration:
                    pass

    if parametrize:
        argnames, argvalues = parametrize
        names = [n.strip() for n in argnames.split(",")] if isinstance(argnames, str) else list(argnames)
        for values in argvalues:
            values = values if isinstance(values, (tuple, list)) else (values,)
            call(**dict(zip(names, values)))
        return "PASS", None

    call()
    return "PASS", None


def main():
    test_dir = os.path.join(ROOT, "tests")
    files = sorted(glob.glob(os.path.join(test_dir, "**", "test_*.py"), recursive=True))

    total, passed, skipped, failed = 0, 0, 0, []
    for path in files:
        rel = os.path.relpath(path, ROOT)
        modname = rel.replace(os.sep, ".")[:-3]
        try:
            spec = importlib.util.spec_from_file_location(modname, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[modname] = module
            spec.loader.exec_module(module)
        except Skipped as e:
            print(f"  SKIP  {rel} (module-level): {e}")
            continue
        except Exception as e:
            print(f"  ERROR {rel} (import failed): {e}")
            failed.append((rel, "<module import>", e, traceback.format_exc()))
            continue

        module_skip = getattr(module, "pytestmark", None)
        module_skip_reason = None
        if module_skip is not None and getattr(module_skip, "__class__", None).__name__ == "_Skipif":
            if module_skip.condition:
                module_skip_reason = module_skip.reason

        for name, fn in discover_test_functions(module):
            total += 1
            if module_skip_reason is not None:
                print(f"  SKIP  {rel}::{name} ({module_skip_reason})")
                skipped += 1
                continue
            try:
                status, reason = run_one(fn, module)
                if status == "SKIP":
                    print(f"  SKIP  {rel}::{name} ({reason})")
                    skipped += 1
                else:
                    print(f"  PASS  {rel}::{name}")
                    passed += 1
            except Skipped as e:
                print(f"  SKIP  {rel}::{name} ({e})")
                skipped += 1
            except Exception as e:
                print(f"  FAIL  {rel}::{name}: {e}")
                failed.append((rel, name, e, traceback.format_exc()))

    print()
    print(f"{passed} passed, {skipped} skipped, {len(failed)} failed, out of {total} collected")
    if failed:
        print(f"\n{len(failed)} FAILURES:")
        for rel, name, e, tb in failed:
            print(f"\n--- {rel}::{name} ---")
            print(tb)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
