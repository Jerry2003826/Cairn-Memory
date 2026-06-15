# OmniBridge OpenCode C-2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first real second-engine proof point by letting OpenCode consume OmniAgent memory through `opencode.json.instructions` and ingest OpenCode JSONL transcripts as `engine=opencode`.

**Architecture:** Keep C-2 as a thin adapter over existing seams. Injection is a new data-backed target in `inject.py`; capture is a new registered engine plus parser normalization for observed OpenCode JSONL rows, with DB writes only through `omni ingest`.

**Tech Stack:** Python stdlib, SQLite, pytest, OpenCode CLI JSONL transcripts.

---

## Files

- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `docs/omniagent-phase-c-charter.md`
- Modify: `docs/opencode-dogfood-2026-06-15.md`
- Modify: `src/omni/capture/__init__.py`
- Create: `src/omni/capture/opencode.py`
- Modify: `src/omni/inject.py`
- Modify: `src/omni/parse.py`
- Modify: `src/omni/ingest.py`
- Modify: `src/omni/cli.py`
- Modify: `tests/test_capture.py`
- Modify: `tests/test_inject.py`
- Modify: `tests/test_parse.py`
- Modify: `tests/test_db.py`
- Modify: `tests/test_cli_help.py`
- Modify: `tests/test_cli_smoke.py`
- Modify: `tests/test_module_budget.py`

## Task 1: Governance And Documentation Approval

- [x] Update `AGENTS.md` so C-2 OpenCode v0 is explicitly approved. The approved scope must name `omni inject opencode` and `omni ingest --engine opencode --transcript <path>`, and must state that OpenCode plugins, MCP, external DB writes, permission tiers, and multi-agent handoff remain deferred.
- [x] Update `docs/omniagent-phase-c-charter.md`: mark C-2 as approved for OpenCode v0, with no migration and no plugin background process.
- [x] Update `README.md` and `README.zh-CN.md` to show C-2 as approved/in progress without listing not-yet-implemented commands in the current command tables.
- [x] Update `docs/opencode-dogfood-2026-06-15.md` with the sanitized recorded `tool_use` JSONL row shape that C-2 parser tests will bind to.
- [x] Run `pytest -q tests/test_docs.py`.
- [x] Commit with message `day21: c2 governance — approve OpenCode v0 scope`.

## Task 2: OpenCode Inject Target

- [x] Add failing tests in `tests/test_inject.py`:

```python
def test_opencode_preview_prints_instruction_config_without_writing(tmp_path: Path) -> None:
    result = inject.inject(tmp_path, target="opencode", mode="preview")
    assert result.wrote is False
    assert not (tmp_path / "opencode.json").exists()
    assert '".omni/generated/memory.md"' in result.body


def test_opencode_link_appends_instruction_once_and_preserves_config(tmp_path: Path) -> None:
    config = tmp_path / "opencode.json"
    config.write_text('{"model":"apiyi/qwen3.7-max","instructions":["README.md"]}\n', encoding="utf-8")
    first = inject.inject(tmp_path, target="opencode", mode="link")
    second = inject.inject(tmp_path, target="opencode", mode="link")
    data = json.loads(config.read_text(encoding="utf-8"))
    assert first.wrote is True
    assert second.wrote is False
    assert data["model"] == "apiyi/qwen3.7-max"
    assert data["instructions"] == ["README.md", ".omni/generated/memory.md"]
```

- [x] Run `pytest -q tests/test_inject.py::test_opencode_preview_prints_instruction_config_without_writing tests/test_inject.py::test_opencode_link_appends_instruction_once_and_preserves_config` and verify the tests fail because `opencode` is not a known target.
- [x] Implement an OpenCode injection target in `src/omni/inject.py` using the existing `InjectResult` shape. Keep Claude behavior byte-identical.
- [x] Add tests for invalid JSON and non-list `instructions`, both proving no write occurs.
- [x] Add a CLI-level redaction test with an existing `opencode.json` containing a secret-like value. The link command must preserve the file value but must not print the raw secret in the diff.
- [x] Add a symlink rejection test proving `omni inject opencode --mode link` cannot follow `opencode.json` outside the project-local write path.
- [x] Run `pytest -q tests/test_inject.py`.
- [x] Commit with message `day21: inject — add OpenCode instructions target`.

