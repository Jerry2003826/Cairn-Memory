import re
import sys
import tomllib
from pathlib import Path

import pytest

from omni import cli


REPO_ROOT = Path(__file__).resolve().parents[1]


def _help_output(capsys: pytest.CaptureFixture[str], *args: str) -> str:
    with pytest.raises(SystemExit) as exc:
        cli.main([*args, "--help"])
    assert exc.value.code == 0
    return capsys.readouterr().out


def test_top_level_help_includes_cli_only_v1_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = _help_output(capsys)

    for command in (
        "init",
        "audit",
        "ingest",
        "status",
        "doctor",
        "eval",
        "outcome",
        "experience",
        "failure",
        "preference",
        "task",
        "project",
        "verify",
        "render",
        "inject",
        "review",
    ):
        assert command in output


def test_top_level_help_uses_cairn_as_primary_program_name(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = _help_output(capsys)

    assert output.startswith("usage: cairn ")


def test_legacy_omni_parser_help_remains_available() -> None:
    output = cli.build_parser(prog="omni").format_help()

    assert output.startswith("usage: omni ")


@pytest.mark.parametrize("command_name", ("cairn", "omni"))
def test_console_entrypoint_help_uses_invoked_program_name(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    command_name: str,
) -> None:
    monkeypatch.setattr(sys, "argv", [command_name, "--help"])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 0
    assert capsys.readouterr().out.startswith(f"usage: {command_name} ")


def test_top_level_help_keeps_internal_commands_hidden(
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = _help_output(capsys)

    for command in ("hook", "parse", "run"):
        assert re.search(rf"^\s+{command}\s", output, flags=re.MULTILINE) is None


def test_version_uses_cairn_memory_package_name(
    capsys: pytest.CaptureFixture[str],
) -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = pyproject["project"]["version"]

    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])

    assert exc.value.code == 0
    assert capsys.readouterr().out == f"cairn-memory {version}\n"


def test_audit_and_ingest_help_are_discoverable(
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit_output = _help_output(capsys, "audit")
    ingest_output = _help_output(capsys, "ingest")

    assert "secrets" in audit_output
    assert "--transcript" in ingest_output
    assert "--run-id" in ingest_output
    assert "--engine" in ingest_output
    assert "claude" in ingest_output
    assert "opencode" in ingest_output


def test_packaging_exposes_cairn_command_with_omni_compatibility() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["name"] == "cairn-memory"
    assert pyproject["project"]["scripts"]["cairn"] == "omni.cli:main"
    assert pyproject["project"]["scripts"]["omni"] == "omni.cli:main"
