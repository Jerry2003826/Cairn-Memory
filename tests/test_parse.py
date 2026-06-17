from __future__ import annotations

import json
from pathlib import Path

from omni import parse


def write_jsonl(path: Path, rows: list[object]) -> None:
    lines = [json.dumps(row) if isinstance(row, dict) else str(row) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_parse_transcript_normalizes_known_jsonl_events(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.jsonl"
    write_jsonl(
        transcript,
        [
            {
                "type": "tool_use",
                "timestamp": "2026-06-11T00:00:00Z",
                "id": "toolu_1",
                "name": "Bash",
                "exit_code": 0,
                "duration_ms": 42,
                "surprise": {"kept": True},
            },
            {
                "event_type": "assistant_message",
                "ts": "2026-06-11T00:00:01Z",
                "tool_use_id": "toolu_1",
                "tool": "Bash",
            },
        ],
    )

    result = parse.parse_transcript(transcript)

    assert result.archive is None
    assert [event.seq for event in result.events] == [1, 2]
    assert result.events[0].event_type == "tool_use"
    assert result.events[0].ts == "2026-06-11T00:00:00Z"
    assert result.events[0].tool == "Bash"
    assert result.events[0].tool_use_id == "toolu_1"
    assert result.events[0].exit_code == 0
    assert result.events[0].duration_ms == 42
    assert result.events[0].source == "transcript"
    assert result.events[0].meta == {"surprise": {"kept": True}}
    assert result.events[1].event_type == "assistant_message"


def test_parse_transcript_treats_claude_code_as_claude_alias(tmp_path: Path) -> None:
    transcript = tmp_path / "claude-code.jsonl"
    write_jsonl(
        transcript,
        [
            {
                "hook_event_name": "SessionEnd",
                "timestamp": "2026-06-17T00:00:00Z",
                "session_id": "s1",
            }
        ],
    )

    result = parse.parse_transcript(transcript, engine="claude_code")

    assert result.archive is None
    assert result.events[0].event_type == "SessionEnd"
    assert result.events[0].meta == {"session_id": "s1"}


def test_parse_transcript_normalizes_observed_opencode_tool_use(tmp_path: Path) -> None:
    transcript = tmp_path / "opencode.jsonl"
    write_jsonl(
        transcript,
        [
            {
                "type": "tool_use",
                "timestamp": 1781497265185,
                "sessionID": "ses_1367",
                "input": {"unexpected": "top-level"},
                "part": {
                    "type": "tool",
                    "tool": "bash",
                    "callID": "call_e413",
                    "state": {
                        "input": {"command": "pnpm run test"},
                        "metadata": {"exit": 0, "output": "sandbox test ok"},
                        "time": {"start": 1781497265149, "end": 1781497265183},
                    },
                },
            }
        ],
    )

    result = parse.parse_transcript(transcript, engine="opencode")
    event = result.events[0]

    assert result.archive is None
    assert event.event_type == "tool_use"
    assert event.ts == "1781497265185"
    assert event.tool == "bash"
    assert event.tool_use_id == "call_e413"
    assert event.exit_code == 0
    assert event.duration_ms == 34
    assert event.meta["input"]["command"] == "pnpm run test"
    assert event.meta["opencode_raw_input"] == {"unexpected": "top-level"}
    assert event.meta["part"]["state"]["input"]["command"] == "pnpm run test"


def test_parse_transcript_normalizes_observed_qwen_stream_json_tool_use(
    tmp_path: Path,
) -> None:
    transcript = tmp_path / "qwen.jsonl"
    write_jsonl(
        transcript,
        [
            {
                "type": "system",
                "subtype": "init",
                "session_id": "ses_qwen",
                "qwen_code_version": "0.16.2",
            },
            {
                "type": "assistant",
                "uuid": "msg_qwen",
                "session_id": "ses_qwen",
                "parent_tool_use_id": None,
                "message": {
                    "id": "msg_qwen",
                    "type": "message",
                    "role": "assistant",
                    "model": "qwen3-coder",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_qwen",
                            "name": "run_shell_command",
                            "input": {"command": "pnpm run test"},
                        }
                    ],
                    "stop_reason": "tool_use",
                    "usage": {"input_tokens": 1, "output_tokens": 2},
                },
            },
            {
                "type": "user",
                "uuid": "result_qwen",
                "session_id": "ses_qwen",
                "parent_tool_use_id": None,
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_qwen",
                            "content": "tests passed",
                            "is_error": False,
                        }
                    ],
                },
            },
            {"type": "result", "subtype": "success", "result": "done"},
        ],
    )

    result = parse.parse_transcript(transcript, engine="qwen")

    assert result.archive is not None
    assert result.archive.line_count == 2
    assert [event.event_type for event in result.events] == ["tool_use", "tool_result"]
    tool_use = result.events[0]
    tool_result = result.events[1]
    assert tool_use.tool == "run_shell_command"
    assert tool_use.tool_use_id == "toolu_qwen"
    assert tool_use.meta["input"]["command"] == "pnpm run test"
    assert tool_use.meta["qwen_content_block"]["input"]["command"] == "pnpm run test"
    assert tool_use.meta["qwen_content_index"] == 0
    assert tool_result.event_type == "tool_result"
    assert tool_result.tool_use_id == "toolu_qwen"
    assert tool_result.meta["qwen_content_block"]["content"] == "tests passed"
    reasons = [
        json.loads(line)["reason"]
        for line in result.archive.payload.decode("utf-8").splitlines()
    ]
    assert reasons == ["qwen_non_tool_line", "qwen_non_tool_line"]


