from __future__ import annotations

import json
from pathlib import Path

import pytest

from omni.status import status_json


def test_status_json_ok_false_when_uninitialized(tmp_path: Path) -> None:
    body = json.loads(status_json(tmp_path))

    assert body["ok"] is False
    assert body["initialized"] is False
    assert body["omni_dir"] is False
    assert body["database"] is False


def test_status_json_ok_false_with_omni_dir_only(tmp_path: Path) -> None:
    (tmp_path / ".omni").mkdir()

    body = json.loads(status_json(tmp_path))

    assert body["ok"] is False
    assert body["initialized"] is False
    assert body["omni_dir"] is True
    assert body["database"] is False


def test_status_json_ok_true_when_omni_dir_and_database_exist(tmp_path: Path) -> None:
    (tmp_path / ".omni").mkdir()
    (tmp_path / ".omni" / "omni.sqlite3").write_bytes(b"")

    body = json.loads(status_json(tmp_path))

    assert body["ok"] is True
    assert body["initialized"] is True
    assert body["omni_dir"] is True
    assert body["database"] is True