## Task 3: OpenCode Engine And Transcript Normalization

- [x] Add failing tests in `tests/test_capture.py` proving `get("opencode").name == "opencode"` and that its run engine is `opencode`.
- [x] Add failing parser test in `tests/test_parse.py` using an observed `opencode run --format json` row:

```python
row = {
    "type": "tool_use",
    "timestamp": 1781497265185,
    "sessionID": "ses_1367",
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
```

Expected normalized event: `event_type == "tool_use"`, `tool == "bash"`,
`tool_use_id == "call_e413"`, `exit_code == 0`, `duration_ms == 34`.

- [x] Add failing ingest test in `tests/test_db.py` proving
  `ingest.ingest(root=tmp_path, run_id="open_run", transcript=path, engine="opencode")`
  stores `runs.engine = "opencode"`.
- [x] Run the focused tests and verify they fail for missing OpenCode support.
- [x] Implement `src/omni/capture/opencode.py` and load it from the registry.
- [x] Add `run_engine` to `CaptureEngine`, preserving Claude as `claude_code`.
- [x] Add `engine` parameter to `ingest.ingest`, `_ingest_one`, and `_ensure_run`,
  defaulting through the selected capture engine.
- [x] Add `parse.py` normalization for observed OpenCode `part.state` tool rows.
- [x] Update the command preview path, either by flattening a redacted command field during OpenCode normalization or by making run-show command discovery recursively inspect bounded nested metadata.
- [x] Add a safety test proving OpenCode transcript ingest does not scan Claude hook spool.
- [x] Add strict OpenCode archive coverage for unrecorded `tool_use` shapes.
- [x] Add strict OpenCode archive coverage for incomplete `part.state` tool rows with missing `part.type`, `part.tool`, or `part.callID`.
- [x] Add safety tests proving OpenCode requires an explicit transcript and unknown engines fail before layout writes.
- [x] Run `pytest -q tests/test_capture.py tests/test_parse.py tests/test_db.py`.
- [x] Commit with message `day21: ingest — normalize OpenCode transcripts`.

## Task 4: CLI Wiring And Smoke Tests

- [x] Add failing CLI tests:
  - `omni inject opencode --mode preview` exits 0 and prints `.omni/generated/memory.md`
  - `omni ingest opencode_run --engine opencode --transcript <path>` exits 0 and `run show` displays the nested command preview
  - unknown `--engine` exits 2 before DB writes
- [x] Run the focused CLI tests and verify they fail.
- [x] Add `--engine` to the ingest parser with choices from registered capture engines.
- [x] Wire CLI ingest to pass `engine=args.engine`.
- [x] Update `README.md` and `README.zh-CN.md` command tables now that the new CLI surface exists.
- [x] Add run-show coverage proving unrelated nested `command` fields are ignored while OpenCode `part.state.input.command` still displays.
- [x] Run `pytest -q tests/test_cli_help.py tests/test_cli_smoke.py`.
- [x] Commit with message `day21: cli — expose OpenCode ingest`.

## Task 5: Dogfood And Closeout Evidence

- [x] Update `docs/opencode-dogfood-2026-06-15.md` with the new C-2 run, keeping the earlier constrained read-surface run as historical evidence.
- [x] Run sandbox OpenCode with `opencode.json.instructions` injection, ingest the UTF-8 JSONL transcript using `--engine opencode`, then record task/outcome evidence through existing CLI writers.
- [x] Run:

```powershell
pytest -q
git diff --check
python -m omni.cli audit secrets
pytest -q tests/test_capture.py tests/test_inject.py tests/test_parse.py tests/test_db.py tests/test_cli_smoke.py
```

- [x] Request code review and fix every Critical/Important issue.
- [x] Commit with message `day21: dogfood — prove OpenCode C-2 loop`.

## Definition Of Done

- C-2 is documented as approved and implemented.
- Claude injection and Claude hook behavior remain compatible.
- OpenCode injection writes only `opencode.json` and preserves existing config.
- OpenCode transcript ingest writes only through `omni ingest`.
- OpenCode run rows store `engine='opencode'`.
- Unknown OpenCode rows archive redacted content rather than guessing schema.
- No new migration, MCP, plugin background process, permission layer, UI, or external write path.
- Full verification and GitHub bot checks pass before merge.