def test_parse_transcript_archives_lines_for_unknown_engine(tmp_path: Path) -> None:
    transcript = tmp_path / "codex.jsonl"
    write_jsonl(
        transcript,
        [
            {
                "type": "tool_use",
                "timestamp": "2026-06-17T00:00:00Z",
                "id": "toolu_codex",
                "name": "Bash",
            }
        ],
    )

    result = parse.parse_transcript(transcript, engine="codex")

    assert result.events == []
    assert result.archive is not None
    archive_record = json.loads(result.archive.payload.decode("utf-8").splitlines()[0])
    assert archive_record["reason"] == "unknown_transcript_shape"


def test_parse_qwen_archives_unrecorded_direct_tool_use_shape(tmp_path: Path) -> None:
    transcript = tmp_path / "qwen-unknown.jsonl"
    write_jsonl(
        transcript,
        [
            {
                "type": "tool_use",
                "timestamp": "2026-06-17T00:00:00Z",
                "input": {"command": "pnpm run test"},
            }
        ],
    )

    result = parse.parse_transcript(transcript, engine="qwen")

    assert result.events == []
    assert result.archive is not None
    assert result.archive.kind == "transcript_archive"
    assert result.archive.line_count == 1
    archive_record = json.loads(result.archive.payload.decode("utf-8").splitlines()[0])
    assert archive_record["reason"] == "unknown_qwen_shape"


def test_parse_opencode_ingests_failed_tool_use_without_input(tmp_path: Path) -> None:
    """I-03: a failed OpenCode tool (state has error/output but no input or
    metadata) must be ingested as an event, not silently archived."""
    transcript = tmp_path / "opencode-failed.jsonl"
    write_jsonl(
        transcript,
        [
            {
                "type": "tool_use",
                "timestamp": 1781497265185,
                "part": {
                    "type": "tool",
                    "tool": "bash",
                    "callID": "call_fail",
                    "state": {
                        "error": "command not found: pytest",
                        "output": "",
                        "time": {"start": 1781497265149, "end": 1781497265183},
                    },
                },
            }
        ],
    )

    result = parse.parse_transcript(transcript, engine="opencode")

    assert result.archive is None
    assert len(result.events) == 1
    event = result.events[0]
    assert event.tool == "bash"
    assert event.tool_use_id == "call_fail"


