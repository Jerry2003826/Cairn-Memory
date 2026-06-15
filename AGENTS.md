# Cairn Memory Phase C (governed brain layer transition)

> **Vision update (2026-06-15).** Cairn Memory is now scoped as an *agent-agnostic*
> governed brain layer for **all** AI Coding Agents (Claude Code, Codex, OpenCode,
> QwenCode, Cursor), delivered in four stages — ① Cairn Memory Kernel · ② Cairn Bridge
> (multi-engine adapters + a read-only access surface) · ③ Cairn Runtime (task
> lifecycle + multi-agent handoff) · ④ Product. The Kernel (Layers 1–5) is done;
> Phase B is done; Phase C has partial approvals. Cairn Bridge foundation
> (capture/inject seams + machine read) and Cairn Runtime C-5 task lifecycle have
> landed. C-2 OpenCode v0 has landed as the first real second-engine proof.
> Read-only MCP has landed as a thin wrapper over existing machine-read
> surfaces. Multi-agent handoff, permission tiers, and UI remain governed future
> work. **Every safety invariant is unchanged.**

## Goal

**Completed:** Cairn Memory CLI-only Claude Code v1 (Layers 1–5). See
`docs/cli-only-claude-code-v1-l1-5-completion-2026-06-15.md`.

**Current phase:** Cairn Memory Phase C — partial governed expansion per
`docs/cairn-memory-phase-c-charter.md`.

Current proven loop (unchanged):

Claude Code run → redacted trace → deterministic facts → generated memory block → measurably changed behavior in the next run.

Phase B added, without breaking safety invariants:

- interactive fact review and read-only doctor diagnostics
- task/profile-aware verify selection (still read-only)
- one new review-gated memory type at a time (preference first)
- multi-project read-only status overview

Phase C approved and landed so far:

- Cairn Bridge foundation: capture-engine seam, inject-target seam, and
  read-only machine surfaces (`cairn memory read`, `cairn failure read`,
  `cairn verify plan`)
- Cairn Runtime C-5: `008_task_runtime.sql` and `cairn task *` lifecycle commands
  for a single open task; multi-agent handoff remains deferred
- C-2 OpenCode v0: `cairn inject opencode --mode preview|link` may update only
  project-local `opencode.json` to add `.omni/generated/memory.md` to OpenCode's
  `instructions` list; `cairn ingest --engine opencode --transcript <path>` may
  ingest UTF-8 `opencode run --format json` transcripts through the existing
  redacted ingest path. No new migration was added.
- C-4 read-only MCP: `cairn mcp serve` exposes only `memory_read`,
  `failure_read`, `verify_plan`, and `task_read` over stdio JSON-RPC. It has no
  write tools, no HTTP transport, and no new migration.

## Non-goals, hard this phase

*(Hard for the currently approved Phase C scope. Items below stay unimplemented
unless a matching charter row and `AGENTS.md` update approve them first.)*

NO LLM extractors.  
NO write-capable MCP server.
NO vector or embedding search.  
NO dashboard or TUI.  
NO multi-engine router.  
NO Computer Use.  
NO automatic evolution.  
NO answer cache.  
No new tables beyond approved migrations for the current phase. Approved now:
001_init.sql through **008_task_runtime.sql**.

Phase B approved (charter section 3):

- `cairn review interactive` (human-gated fact candidate review)
- `cairn doctor` (read-only project diagnostics)
- `cairn verify --task` / `--profile` (read-only selection mapping)
- `007_preference_memory.sql` and `cairn preference *` (Sub-C)
- `cairn project register|ls` and `cairn status --all` (read-only multi-project)

Phase C approved and landed:

- C-1/C-3 Cairn Bridge foundation: capture/inject seams plus read-only machine
  surfaces (`cairn memory read`, `cairn failure read`, `cairn verify plan`)
- C-4 read-only MCP wrapper: `cairn mcp serve` wraps `memory read`,
  `failure read`, `verify plan`, and `task read` as read-only MCP tools
