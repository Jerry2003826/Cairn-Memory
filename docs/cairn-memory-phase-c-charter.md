# Cairn Memory Phase C Charter (DRAFT — partial approvals landed)

Date: 2026-06-15
Status: **C-1**, **C-2 OpenCode v0**, **C-3**, **C-4 read-only MCP**, **C-5**,
and **QwenCode v0** are approved and merged or implemented. Remaining
Product/Runtime scope is still draft/proposed. Any remaining Phase C sub-project
still requires explicit approval and a matching `AGENTS.md` update before
implementation — the same rule Phase B used.

## Purpose

The 2026-06-15 vision reframes Cairn Memory as an **agent-agnostic** governed brain
layer for AI Coding Agents (Claude Code, Codex, OpenCode, QwenCode, Cursor) — not
a Claude-only memory loop. Phase A/B built the **Kernel** (Layers 1–5) with its
I/O bound to Claude Code. **Phase C opens the boundary toward Cairn Bridge**
(multi-engine adapters + a read-only access surface) **without relaxing any safety
invariant.**

This charter supersedes the "MCP server / multi-engine router / multi-agent" rows
of the Phase B non-goals **only as approved future direction** — implementation
still proceeds one governed sub-project at a time.

## 1. Invariants (unchanged from Phase B — must not relax)

- **Redaction-before-write** — every byte under `.omni/` passes `redact.redact`.
- **`cairn hook` always exits 0** — hooks never write the DB; only append redacted spool lines.
- **Read-only commands** open SQLite `mode=ro`, never run migrations, never write Cairn Memory state.
- **Human review gate** — candidates become active memory only after explicit approve. No automatic success inference, no automatic memory evolution.
- **Render safety** — generated memory must not leak internal ids, evidence, timestamps, or confidence scores.
- **Real-project gate** — no hooks / real dogfood until `cairn audit secrets` exits 0 in both checkouts.

### New invariants introduced by multi-agent scope

- **External agents are read-only consumers.** Any adapter or MCP surface may
  *read* rendered memory, known failures, verify plans, task read views, and
  future approved audit summaries. It **must not** write Cairn Memory state. Every
  write still goes through the human-gated CLI write commands listed in
  `AGENTS.md`.
- **Capture stays append-only and redacted.** A new capture adapter (OpenCode,
  Codex, …) obeys the same contract as the Claude hook: redact → append spool,
  never touch the DB, never block the host agent.

Violations require reverting the commit.

## 2. Vision → repository mapping

| Vision stage | Status in this repo |
|---|---|
| ① Cairn Memory Kernel | **done** (Phase A/B); I/O currently bound to Claude Code |
| ② Cairn Bridge | **foundation done** (C-1 capture/inject seams + C-3 machine read); **C-2 OpenCode v0 done**; **QwenCode v0 done**; **C-4 read-only MCP done** |
| ③ Cairn Runtime (task lifecycle, multi-agent handoff) | **C-5 partial done** — task lifecycle only; handoff deferred |
| ④ Product (orchestration, permission tiers, UI) | deferred |

## 3. Relaxations (Phase C only)

| Area | Pre-C boundary | Phase C allowance |
|---|---|---|
| Agent binding | Claude-only hook / transcript / `CLAUDE.md` | **C-1 done:** capture + inject-target seams with Claude as the first implementation; **C-2 done:** OpenCode v0 as one real second engine; **QwenCode v0 done:** project-local context injection plus transcript ingest |
| MCP | forbidden | **C-4 done:** a read-only stdio MCP server over the machine-read surface — **no write tools** |
| Machine read | human-facing CLI text only | **C-3 done:** stable JSON for `cairn memory read`, `cairn failure read`, and `cairn verify plan`; audit summary remains future scope |
| Inject target | `CLAUDE.md` only | **C-1 done:** parametrized managed-region injection; new targets require recorded syntax, not guesses |

**Still forbidden in Phase C** (defer to Runtime/Product): multi-agent orchestration /
handoff, permission tiers, dashboard / TUI, vector / embedding search, LLM extractors,
automatic memory evolution, **any external write path**, Computer Use.

**Approved and landed for C-2 OpenCode v0:** OpenCode config injection and
transcript ingest only. `cairn inject opencode` may update project-local
`opencode.json` by adding
`.omni/generated/memory.md` to the official OpenCode `instructions` list.
`cairn ingest --engine opencode --transcript <path>` may ingest UTF-8 JSONL output
from `opencode run --format json` through the existing redacted ingest path.
OpenCode plugins, background capture processes, write-capable MCP tools, permission tiers, and
multi-agent handoff remain deferred.

