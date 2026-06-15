# CLI-only Claude Code v1 Readiness

## Product Shape

CLI-only Claude Code v1 is the first productized Cairn Memory shape:

- local Python CLI only
- Claude Code only
- project-local `.omni/` state only
- no background service
- no MCP server
- no vector search
- no dashboard or TUI
- no adapter layer beyond Claude Code hooks
- no automatic success inference or automatic memory evolution

The goal is not to add another memory type. The goal is to make the existing
closed loop installable, discoverable, and explainable for one Claude Code user:

```text
Claude Code run
-> redacted trace
-> ingest
-> behavior eval
-> user-marked outcome
-> reviewable experience/failure memory
-> render
-> next Claude Code run
-> measurable behavior comparison
```

## Existing Capabilities

The runtime already has the pieces needed for the loop:

- `cairn init`
- `cairn audit secrets`
- `cairn init --install-claude-hooks --yes`
- `cairn inject claude --mode preview`
- `cairn inject claude --mode link`
- `cairn ingest`
- `cairn status`
- `cairn eval run <run_id>`
- `cairn eval dogfood --cold <run_id> --warm <run_id>`
- `cairn outcome mark <run_id>`
- `cairn outcome mark-from-verify <run_id>`
- `cairn outcome show <run_id>`
- `cairn experience extract|ls|show|approve|reject`
- `cairn experience note ls|show|retire`
- `cairn failure extract|ls|show|approve|reject`
- `cairn failure pattern ls|show|retire`
- `cairn verify`
- `cairn render`

CLI-only v1 starts by making the required safety and ingestion commands
discoverable in `cairn --help`: `audit` and `ingest` are public commands.
Lower-level debug or review internals such as `run` and `review` remain hidden
from top-level help until they have a deliberate user-facing shape.

## First-run Path

The operator-facing command sequence is maintained in
`docs/cli-only-claude-code-v1-runbook.md`.

For the Cairn Memory checkout:

```powershell
cd C:\Users\Jiarui Li\Documents\OmniAgent
pip install -e ".[dev]"
where cairn
pytest -q
cairn audit secrets
```

For a Claude Code target project:

```powershell
cd <target-project>
cairn init
cairn audit secrets
cairn init --install-claude-hooks --yes
cairn inject claude --mode preview
cairn inject claude --mode link
```

The real-project rule remains unchanged: do not install hooks into a real
project until `cairn audit secrets` passes in that checkout.

After a Claude Code session:

```powershell
cairn ingest
cairn audit secrets
cairn status
cairn eval run <run_id>
cairn verify
cairn outcome mark-from-verify <run_id> --success --task-type validation
cairn experience extract <run_id>
cairn experience ls
cairn failure extract <run_id>
cairn failure ls
# inspect candidates, then approve or reject explicitly
cairn render --diff
cairn render
```

Human review remains explicit. v1 does not approve experience notes or failure
patterns automatically. Take `<run_id>` from the `cairn ingest` `run_ids=...`
output, and use `--success` only after a passing verification command. Rendering
only includes already approved notes and active failure patterns.

## Acceptance Criteria

CLI-only Claude Code v1 is ready when these are true:

1. A fresh user can discover the supported command path from `cairn --help`,
   subcommand help, and one runbook.
2. The runbook includes a first-run path, post-run ingest path, review path, and
   rollback/retire path.
3. The real-project safety gate is clear: `cairn audit secrets` must pass before
   hook installation.
4. Read-only commands are documented and tested to avoid migrations and SQLite
   writes.
5. Approved writers are documented and limited to the AGENTS.md command list.
6. `memory.md` rendering still excludes run ids, candidate ids, note ids,
   pattern ids, evidence payloads, timestamps, confidence, and raw stderr.
7. A temporary-project smoke proves the public CLI path can initialize and
   render memory without relying on private test helpers; lifecycle tests cover
   note and pattern retirement.
8. A real Claude Code dogfood record demonstrates at least one cold/warm
   comparison using the v1 path.

## Implementation Order

1. Make the existing v1 path discoverable in CLI help.
2. Add a concise CLI-only user runbook.
3. Add a temporary-project CLI smoke that uses only public commands.
4. Run one real Claude Code dogfood acceptance pass using the runbook.
5. Write a closeout record with the exact commands, run ids, audit result, and
   dogfood verdict.

## Non-goals

Do not implement these in CLI-only Claude Code v1:

- MCP
- vector search
- dashboard or TUI
- adapter layer for other agents
- Computer Use
- LLM extractors
- Soul runtime
- new database tables
- new memory types
- automatic success inference
- automatic failure memory
- automatic memory evolution
- supersede or reactivation lifecycle