def test_parse_opencode_archives_unrecorded_tool_use_shape(tmp_path: Path) -> None:
    transcript = tmp_path / "opencode-unknown.jsonl"
    write_jsonl(
        transcript,
        [
            {
                "type": "tool_use",
                "timestamp": 1781497265185,
                "part": {"state": "running"},
            }
        ],
    )

    result = parse.parse_transcript(transcript, engine="opencode")

    assert result.events == []
    assert result.archive is not None
    assert result.archive.kind == "transcript_archive"
    assert result.archive.line_count == 1
    archive_record = json.loads(result.archive.payload.decode("utf-8").splitlines()[0])
    assert archive_record["reason"] == "unknown_opencode_shape"


def test_parse_opencode_archives_incomplete_tool_use_shapes(tmp_path: Path) -> None:
    transcript = tmp_path / "opencode-incomplete.jsonl"
    write_jsonl(
        transcript,
        [
            {"part": {"type": "tool", "tool": "bash", "callID": "call_missing_type"}},
            {"type": "tool_use", "part": {"state": {}}},
            {
                "type": "tool_use",
                "part": {
                    "type": "message",
                    "tool": "bash",
                    "callID": "call_bad",
                    "state": {"metadata": {"exit": 0}},
                },
            },
        ],
    )

    result = parse.parse_transcript(transcript, engine="opencode")

    assert result.events == []
    assert result.archive is not None
    assert result.archive.line_count == 3
    reasons = [
        json.loads(line)["reason"]
        for line in result.archive.payload.decode("utf-8").splitlines()
    ]
    assert reasons == [
        "unknown_opencode_shape",
        "unknown_opencode_shape",
        "unknown_opencode_shape",
    ]


