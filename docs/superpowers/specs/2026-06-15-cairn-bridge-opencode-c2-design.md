# Cairn Bridge C-2 OpenCode Design

Date: 2026-06-15
Status: approved scope for implementation

## Goal

Prove Cairn Bridge with one real second engine, OpenCode, without turning
Cairn Memory into an agent runner. OpenCode remains responsible for coding,
tool-calling, permissions, and model/provider configuration. Cairn Memory provides
governed brain-layer context and accepts redacted run evidence through existing
CLI write paths.

## Approved C-2 v0 Scope

C-2 v0 adds only:

1. `cairn inject opencode --mode preview|link`
2. `cairn ingest --engine opencode --transcript <utf8-jsonl>`
3. OpenCode transcript normalization for observed `opencode run --format json`
   tool events
4. documentation and dogfood evidence for a cold/warm OpenCode loop

It adds no new migration, no MCP server, no plugin background process, no
permission policy, no multi-agent router, and no external write path. All
database writes still go through `cairn ingest`, `cairn task *`, `cairn outcome *`,
and the existing human-gated memory review commands.

## Recorded OpenCode Facts

The design is based on two recorded facts:

- Official OpenCode rules documentation says OpenCode reads project
  `AGENTS.md` and can also combine additional instruction files from the
  `instructions` array in `opencode.json`.
- Real dogfood in `docs/opencode-dogfood-2026-06-15.md` captured
  `opencode run --format json` as UTF-8 JSONL rows. Its "Recorded OpenCode
  JSONL Row Shape" section includes a sanitized `tool_use` row where command,
  exit, and timing data live under `part.state`; long command output is omitted
  from that evidence excerpt.

The future adapter must not invent unrecorded OpenCode hook fields. Unknown
OpenCode rows continue to fall into the redacted transcript archive.

## Injection Design

`cairn inject opencode --mode link` updates a project-local `opencode.json` file
so its `instructions` array contains `.omni/generated/memory.md`.

Behavior:

- If `opencode.json` does not exist, create a minimal JSON object with schema and
  instructions.
- If it exists and has an `instructions` array, append the Cairn memory path once.
- If the entry already exists, make no write.
- If the file is invalid JSON or `instructions` is not a list, fail with exit 2
  and leave the file unchanged.
- Preview mode prints the minimal config snippet and never writes.

This follows the official OpenCode path for external instruction files and keeps
user-authored `AGENTS.md` content untouched.

## Capture / Ingest Design

`cairn ingest --engine opencode --transcript <path>` records the run engine as
`opencode` in `runs.engine` and parses UTF-8 JSONL output produced by
`opencode run --format json`.

For observed tool events:

- `event_type`: existing row `type`
- `tool`: `part.tool`
- `tool_use_id`: `part.callID`
- `exit_code`: `part.state.metadata.exit`
- `duration_ms`: `part.state.time.end - part.state.time.start` when both are
  numeric
- `meta`: the redacted original OpenCode row minus only normalized top-level
  fields

Human-facing run views may derive command previews from the nested redacted
`part.state.input.command` field, but the parser must not invent additional
OpenCode fields beyond the recorded row shape.

No raw transcript content is stored. Existing transcript redaction and artifact
storage remain the only persistence path.

## Safety Invariants

- Redaction-before-write remains mandatory for transcript events, archive rows,
  and config diffs. Tests must prove printed `opencode.json` diffs redact
  secret-like existing config values.
- `cairn hook` remains Claude-compatible and always exits 0.
- OpenCode capture does not write the DB outside `cairn ingest`.
- Read-only surfaces remain read-only and migration-free.
- `cairn inject opencode` may edit only `opencode.json`; it never touches global
  OpenCode config.
- OpenCode remains a read-only consumer of `cairn memory read`, `failure read`,
  `verify plan`, and `task read`. Memory activation still requires human review.

## Acceptance Evidence

C-2 is acceptable when:

- unit tests prove OpenCode injection preserves existing config and rejects
  invalid config without writing
- CLI tests prove OpenCode config diffs are redacted before printing
- parser/ingest tests prove OpenCode JSONL command, exit, and engine data are
  stored correctly
- read-only/leak tests still pass
- `pytest -q`, `git diff --check`, and `python -m omni.cli audit secrets` pass
- a sandbox OpenCode run uses injected memory context or read surfaces, runs the
  selected verification command, and leaves run/task/outcome evidence