- C-5 task lifecycle: `cairn task start|status|ls|show|close|abandon|read`,
  `008_task_runtime.sql`, and ingest attachment to the current open task
  (`task close` requires an explicit `--success`, `--failed`, or `--unknown`;
  `task read` exposes only the current project's open task view)

Phase C approved and landed in the current implementation branch:

- C-2 OpenCode v0: one second engine via OpenCode config injection and
  transcript ingest only. OpenCode remains the coding agent; Cairn Memory only
  supplies governed context and redacted evidence capture through existing CLI
  writers.
- C-4 read-only MCP: external agents may call only the existing read surfaces
  through stdio MCP tools. Cairn Memory still exposes no external write path.

Still deferred beyond the current Phase C approvals:

- automatic/default observed_command extractor behavior
- additional memory types beyond the one approved Sub-C type
- OpenCode plugin background capture and Codex/QwenCode/Cursor adapters until
  explicitly approved
- multi-agent orchestration / handoff, permission tiers, UI (Layer 6–9 beyond task lifecycle)

If a task needs something outside the charter, STOP and leave a TODO comment.
`scripts/golden_demo.sh` may exist as a local sandbox harness; manual acceptance
remains the runbook in `docs/demo.md` and the relevant closeout notes.

## Safety rules

Violations require reverting the commit.

1. REDACTION-BEFORE-WRITE, from Day 1:
   every content byte written under `.omni/` MUST pass `redact.redact(bytes)`.
   This includes spike dumps and spool lines.
   There is NO raw-dump path anywhere, not even `/tmp`.
   There is no original vault.
   Redaction is irreversible.
   In spike-dump mode, if the redactor fails, write a stub:
   `{error, payload_sha256, byte_len}` instead of content.

2. `cairn hook` ALWAYS exits 0.
   It never blocks.
   It never makes permission decisions.
   It only redacts and appends to `.omni/spool/`.
   It records its own `elapsed_ms` into the spool line meta.
   Errors go to `.omni/spool/_errors.log` on a best-effort basis.
   The process still exits 0.

3. Hooks never write the DB.
   Stop and SessionEnd hooks only write redacted ingest request files under:
   `.omni/spool/`.

   `cairn` is the preferred CLI name; legacy `omni` invokes the same CLI for
   compatibility. The command safety classifications below apply to both names.

   Legacy `.omni/spool/ingest_queue.jsonl` is read best-effort for migration,
   but new hooks do not append to it.

   Only these commands write SQLite:
   - `cairn ingest`
   - `cairn review`
   - `cairn review interactive`
   - `cairn render`
   - `cairn outcome mark`
   - `cairn outcome mark-from-verify`
   - `cairn experience extract`
   - `cairn experience approve`
   - `cairn experience reject`
   - `cairn experience note retire`
   - `cairn failure extract`
   - `cairn failure approve`
   - `cairn failure reject`
   - `cairn failure pattern retire`
   - `cairn preference extract`
   - `cairn preference approve`
   - `cairn preference reject`
   - `cairn preference note retire`
   - `cairn project register`
   - `cairn task start`
   - `cairn task close`
   - `cairn task abandon`

   These commands are read-only:
   - `cairn parse`
   - `cairn run show`
   - `cairn status`
   - `cairn status --all`
   - `cairn doctor`
   - `cairn eval run`
   - `cairn eval dogfood`
   - `cairn dogfood`
   - `cairn outcome show`
   - `cairn outcome ls`
   - `cairn experience ls`
   - `cairn experience show`
   - `cairn experience note ls`
   - `cairn experience note show`
   - `cairn failure ls`
   - `cairn failure show`
   - `cairn failure pattern ls`
   - `cairn failure pattern show`
   - `cairn failure read`
   - `cairn preference ls`
   - `cairn preference show`
   - `cairn preference note ls`
   - `cairn preference note show`
   - `cairn project ls`
   - `cairn mcp serve`
   - `cairn memory read`
   - `cairn verify`
   - `cairn verify plan`
   - `cairn task status`
   - `cairn task ls`
   - `cairn task show`
   - `cairn task read`

   Read-only commands open SQLite in read-only mode and never run
   migrations; migrations run only inside approved write commands.
   `cairn verify` is SQLite read-only but executes the selected project
   verification command, including when `--qualifier`, `--task`, or
   `--profile` is used; it writes no Cairn Memory state.
   `cairn verify plan` uses the same read-only selection layer but spawns
   no verification subprocess.
   `cairn mcp serve` opens SQLite through the same read-only machine-read
   surfaces and must expose no write tools.
   `cairn doctor` and `cairn status --all` do not open project SQLite at all
   when reporting aggregate health (doctor opens read-only for schema checks
   on the current project only).

4. Never modify user content in `CLAUDE.md` outside the managed region:

   ```md
   <!-- omni:begin -->
   @.omni/generated/memory.md
   <!-- omni:end -->
   ```

5. `cairn init` creates `.omni/` only.
   Bare `cairn init` may ensure exactly one gitignore entry: `.omni/`.
   Routine commands such as `cairn ingest` and `cairn audit secrets` must not
   modify `.gitignore` or other user files while ensuring the `.omni/` layout.
   Installing hooks into project-level `.claude/settings.json` requires:

   ```bash
   cairn init --install-claude-hooks
   ```

   This command must:
   - print a redacted diff
   - ensure hook-owned gitignore entries for `.claude/*.omni-tmp` and
     `.claude/settings.json.omni-bak`
   - write `.claude/settings.json` with atomic temp-file replace
   - not create a raw settings backup by default
   - never touch global `~/.claude/settings.json`

   If `cairn audit secrets` has never passed in this checkout, installing hooks additionally requires `--yes`.

6. Real projects are FORBIDDEN until `cairn audit secrets` exits 0.
   Default manual testing happens in `scripts/create_sandbox.sh` repos. Real
   dogfood acceptance may run only as an explicit Dogfood Acceptance Pack task
   after `cairn audit secrets` passes in both the Cairn Memory checkout and the
   target project.

## Environment and commands

- Python >= 3.11
- Runtime: Python stdlib only
- Dev dependency: pytest only

Install:

```bash
pip install -e ".[dev]"
```

Test:

```bash
pytest -q
```

Run tests before every commit.

DB pragmas are set in `db.connect()`, not in migrations:

```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
PRAGMA foreign_keys=ON;
```

## Implementation order

Do not reorder.

1. Skeleton:
   - `pyproject.toml`
   - `omni` entrypoint
   - `config.py`
   - `ids.py`
   - `cairn init`

2. `redact.py` MINIMAL:
   - env reverse lookup
   - regex pack
   - fail-closed / stub behavior
   - tests

3. `hook.py`:
   - stdin → `redact_minimal` → spike dump / spool
   - `cairn init --install-claude-hooks`
   - `scripts/create_sandbox.sh`

4. `migrations/001_init.sql`:
   - migration runner
   - `db.py`

5. `parse.py`:
   - transcript JSONL → normalized events
   - unknown lines → redacted `transcript_archive`

6. `store.py`, `spool.py`, `ingest.py`:
   - content-addressed artifact store
   - ingest queue
   - reconcile by `tool_use_id`
   - `duration_ms`
   - watchdog
   - `cairn run show`

7. `redact.py` FULL:
   - entropy detector
   - skip list
   - allowlists
   - fixtures corpus
   - `cairn audit secrets`
   - scan the ENTIRE `.omni/` tree, including `spike/` and `spool/`

8. Extractors and gate:
   - `extract/pm.py`
   - `extract/scripts.py`
   - `gate.py`
   - non-interactive `cairn review approve|reject <id>`

9. Renderer and injection:
   - `render.py`
   - `inject.py`
   - `cairn render`
   - `cairn inject claude`

10. Docs:
   - `docs/demo.md`
   - manual cold/warm procedure
   - G6 robust criterion
   - final definition-of-done checklist

## Codex working agreement

One step = one commit.

Commit message format:

```text
dayN: <step> — <what works now>
```

Commit body must include the `pytest -q` summary.

When Claude Code hook or transcript behavior is UNKNOWN:
- do not invent fields
- unknown keys go to `events.meta`
- unknown transcript lines go to redacted `transcript_archive`
- the human runs the spike and fills `docs/spike-report-template.md`
- code adapts only to recorded facts

## Week-1 Definition of Done

- `pytest -q` green
- redaction positives: 100% recall on curated fixtures
- redaction negatives: 0 false positives on curated negative corpus
- no open-world false-positive claim
- `cairn audit secrets` exits 0 on the sandbox after a real session
- full `.omni/` tree scan passes
- manual cold/warm demo passes per `docs/demo.md`
- warm run satisfies G6 ROBUST criterion on 3/3 golden tasks
- `golden_demo.sh` is optional harness coverage only; manual `docs/demo.md`
  acceptance remains authoritative
