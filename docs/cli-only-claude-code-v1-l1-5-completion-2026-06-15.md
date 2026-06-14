# CLI-only Claude Code v1 — Layers 1–5 Completion Check

Date: 2026-06-15

## Purpose

Make the Definition-of-Done for the memory-and-verification base (layers 1–5 of
the OmniAgent vision) explicit and auditable. This is a closeout check, not a new
feature: it adds no tables, migrations, agents, UI, or memory types, and it stays
inside the CLI-only Claude Code v1 boundary defined in `AGENTS.md`.

## Scope

"Complete" here is the v1 DoD: the existing layers 1–5 are stable, test-guarded,
and documented. It explicitly excludes new memory types that would need new
tables (preference / architecture / review / release memory) and task-profile
verification that depends on a task runtime — those are later phases (layers
6–9).

## Layer DoD and evidence

### Layer 1 — Memory Kernel
DoD: the rendered memory kinds (fast path, commands, experience notes, known
failures) render deterministically and never leak internal ids, evidence,
timestamps, or confidence.
- `src/omni/render.py`; section order Fast Path · Commands · Experience Notes · Known Failures · Boundaries · Project.
- `tests/test_render.py` asserts `confidence`, `created_at`, `evidence`, and hidden `run_id` / `event_id` do not appear in rendered output.

### Layer 2 — Trace & Evidence
DoD: capture redacts before write, archives unknown transcript lines, and catches
the sandbox secret classes.
- `src/omni/redact.py` (regex pack + env reverse lookup + skiplist); `tests/test_redact.py` covers `AKIA…` and `ghp_…` (the sandbox secrets); `tests/test_audit.py` covers audit capture.
- `src/omni/parse.py` archives unknown lines; `tests/test_parse.py` covers `invalid_json`, `unknown_transcript_shape`, and archive truncation.
- AGENTS safety rules 1–3 (redaction-before-write, `omni hook` always exits 0, hooks never write the DB).

### Layer 3 — Behavior Eval
DoD: `memory_effect` branches are stable, cold/warm comparison works, and the
semantics are documented.
- `src/omni/eval.py` (`_classify`); `tests/test_eval.py` covers `helped` / `neutral` / `failed_to_help` / `unknown` and the dogfood summary.
- `docs/cli-only-claude-code-v1-eval-semantics.md` (new).
- Real evidence: `docs/cli-only-claude-code-v1-closeout-2026-06-15.md` (rediscovery 10 → 0).

### Layer 4 — Verify & Outcome
DoD: `omni verify` is read-only to OmniMemory state, every reason code is
documented, and the outcome bridge is stable.
- `src/omni/verify.py` (read-only connection); `tests/test_verify.py` covers the read-only invariant, every reason code, CLI exit codes, and `ambiguous_qualifier` at the CLI layer.
- `docs/cli-only-claude-code-v1-verify-reason-codes.md` (new).
- `omni outcome mark-from-verify` bridge; `scripts/dogfood_ritual.py` orchestration.

### Layer 5 — Governed Learning
DoD: the candidate → approve → render → retire loop is stable and illegal
transitions are rejected.
- `src/omni/experience.py` / `src/omni/failure.py`; `tests/test_experience.py` (approved cannot be rejected, rejected cannot be approved, reject prevents recreation) and `tests/test_failure.py` (retire reports `can_reactivate=false`, `supersede_supported=false`).

## Global acceptance

- `pytest -q`: 492 passed, 3 skipped, 1 warning.
- `git diff --check`: clean.
- Each layer DoD has test and/or documentation evidence above.
- Docs are consistent with `AGENTS.md`.

## Ongoing (governed practice, not code work)

These stay outside the code base by design and accrue with real use:

- Layer 3 statistical cold/warm evidence accumulates from real Claude Code
  sessions via `scripts/dogfood_ritual.py`, per
  `docs/cli-only-claude-code-v1-dogfood-cadence.md`. The "no automatic execution
  of Claude Code" boundary is kept.
- Experience and failure approvals stay human-reviewed.
- Renderer wording is retuned from real dogfood feedback.

## Boundary

No new tables, migrations, agents, UI, or LLM extractors; no automatic Claude
Code execution; no automatic success inference. Layers 6–9 (agent orchestration,
task runtime, policy/permission, governance UI) remain out of scope for this
phase.