def test_parse_transcript_archives_unknown_lines_with_redaction(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OMNI_PARSE_SECRET", "parse-secret-value-123")
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps({"type": "tool_result", "timestamp": "2026-06-11T00:00:02Z"}),
                "not-json parse-secret-value-123",
                json.dumps(
                    {
                        "timestamp": "2026-06-11T00:00:03Z",
                        "api_key": "parse-secret-value-123",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = parse.parse_transcript(transcript)

    assert len(result.events) == 1
    assert result.archive is not None
    assert result.archive.kind == "transcript_archive"
    assert result.archive.line_count == 2
    assert result.archive.redaction_status == "redacted"
    assert "env" in result.archive.detectors
    assert not (tmp_path / ".omni").exists()
    archive_text = result.archive.payload.decode("utf-8")
    assert "parse-secret-value-123" not in archive_text
    records = [json.loads(line) for line in archive_text.splitlines()]
    assert [record["line"] for record in records] == [2, 3]
    assert records[0]["reason"] == "invalid_json"
    assert records[1]["reason"] == "unknown_transcript_shape"


def test_parse_transcript_redacts_known_event_meta_in_return_value(tmp_path: Path) -> None:
    secret = "sk-parsemetasecretvalue1234567890"
    transcript = tmp_path / "transcript.jsonl"
    write_jsonl(
        transcript,
        [
            {
                "type": "tool_use",
                "timestamp": "2026-06-11T00:00:00Z",
                "name": "Bash",
                "api_key": secret,
            }
        ],
    )

    result = parse.parse_transcript(transcript)
    meta_text = json.dumps(result.events[0].meta, sort_keys=True)
    rendered = parse.events_as_jsonl(result.events)

    assert secret not in meta_text
    assert "REDACTED:" in meta_text
    assert result.events[0].redaction_status == "redacted"
    assert "openai_token" in result.events[0].detectors
    assert result.events[0].as_dict()["redaction_status"] == "redacted"
    assert "openai_token" in result.events[0].as_dict()["detectors"]
    assert secret not in rendered
    assert "\\u27e8REDACTED:" not in rendered
    assert "\u27e8REDACTED:" in rendered
    assert not (tmp_path / ".omni").exists()
    assert not (tmp_path / ".omni" / "omni.sqlite3").exists()


def test_parse_transcript_redacts_secret_like_known_event_fields(tmp_path: Path) -> None:
    secret = "ghp_" + "abcdefghijklmnopqrstuvwxyz1234567890"
    transcript = tmp_path / "transcript.jsonl"
    write_jsonl(
        transcript,
        [
            {
                "type": "tool_use",
                "timestamp": "2026-06-11T00:00:00Z",
                "id": secret,
                "name": f"token={secret}",
            }
        ],
    )

    result = parse.parse_transcript(transcript)
    rendered = parse.events_as_jsonl(result.events)
    event = result.events[0]

    assert secret not in event.tool
    assert secret not in event.tool_use_id
    assert secret not in rendered
    assert "REDACTED:" in rendered


def test_parse_transcript_streams_without_reading_entire_file(
    tmp_path: Path, monkeypatch
) -> None:
    transcript = tmp_path / "large.jsonl"
    with transcript.open("w", encoding="utf-8") as handle:
        for index in range(50_000):
            handle.write(
                json.dumps(
                    {
                        "type": "tool_use",
                        "timestamp": f"2026-06-11T00:00:{index % 60:02d}Z",
                        "id": f"toolu_{index}",
                    }
                )
                + "\n"
            )

    def fail_read_bytes(_path: Path) -> bytes:
        raise AssertionError("parse_transcript must stream transcript lines")

    monkeypatch.setattr(Path, "read_bytes", fail_read_bytes)

    result = parse.parse_transcript(transcript)

    assert len(result.events) == 50_000
    assert result.archive is None


def test_parse_transcript_caps_large_unknown_archive_payload(tmp_path: Path) -> None:
    transcript = tmp_path / "large-unknown.jsonl"
    with transcript.open("w", encoding="utf-8") as handle:
        for index in range(100_000):
            handle.write(json.dumps({"unknown": index, "padding": "x" * 40}) + "\n")

    result = parse.parse_transcript(transcript)

    assert result.events == []
    assert result.archive is not None
    assert result.archive.line_count == 100_000
    assert len(result.archive.payload) < 1024 * 1024
    records = [json.loads(line) for line in result.archive.payload.decode("utf-8").splitlines()]
    assert records[-1]["error"] == "archive_truncated"
    assert records[-1]["omitted_lines"] > 0
    assert result.archive.redaction_status == "truncated"


def test_events_as_jsonl_redacts_each_line_for_large_output() -> None:
    secret = "sk-" + "largeparseoutputsecretvalue1234567890"
    events = [
        parse.NormalizedEvent(
            seq=index + 1,
            ts="2026-06-11T00:00:00Z",
            event_type="tool_use",
            tool="Bash",
            tool_use_id=f"toolu_{index}",
            exit_code=0,
            duration_ms=None,
            source="transcript",
            meta={"api_key": secret, "padding": "x" * 200},
        )
        for index in range(6_000)
    ]

    rendered = parse.events_as_jsonl(events)
    lines = rendered.splitlines()

    assert len(lines) == len(events)
    assert "payload_truncated" not in rendered
    assert secret not in rendered
    assert all(json.loads(line)["event_type"] == "tool_use" for line in lines)


def test_events_as_jsonl_is_stable(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.jsonl"
    write_jsonl(transcript, [{"hook_event_name": "SessionEnd", "session_id": "s1"}])

    result = parse.parse_transcript(transcript)
    rendered = parse.events_as_jsonl(result.events)

    assert rendered == (
        '{"detectors":[],"duration_ms":null,"event_type":"SessionEnd","exit_code":null,'
        '"meta":{"session_id":"s1"},"redaction_status":"clean","seq":1,"source":"transcript","tool":null,'
        '"tool_use_id":null,"ts":""}\n'
    )
