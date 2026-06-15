from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from omni import inject


REPO_ROOT = Path(__file__).resolve().parents[1]
MANAGED_REGION = """<!-- omni:begin -->
@.omni/generated/memory.md
<!-- omni:end -->
"""


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


def test_preview_mode_prints_managed_region_without_writing(tmp_path: Path) -> None:
    result = inject.inject_claude(tmp_path, mode="preview")

    assert result.body == MANAGED_REGION
    assert result.wrote is False
    assert not (tmp_path / "CLAUDE.md").exists()


def test_link_mode_writes_managed_region_and_preserves_user_content(tmp_path: Path) -> None:
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("# Project notes\n\nKeep this.\n", encoding="utf-8")

    result = inject.inject_claude(tmp_path, mode="link")
    second = inject.inject_claude(tmp_path, mode="link")
    text = claude_md.read_text(encoding="utf-8")

    assert result.wrote is True
    assert second.wrote is False
    assert text.startswith("# Project notes")
    assert "Keep this." in text
    assert MANAGED_REGION in text
    assert text.count("<!-- omni:begin -->") == 1
    assert text.count("<!-- omni:end -->") == 1


def test_link_refuses_to_overwrite_manually_changed_managed_region(tmp_path: Path) -> None:
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text(
        "# Project notes\n\n<!-- omni:begin -->\nmanual edit\n<!-- omni:end -->\n",
        encoding="utf-8",
    )

    with pytest.raises(inject.ManagedRegionEditedError) as raised:
        inject.inject_claude(tmp_path, mode="link")

    assert "manual edit" in raised.value.diff
    assert claude_md.read_text(encoding="utf-8").count("manual edit") == 1


def test_link_accepts_managed_region_at_eof_without_trailing_newline(
    tmp_path: Path,
) -> None:
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text(MANAGED_REGION.rstrip("\n"), encoding="utf-8")

    result = inject.inject_claude(tmp_path, mode="link")

    assert result.wrote is False
    assert claude_md.read_text(encoding="utf-8") == MANAGED_REGION.rstrip("\n")


def test_opencode_preview_prints_instruction_config_without_writing(tmp_path: Path) -> None:
    result = inject.inject(tmp_path, target="opencode", mode="preview")

    assert result.wrote is False
    assert not (tmp_path / "opencode.json").exists()
    assert '".omni/generated/memory.md"' in result.body


def test_opencode_link_appends_instruction_once_and_preserves_config(tmp_path: Path) -> None:
    config = tmp_path / "opencode.json"
    config.write_text(
        '{"model":"apiyi/qwen3.7-max","instructions":["README.md"]}\n',
        encoding="utf-8",
    )

    first = inject.inject(tmp_path, target="opencode", mode="link")
    second = inject.inject(tmp_path, target="opencode", mode="link")
    data = json.loads(config.read_text(encoding="utf-8"))

    assert first.wrote is True
    assert second.wrote is False
    assert data["model"] == "apiyi/qwen3.7-max"
    assert data["instructions"] == ["README.md", ".omni/generated/memory.md"]


def test_opencode_link_accepts_jsonc_comments_and_trailing_commas(tmp_path: Path) -> None:
    config = tmp_path / "opencode.json"
    config.write_text(
        """
{
  // OpenCode accepts JSONC project config.
  "model": "apiyi/qwen3.7-max",
  "note": "literal // and /* stay */ plus ,]",
  /* project provider config */
  "provider": {
    "apiyi": {
      "options": {
        "baseURL": "https://api.apiyi.com/v1", // keep URL slashes intact
      },
    },
  },
  "instructions": [
    "README.md",
  ],
}
""".lstrip(),
        encoding="utf-8",
    )

    result = inject.inject(tmp_path, target="opencode", mode="link")
    data = json.loads(config.read_text(encoding="utf-8"))

    assert result.wrote is True
    assert data["model"] == "apiyi/qwen3.7-max"
    assert data["note"] == "literal // and /* stay */ plus ,]"
    assert data["provider"]["apiyi"]["options"]["baseURL"] == "https://api.apiyi.com/v1"
    assert data["instructions"] == ["README.md", ".omni/generated/memory.md"]


def test_opencode_link_rejects_unclosed_jsonc_block_comment_without_writing(
    tmp_path: Path,
) -> None:
    config = tmp_path / "opencode.json"
    original = '{"instructions": ["README.md"]} /* unfinished\n'
    config.write_text(original, encoding="utf-8")

    with pytest.raises(ValueError, match=r"invalid opencode\.json"):
        inject.inject(tmp_path, target="opencode", mode="link")

    assert config.read_text(encoding="utf-8") == original


def test_opencode_link_rejects_invalid_json_without_writing(tmp_path: Path) -> None:
    config = tmp_path / "opencode.json"
    original = "{ invalid json\n"
    config.write_text(original, encoding="utf-8")

    with pytest.raises(ValueError, match=r"invalid opencode\.json"):
        inject.inject(tmp_path, target="opencode", mode="link")

    assert config.read_text(encoding="utf-8") == original


def test_opencode_link_rejects_non_list_instructions_without_writing(tmp_path: Path) -> None:
    config = tmp_path / "opencode.json"
    original = '{"instructions":"README.md"}\n'
    config.write_text(original, encoding="utf-8")

    with pytest.raises(ValueError, match="instructions must be a list"):
        inject.inject(tmp_path, target="opencode", mode="link")

    assert config.read_text(encoding="utf-8") == original


def test_opencode_link_rejects_symlink_without_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / "opencode.json"
    original_is_symlink = Path.is_symlink

    def fake_is_symlink(path: Path) -> bool:
        if path == config:
            return True
        return original_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)

    with pytest.raises(ValueError, match="symlinks are not allowed"):
        inject.inject(tmp_path, target="opencode", mode="link")

    assert not config.exists()


def test_inject_cli_unknown_target_returns_exit_2(tmp_path: Path) -> None:
    result = run_omni(tmp_path, "inject", "unknown", "--mode", "preview")
    assert result.returncode == 2
    assert "invalid choice" in result.stderr


def test_inject_cli_preview_and_link_modes(tmp_path: Path) -> None:
    preview = run_omni(tmp_path, "inject", "claude", "--mode", "preview")
    link = run_omni(tmp_path, "inject", "claude", "--mode", "link")

    assert preview.returncode == 0, preview.stderr
    assert preview.stdout == MANAGED_REGION
    assert link.returncode == 0, link.stderr
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == MANAGED_REGION


def test_opencode_inject_cli_redacts_printed_config_diff(tmp_path: Path) -> None:
    token_value = "opencode-diff-" + "token-value-123456"
    config = tmp_path / "opencode.json"
    config.write_text(
        json.dumps({"api_key": token_value, "instructions": ["README.md"]}) + "\n",
        encoding="utf-8",
    )

    result = run_omni(tmp_path, "inject", "opencode", "--mode", "link")
    data = json.loads(config.read_text(encoding="utf-8"))

    assert result.returncode == 0, result.stderr
    assert token_value in data["api_key"]
    assert token_value not in result.stdout
    assert "REDACTED:secret_assignment:" in result.stdout
    assert ".omni/generated/memory.md" in data["instructions"]
