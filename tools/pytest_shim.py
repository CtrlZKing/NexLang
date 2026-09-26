"""
Minimal, dependency-free stand-in for the parts of `pytest` this test
suite actually uses (pytest.raises, pytest.mark.parametrize,
pytest.mark.skipif, pytest.importorskip). Installed into
sys.modules['pytest'] by tools/run_tests.py so the *exact* test files
in tests/ run unmodified. This sandbox has no network access, so a
real `pip install pytest` was not possible - once it is, delete this
shim and run real pytest instead; nothing in tests/ needs to change.
"""
import importlib
import types


class Skipped(Exception):
    pass


class _RaisesContext:
    def __init__(self, exc_type):
        self.exc_type = exc_type
        self.value = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            raise AssertionError(f"expected {self.exc_type.__name__} to be raised, but nothing was raised")
        if not issubclass(exc_type, self.exc_type):
            return False
        self.value = exc_val
        return True


class _Mark:
    class _Parametrize:
        def __init__(self, argnames, argvalues):
            self.argnames = argnames
            self.argvalues = argvalues

        def __call__(self, fn):
            fn.__nex_parametrize__ = (self.argnames, self.argvalues)
            return fn

    class _Skipif:
        def __init__(self, condition, reason=""):
            self.condition = condition
            self.reason = reason

        def __call__(self, fn):
            fn.__nex_skipif__ = (self.condition, self.reason)
            return fn

    def parametrize(self, argnames, argvalues):
        return self._Parametrize(argnames, argvalues)

    def skipif(self, condition, reason=""):
        return self._Skipif(condition, reason)


def raises(exc_type):
    return _RaisesContext(exc_type)


def importorskip(modname):
    try:
        return importlib.import_module(modname)
    except ImportError as e:
        raise Skipped(f"could not import {modname!r}: {e}")


class _CapturedText:
    def __init__(self, out, err):
        self.out = out
        self.err = err


class _CapSys:
    """Minimal stand-in for pytest's built-in `capsys` fixture."""

    def __init__(self):
        import io
        self._stdout = io.StringIO()
        self._stderr = io.StringIO()

    def __enter__(self):
        import sys
        self._real_out, self._real_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = self._stdout, self._stderr
        return self

    def __exit__(self, *exc):
        import sys
        sys.stdout, sys.stderr = self._real_out, self._real_err
        return False

    def readouterr(self):
        out, err = self._stdout.getvalue(), self._stderr.getvalue()
        self._stdout.seek(0)
        self._stdout.truncate()
        self._stderr.seek(0)
        self._stderr.truncate()
        return _CapturedText(out, err)


def fixture(func=None, **kwargs):
    """Minimal stand-in for @pytest.fixture. Supports both plain-return
    and yield-based (setup/teardown) fixture functions."""
    def decorator(f):
        f.__is_fixture__ = True
        return f
    if func is not None:
        return decorator(func)
    return decorator


def make_capsys():
    return _CapSys()


mark = _Mark()


def install():
    import sys
    mod = types.ModuleType("pytest")
    mod.raises = raises
    mod.importorskip = importorskip
    mod.mark = mark
    mod.fixture = fixture
    mod.skip = lambda reason="": (_ for _ in ()).throw(Skipped(reason))
    sys.modules["pytest"] = mod
    return mod
