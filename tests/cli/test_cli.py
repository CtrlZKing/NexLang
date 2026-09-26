import os
import sys
import pytest
from cli import main as cli_main


def write_nex(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content)
    return str(path)


def test_version(capsys):
    code = cli_main.main(["version"])
    out = capsys.readouterr().out
    assert code == 0
    assert "NexLang" in out
    assert cli_main.VERSION in out


def test_run_hello_world(tmp_path, capsys):
    path = write_nex(tmp_path, "hello.nex", 'SAY "Hello, World!"')
    code = cli_main.main(["run", path])
    out = capsys.readouterr().out
    assert code == 0
    assert out == "Hello, World!\n"


def test_run_shorthand(tmp_path, capsys):
    path = write_nex(tmp_path, "hello.nex", 'SAY "Hi"')
    code = cli_main.main([path])
    out = capsys.readouterr().out
    assert code == 0
    assert out == "Hi\n"


def test_run_missing_file(capsys):
    code = cli_main.main(["run", "does_not_exist.nex"])
    out = capsys.readouterr().out
    assert code == 1
    assert "not found" in out


def test_check_valid_program(tmp_path, capsys):
    path = write_nex(tmp_path, "ok.nex", "SET x TO 10\nSAY x")
    code = cli_main.main(["check", path])
    out = capsys.readouterr().out
    assert code == 0
    assert "No syntax errors" in out


def test_check_invalid_program_reports_error(tmp_path, capsys):
    path = write_nex(tmp_path, "bad.nex", "IF x IS 1 THEN\nSAY x")
    code = cli_main.main(["check", path])
    err = capsys.readouterr().err
    assert code == 1
    assert "NX203" in err


def test_check_reports_semantic_errors_not_just_syntax(tmp_path, capsys):
    path = write_nex(tmp_path, "bad.nex", "SAY totally_unknown_name")
    code = cli_main.main(["check", path])
    err = capsys.readouterr().err
    assert code == 1
    assert "NX401" in err


def test_check_reports_type_mismatch(tmp_path, capsys):
    path = write_nex(tmp_path, "bad.nex", 'SET age AS NUMBER TO "fifteen"')
    code = cli_main.main(["check", path])
    err = capsys.readouterr().err
    assert code == 1
    assert "NX405" in err


def test_check_prints_unreachable_code_as_warning_not_failure(tmp_path, capsys):
    path = write_nex(tmp_path, "warn.nex", 'FUNCTION f()\n    RETURN 1\n    SAY "dead"\nEND\n')
    code = cli_main.main(["check", path])
    out = capsys.readouterr().out
    assert code == 0  # a warning does not fail the check
    assert "No syntax errors" in out
    assert "warning" in out.lower()


def test_runtime_error_reported_on_stderr(tmp_path, capsys):
    path = write_nex(tmp_path, "err.nex", "SAY undefined_variable")
    code = cli_main.main(["run", path])
    err = capsys.readouterr().err
    assert code == 1
    assert "NX301" in err


def test_unknown_command_suggests_alternative(capsys):
    code = cli_main.main(["rn"])
    out = capsys.readouterr().out
    assert code == 1
    assert "Unknown command" in out
    assert "run" in out


def test_planned_command_is_honest_about_not_being_implemented(capsys):
    code = cli_main.main(["install"])
    out = capsys.readouterr().out
    assert code == 2
    assert "planned but not implemented" in out


def test_help_topic(capsys):
    code = cli_main.main(["help", "variables"])
    out = capsys.readouterr().out
    assert code == 0
    assert "SET" in out


def test_help_no_args_shows_usage(capsys):
    code = cli_main.main(["help"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Usage:" in out
