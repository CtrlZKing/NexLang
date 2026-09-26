from unittest.mock import patch

from cli import main as cli_main


def test_no_args_launches_ide_not_usage(capsys):
    """`nex` with no arguments must launch the IDE (PART 3), not print
    usage/return an error like it used to."""
    with patch("cli.main.cmd_ide", return_value=0) as mock_ide:
        code = cli_main.main([])
    assert code == 0
    mock_ide.assert_called_once()


def test_ide_subcommand_also_launches_ide(capsys):
    with patch("cli.main.cmd_ide", return_value=0) as mock_ide:
        code = cli_main.main(["ide"])
    assert code == 0
    mock_ide.assert_called_once()


def test_ide_launches_web_ide_with_optional_path(capsys):
    """`nex ide <file>` and bare `cmd_ide(path)` must call the real
    NexIDE web launcher (not a second, fake implementation) - see
    docs/IDE_IDENTITY.md for why this replaced the old Tkinter GUI.
    The launcher itself opens a real browser window and blocks until
    it's closed, so it's mocked here rather than actually invoked."""
    with patch("ide.web.launcher.launch_web_ide") as mock_launch:
        code = cli_main.cmd_ide("some_file.nex")
    assert code == 0
    mock_launch.assert_called_once_with("some_file.nex")


def test_repl_and_run_and_check_still_work(tmp_path, capsys):
    """Regression check: adding `nex`/`nex ide` must not disturb the
    existing commands (PART 8 - keep CLI support)."""
    path = tmp_path / "hello.nex"
    path.write_text('SAY "Hello"')
    assert cli_main.main(["run", str(path)]) == 0
    assert "Hello" in capsys.readouterr().out
    assert cli_main.main(["check", str(path)]) == 0
    assert "No syntax errors" in capsys.readouterr().out
    assert cli_main.main(["version"]) == 0
