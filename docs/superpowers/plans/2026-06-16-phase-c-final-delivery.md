# Phase C Final Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the currently approved Phase C deliverable by adding fresh multi-sample OpenCode dogfood evidence and synchronized delivery documentation without expanding Cairn Memory scope.

**Architecture:** This plan adds evidence and tests only. It does not change runtime behavior, schemas, CLI surfaces, adapters, or write paths. OpenCode remains a coding agent and Cairn Memory remains the governed brain layer with read-only agent-facing surfaces and human-invoked CLI writers.

**Tech Stack:** Python 3.11+, pytest, Markdown docs, existing Cairn Memory CLI, OpenCode via `npx -y opencode-ai@latest run --format json` with observed version `1.17.7`.

---

## Files

- Modify: `tests/test_docs.py`
- Create: `docs/phase-c-final-delivery-2026-06-16.md`
- Modify: `docs/opencode-dogfood-2026-06-15.md`
- Modify: `README.md`

## Task 1: Document Acceptance Guard

- [x] **Step 1: Write the failing docs test**

Add `test_phase_c_final_delivery_doc_records_multisample_opencode_proof` to `tests/test_docs.py`. The test must require the final evidence doc to contain:

- approved Phase C scope only
- OpenCode multi-sample dogfood
- read-only consumer wording
- safety invariants
- exact Cairn Memory read-surface and writer commands
- explicit categories for verified work, remaining dogfood, non-goals, and next tasks
- no local absolute Windows path or user identity leakage

- [x] **Step 2: Run the test and verify RED**

Run:

```powershell
python -m pytest tests/test_docs.py::test_phase_c_final_delivery_doc_records_multisample_opencode_proof -q
```

Observed: failed because `docs/phase-c-final-delivery-2026-06-16.md` did not exist.

## Task 2: OpenCode Dogfood Evidence

- [x] **Step 1: Create a disposable sandbox**

Run from the worktree:

```powershell
$repo = (Resolve-Path .).Path
$sandbox = Join-Path $env:TEMP ("cairn-phase-c-final-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
powershell -ExecutionPolicy Bypass -File "$repo\scripts\create_sandbox.ps1" $sandbox
```

- [x] **Step 2: Initialize Cairn Memory and verify secrets**

Run inside the sandbox with the worktree source on `PYTHONPATH`:

```powershell
$env:PYTHONPATH = "$repo\src"
python -m omni.cli init
python -m omni.cli audit secrets
python -m omni.cli ingest bootstrap_static
python -m omni.cli render
python -m omni.cli inject opencode --mode link
```

Expected: `audit secrets` exits 0 and `opencode.json` contains `.omni/generated/memory.md` in `instructions`.

- [x] **Step 3: Record read surfaces before OpenCode**

Run:

```powershell
python -m omni.cli memory read
python -m omni.cli failure read
python -m omni.cli verify plan
python -m omni.cli task read
```

Expected: read-only commands expose command memory, failure memory, verify selection, and task state without migrating or writing.

- [x] **Step 4: Run at least two fresh OpenCode samples**

For each sample:

```powershell
python -m omni.cli task start "<intent>" --task-type validation
npx -y opencode-ai@latest run --format json --model apiyi/deepseek-chat --agent build --dangerously-skip-permissions "<prompt>" > <sample>.jsonl
python -m omni.cli ingest <run_id> --engine opencode --transcript <sample>.jsonl
python -m omni.cli run show <run_id>
python -m omni.cli task close --success --from-verify [--profile release]
python -m omni.cli audit secrets
```

Observed: `run show` recorded command previews showing OpenCode used Cairn Memory read surfaces before `pnpm run test` and `pnpm run build`; outcome evidence was written through task close.

## Task 3: Evidence Documentation

- [x] **Step 1: Create `docs/phase-c-final-delivery-2026-06-16.md`**

The doc must record only observed evidence. It must avoid local absolute paths and identities, and it must separate:

- implemented and verified
- implemented but needing more dogfood samples
- explicitly not implemented
- next smallest high-value tasks

- [x] **Step 2: Update prior OpenCode evidence conclusion**

Modify `docs/opencode-dogfood-2026-06-15.md` to point to the new final delivery evidence instead of leaving the single-sample caveat as the latest state.

- [x] **Step 3: Link the delivery evidence from README**

Modify `README.md` to link `docs/phase-c-final-delivery-2026-06-16.md` in the proof/artifact section.

- [x] **Step 4: Run docs tests**

Run:

```powershell
python -m pytest tests/test_docs.py -q
```

Observed: `14 passed, 1 warning`.

## Task 4: Review and Final Verification

- [x] **Step 1: Request code/evidence review**

Dispatch a reviewer with the diff range and require review against:

- approved Phase C scope
- evidence accuracy
- no local identity leakage
- no overclaiming beyond observed samples
- code/doc elegance

- [x] **Step 2: Fix Critical and Important review issues**

Re-run the targeted docs test and any commands affected by the fix.

Observed: reviewer found no Critical issues. Important issues were fixed by
making the evidence document self-contained, recording OpenCode version 1.17.7,
using the canonical writer path, strengthening docs tests, and removing local
path or identity strings from the plan. Final reviewer approved with no
Critical or Important blockers.

- [x] **Step 3: Run final gates**

Run:

```powershell
python -m pytest -q
git diff --check
python -m omni.cli audit secrets
```

Also run a compact read-only invariant proof using the current code/tests:

```powershell
python -m pytest tests/test_cli_smoke.py tests/test_db.py tests/test_task.py -q
```

Observed:

- `python -m pytest -q`: 622 passed, 3 skipped, 1 warning.
- `git diff --check`: pass.
- `python -m omni.cli audit secrets`: ok=true.
- `python -m pytest tests/test_cli_smoke.py tests/test_db.py tests/test_task.py -q`: 131 passed, 3 skipped, 1 warning.

- [x] **Step 4: Commit, push, and triage bots**

Commit with the required format and push the branch:

```powershell
git status --short
git add tests/test_docs.py docs/phase-c-final-delivery-2026-06-16.md docs/opencode-dogfood-2026-06-15.md README.md docs/superpowers/plans/2026-06-16-phase-c-final-delivery.md
git commit -m "dayC: phase c final delivery — OpenCode evidence is multisample"
$branch = git branch --show-current
git push -u origin $branch
gh pr create --base main --head $branch --title "Phase C final delivery evidence" --body-file <generated-body>
gh pr checks <pr-url> --watch
gh pr view <pr-url> --comments
```

Observed:

- Branch pushed and PR opened as `Phase C final delivery evidence`.
- GitHub CI checks passed for Python 3.11 and 3.12.
- SonarCloud quality gate passed.
- Cursor Approval Agent approved the PR.
- CodeRabbit completed review. Its only actionable item was this checkbox state
  update; no Critical or Important blocker was reported.
