# CLI-only Claude Code v1 Runbook

This runbook is the operator path for the first CLI-only Cairn Memory product
shape. It assumes one local Claude Code user, project-local `.omni/` state, and
no service, MCP server, dashboard, vector search, or adapter layer.

## Preconditions

- Python 3.11 or newer
- Claude Code installed
- Cairn Memory installed from the local checkout with `pip install -e ".[dev]"`
- On Windows, `where cairn` resolves to the intended executable

## Install and Local Safety Check

Run this in the Cairn Memory checkout:

```powershell
cd C:\Users\Jiarui Li\Documents\OmniAgent
pip install -e ".[dev]"
where cairn
pytest -q
cairn audit secrets
```

Do not install hooks into a real target project until this checkout passes
`cairn audit secrets`.

## Target Project Setup

Run this from the target project root:

```powershell
cd <target-project>
cairn init
cairn audit secrets
cairn init --install-claude-hooks --yes
cairn inject claude --mode preview
cairn inject claude --mode link
```

`cairn inject claude --mode preview` should show only the managed region. The
link mode must not modify user-authored `CLAUDE.md` content outside:

```md
<!-- omni:begin -->
@.omni/generated/memory.md
<!-- omni:end -->
```

## Run Claude Code

Start a fresh Claude Code session in the target project. Use a normal task
prompt. Do not over-prompt the expected command if you are trying to measure
whether memory changes behavior.

For a validation dogfood run, a suitable prompt is:

```text
Please validate this project and tell me whether the current setup works. Use the project memory if available.
```

## After a Claude Code Run

Run:

```powershell
cairn ingest
cairn audit secrets
cairn status
```

Record the new `run_id` from the `cairn ingest` `run_ids=...` output, then
inspect behavior:

```powershell
cairn eval run <run_id>
cairn verify
cairn outcome mark-from-verify <run_id> --success --task-type validation
cairn outcome show <run_id>
cairn outcome ls
```

`cairn verify` is read-only with respect to Cairn Memory state. In the post-verify
flow, the write into the Outcome Log happens through
`cairn outcome mark-from-verify`. Use
`--success` only after a passing verification command; use `--failed` or
`--unknown` when the user has not confirmed task success.

For the full `reason_code` enumeration and the `reason_code` → `tests_status`
mapping used by `cairn outcome mark-from-verify`, see
[Verify reason codes](experience-memory-v0.md#verify-reason-codes-v05-reference)
in `docs/experience-memory-v0.md`.

`cairn outcome show <run_id>` shows one run; `cairn outcome ls` lists every
recorded outcome with a per-field tally (status, tests_status, memory_effect,
task_type). Both are read-only with respect to Cairn Memory state.

## Review and Render Memory

Extract reviewable candidates:

```powershell
cairn experience extract <run_id>
cairn experience ls
cairn failure extract <run_id>
cairn failure ls
```

Inspect candidates before approving:

```powershell
cairn experience show <exp_cand_id>
cairn failure show <failure_cand_id>
```

Approve or reject explicitly:

```powershell
cairn experience approve <exp_cand_id>
cairn experience reject <exp_cand_id>
cairn failure approve <failure_cand_id> --summary "<summary>" --suggested-action "<action>"
cairn failure reject <failure_cand_id>
```

Render only after review:

```powershell
cairn render --diff
cairn render
cairn audit secrets
```

## Withdraw Rendered Guidance

Experience notes and failure patterns are withdrawable without deleting their
evidence:

```powershell
cairn experience note ls
cairn experience note show <note_id>
cairn experience note retire <note_id>
cairn failure pattern ls
cairn failure pattern show <pattern_id>
cairn failure pattern retire <pattern_id>
cairn render --diff
cairn render
```

Retired notes and retired patterns do not render into
`.omni/generated/memory.md`. v1 does not support reactivation or supersede.

## Dogfood Comparison

Compare a cold or older run against a warm run:

```powershell
cairn eval dogfood --cold <old_run_id> --warm <new_run_id>
```

For a read-only consolidated review of one warm run (behavior eval, recorded
outcome when present, and optional cold/warm pairwise compare), use the
top-level command instead of chaining the low-level eval/outcome commands:

```powershell
cairn dogfood --warm <new_run_id>
cairn dogfood --warm <new_run_id> --cold <old_run_id>
```

`cairn dogfood` does not ingest, verify, or mark outcomes. Use
`scripts/dogfood_ritual.py` when you need the full write-path governance ritual.

Treat cold/warm comparison as stronger evidence than a single-run
`memory_effect`, especially when Claude Code imports memory without emitting an
explicit `Read` event for `CLAUDE.md` or `.omni/generated/memory.md`.

## Pass Criteria

For a validation task, a strong pass is:

- `cairn audit secrets` passes after ingest and after render.
- The warm run executes the known verification command.
- The first expected verification command appears before README/package/deploy
  rediscovery and before broad scans.
- `cairn eval dogfood` reports `improvement=true`.

A partial pass is still useful evidence if rediscovery decreases and the
expected command is adopted, but pre-command rediscovery remains.