**Approved and landed for QwenCode v0:** QwenCode project-context injection and
transcript ingest only. `cairn inject qwen` may update project-local `QWEN.md`
by managing only the Cairn Memory region that imports
`@.omni/generated/memory.md`. `cairn ingest --engine qwen --transcript <path>`
may ingest UTF-8 JSONL output from `qwen --output-format stream-json` through
the existing redacted ingest path. QwenCode plugins, background capture
processes, global `~/.qwen` edits, write-capable MCP tools, permission tiers,
and multi-agent handoff remain deferred.

**Approved and landed for C-4 read-only MCP:** `cairn mcp serve` exposes exactly
four stdio MCP tools over the existing machine-read surfaces:
`memory_read`, `failure_read`, `verify_plan`, and `task_read`. It adds no
HTTP transport, no write tools, no external DB write path, and no migration.

**Approved and landed in Phase C (Stage ③ — task lifecycle, C-5):** `cairn task *` lifecycle
commands and migration **`008_task_runtime.sql`** (`tasks` table + nullable
`runs.task_id`). Tasks are **operational state, not memory** — closing a task does
not auto-create experience/failure/preference rows or infer success without the
existing human-gated commands.

**v0 decisions (locked for C-5 implementation):**
- Representative run for `task close`: the most recent run attached to the task; if
  none, close records task-level `outcome_status` / `tests_status` only.
- Second `task start` while one is open: hard error (no auto-close / supersede).
- `task close` requires an explicit `--success`, `--failed`, or `--unknown`; no
  silent default outcome status in automation.
- `task read` is scoped to the current project and exposes only leak-free open
  task context.
- `eval` / memory `extract` stay run-keyed in this stage.

## 4. Phase C sub-projects

| Sub-project | Scope | New surface | Migration | Status |
|---|---|---|---|---|
| **C-1: capture/inject seam** | refactor `hook`/`ingest` capture and `inject` into adapter interfaces; Claude becomes one impl behind them (pure refactor, behavior unchanged) | internal interfaces; `cairn inject claude` remains the only target | none | **done** |
| **C-2: OpenCode v0** | OpenCode config injection + UTF-8 `opencode run --format json` transcript ingest; prove one governed OpenCode validation loop end to end | `cairn inject opencode`, `cairn ingest --engine opencode --transcript <path>` | none | **done** |
| **C-3: machine read** | stable read-only JSON for memory / known-failures / verify-plan | `cairn memory read`, `cairn failure read`, `cairn verify plan` (R) | none | **done** |
| **C-4: read-only MCP** | wrap C-3 plus task read as MCP tools, read-only | `cairn mcp serve` (R) | none | **done** |
| **C-5: task lifecycle** | `tasks` table + `runs.task_id`; start/status/ls/show/close/abandon/read; ingest attaches runs to open task | `cairn task *` | **`008_task_runtime.sql`** | **done** |
| **QwenCode v0** | Project-local `QWEN.md` managed-region injection + UTF-8 `qwen --output-format stream-json` transcript ingest | `cairn inject qwen`, `cairn ingest --engine qwen --transcript <path>` | none | **done** |

Historical order: **C-1 → C-3 → C-2 → C-4 → C-5 → QwenCode v0.** C-1, C-2,
C-3, C-4, C-5, and QwenCode v0 have landed or are complete on the active branch.
Migrations beyond 008 follow the approval process in §5.

## 5. Definition of Done, migrations, execution protocol

### Approved migrations (Phase C)

| Migration | Table(s) / change | Sub-project |
|---|---|---|
| `008_task_runtime.sql` | `tasks`; nullable `runs.task_id`; `meta.current_task_id` pointer | C-5 |

Reuse Phase B charter §4 (sub-project DoD template), §5 (migration approval
006 → 007+ → 008+), and §6 (execution protocol: brainstorm → spec → plan → TDD,
one step = one commit). Each Phase C sub-project additionally asserts:

- the read-only external-consumer invariant holds (no adapter/MCP write path)
- a second-engine adapter does not regress the Claude path
- machine-read output passes the same metadata-leak tests as `render`

## 6. Remaining open decisions for the human

1. ~~Which second engine first — OpenCode or Codex?~~ **Resolved:** OpenCode v0 first.
2. ~~Should C-4 expose only the existing C-3 read views first, or add a separately approved read-only audit summary before MCP?~~ **Resolved:** C-4 exposes only existing read surfaces plus `task read`; audit summary remains future scope.
3. ~~Does `task` runtime (Stage ③) stay deferred until Cairn Bridge has a proven second engine?~~ **Resolved:** C-5 (task lifecycle) approved after Cairn Bridge; multi-agent handoff stays deferred.
4. ~~Which adapter after OpenCode?~~ **Resolved:** QwenCode v0 next, limited to
   project-local `QWEN.md` injection and `stream-json` transcript ingest.
