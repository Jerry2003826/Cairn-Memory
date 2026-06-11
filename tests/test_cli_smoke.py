from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_omni(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "omni.cli", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_init_creates_layout_and_is_idempotent(tmp_path: Path) -> None:
    first = run_omni(tmp_path, "init")
    second = run_omni(tmp_path, "init")

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr

    omni_dir = tmp_path / ".omni"
    assert omni_dir.is_dir()
    for dirname in ("spool", "spike", "artifacts", "generated"):
        assert (omni_dir / dirname).is_dir()
    assert (omni_dir / "config.toml").read_text(encoding="utf-8")

    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert gitignore.count(".omni/generated/") == 1


def test_init_does_not_modify_claude_settings(tmp_path: Path) -> None:
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    settings = claude_dir / "settings.json"
    original = '{"hooks":[]}\n'
    settings.write_text(original, encoding="utf-8")

    result = run_omni(tmp_path, "init")

    assert result.returncode == 0, result.stderr
    assert settings.read_text(encoding="utf-8") == original
    assert not (claude_dir / "settings.json.omni-bak").exists()


def test_cli_help_smoke(tmp_path: Path) -> None:
    result = run_omni(tmp_path, "--help")

    assert result.returncode == 0
    assert "init" in result.stdout
