from __future__ import annotations

import json
from pathlib import Path

from omni import hook
from omni import spool


def test_capture_hook_writes_stub_when_redactor_raises(tmp_path: Path, monkeypatch) -> None:
    payload = b"raw secret must not be written"

    def fail(_payload: bytes):
        raise RuntimeError("boom")

    monkeypatch.setattr(hook, "redact_minimal", fail)

    result = hook.capture_hook(payload, root=tmp_path)

    assert result.ok is True
    assert result.spool_path is not None
    written = result.spool_path.read_text(encoding="utf-8")
    assert "raw secret must not be written" not in written
    record = json.loads(written)
    stub = json.loads(record["payload"])
    assert record["meta"]["redaction_status"] == "withheld"
    assert stub["error"] == "redaction_failed"
    assert stub["byte_len"] == len(payload)


def test_session_end_writes_per_request_ingest_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OMNI_QUEUE_SECRET", "queue-secret-value-123")
    result = hook.capture_hook(
        b'{"hook_event_name":"SessionEnd","session_id":"queue-secret-value-123",'
        b'"transcript_path":"t.jsonl"}',
        root=tmp_path,
    )

    request_files = sorted((tmp_path / ".omni" / "spool").glob("ingest-*.json"))
    request_text = request_files[0].read_text(encoding="utf-8")

    assert result.ok is True
    assert len(request_files) == 1
    assert not (tmp_path / ".omni" / "spool" / "ingest_queue.jsonl").exists()
    assert "SessionEnd" in request_text
    assert "queue-secret-value-123" not in request_text
    assert "REDACTED:env:" in request_text


def test_drain_ingest_queue_reads_request_files_and_skips_malformed(
    tmp_path: Path,
) -> None:
    spool_dir = tmp_path / ".omni" / "spool"
    spool_dir.mkdir(parents=True)
    (spool_dir / "ingest-1.json").write_text(
        '{"event":"SessionEnd","session_id":"s1","transcript_path":"a.jsonl"}\n',
        encoding="utf-8",
    )
    (spool_dir / "ingest-2.json").write_text(
        '{"event":"SessionEnd","session_id":"s2","transcript_path":"b.jsonl"}\n',
        encoding="utf-8",
    )
    malformed = spool_dir / "ingest-bad.json"
    malformed.write_text("not-json\n", encoding="utf-8")

    requests = spool.drain_ingest_queue(tmp_path)
    second = spool.drain_ingest_queue(tmp_path)

    assert [request["session_id"] for request in requests] == ["s1", "s2"]
    assert second == []
    assert not (spool_dir / "ingest-1.json").exists()
    assert not (spool_dir / "ingest-2.json").exists()
    assert malformed.exists()
