# QwenCode v0 Adapter Evidence

Date: 2026-06-17 local.

Scope: approved narrow adapter only. QwenCode remains the coding agent. Cairn
Memory supplies governed context and redacted transcript ingest through existing
CLI surfaces.

## Boundary

Implemented:

- `cairn inject qwen --mode preview|link`
- project-local `QWEN.md` managed-region injection of
  `@.omni/generated/memory.md`
- `cairn ingest --engine qwen --transcript <utf8-jsonl>`
- parser support for QwenCode `qwen --output-format stream-json` tool evidence:
  top-level `assistant` messages with `message.content[].type == "tool_use"`
  and top-level `user` messages with `message.content[].type == "tool_result"`

Explicitly not implemented:

- no QwenCode hook installer
- no QwenCode background capture
- no plugin daemon
- no global `~/.qwen` edits
- no write-capable MCP or external write path
- no new migration
- no Codex or Cursor adapter

## Recorded QwenCode facts

Local QwenCode CLI inspection showed:

- installed command: `qwen`
- visible version: `0.16.2`
- headless transcript mode: `qwen --output-format stream-json`
- project context file: `QWEN.md`
- `QWEN.md` supports `@path/to/file` imports, with relative paths resolved from
  the context file

Those facts shaped the adapter: Cairn Memory writes only the project-local
`QWEN.md` managed region and ingests only UTF-8 stream-json transcript files.

## Acceptance

Focused test command:

```powershell
/tmp/cairn-memory-pytest-venv/bin/python -m pytest \
  tests/test_parse.py \
  tests/test_inject.py \
  tests/test_cli_help.py \
  tests/test_capture.py \
  tests/test_db.py::test_ingest_qwen_transcript_records_engine \
  tests/test_cli_smoke.py::test_qwen_inject_cli_preview \
  tests/test_cli_smoke.py::test_ingest_cli_accepts_qwen_engine_and_run_show_nested_command \
  tests/test_cli_smoke.py::test_ingest_cli_qwen_requires_transcript_before_layout_write \
  -q
```

Result:

```text
50 passed
```

Full suite:

```text
649 passed
```

Covered behavior:

- `qwen` is a registered capture engine for run metadata
- `cairn inject qwen --mode preview` prints the managed region without writing
- `cairn inject qwen --mode link` preserves existing `QWEN.md` content and is
  idempotent
- symlinked `QWEN.md` is rejected before write
- `cairn ingest --engine qwen` requires an explicit transcript before creating
  `.omni/`
- QwenCode stream-json `tool_use` input is normalized so run show can display
  nested commands such as `pnpm run test`
- common QwenCode non-tool messages are ignored rather than archived as unknown
  transcript shapes
