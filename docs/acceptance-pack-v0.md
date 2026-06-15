# Acceptance Pack v0

Acceptance Pack v0 is a small, deterministic procedure for packaging the existing
evidence of an **already-ingested** run. It does not start a new Claude Code
session, add runtime features, add new memory types, or add new database tables.
It only replays existing read-only commands and explicitly run approved writer
steps, then records redacted, bounded fields.

Acceptance Pack v0 is **evidence packaging, not causal proof**. A single run is
evidence about observed behavior. The strongest claim comes from a comparable
cold/warm pair, not from one run in isolation.

For running a fresh warm run end-to-end, use
[`dogfood-acceptance-pack-v0.md`](dogfood-acceptance-pack-v0.md) instead. This
pack focuses on summarizing evidence that is already in the database.

## Read-only vs writer commands

Read-only commands open SQLite read-only, run no migrations, and write no
Cairn Memory state. `cairn verify` is read-only for Cairn Memory state but executes
the selected project verification command.

| Command | Class | Notes |
| --- | --- | --- |
| `cairn status` | read-only | filesystem/state summary, no DB write |
| `cairn eval run <run_id>` | read-only | heuristic behavior classification |
| `cairn eval dogfood --cold <id> --warm <id>` | read-only | cold/warm comparison |
| `cairn verify` | read-only (executes command) | no Cairn Memory write; runs the selected verification command |
| `cairn outcome show <run_id>` | read-only | reads the existing outcome row |
| `cairn outcome mark-from-verify <run_id>` | **approved writer** | the explicit verify->outcome write bridge |
| `cairn experience extract <run_id>` | **approved writer** | run explicitly by a human; creates reviewable candidates |
| `cairn failure extract <run_id>` | **approved writer** | run explicitly by a human; creates reviewable candidates |

`cairn audit secrets` is not a SQLite writer. It scans the `.omni/` tree and
writes only the existing audit marker `.omni/audit/secrets.passed` when it
passes. Approved writers must be run explicitly by a human; this pack never runs
`experience extract` or `failure extract` for you, because they are writers.

## Step 0 - Gate

```bash
cairn audit secrets
cairn status
```

Expected:

- `cairn audit secrets`: `ok=true`, with empty `positive_failures`,
  `negative_failures`, and `omni_leaks`. Do not continue if this fails.
- `cairn status`: `ok=true`, and the `omni_dir`, `database`, and (if memory was
  rendered) `generated_memory` / `claude_link` flags reflect the project state.

## Step 1 - Behavior Eval (read-only)

```bash
cairn eval run <run_id>
```

Record these fields (all redacted and bounded already):

- `memory_effect`: `helped`, `neutral`, `failed_to_help`, or `unknown`
- `claude_md_read`, `memory_md_read`
- `expected_verification_executed`
- `first_expected_command`, `first_expected_command_position`
- `rediscovery_count`
- `reason`
- `active_expected_commands`
- `observed_commands` and `observed_commands_omitted`
- `rediscovery_events_before_first_expected_command` and
  `rediscovery_events_omitted`

Caveat: a single-run `memory_effect` can remain `neutral` even on a good run
when Claude Code memory import is not observable as an explicit `Read` event.
Treat `neutral` here as "not observed", not as "memory did not help".

## Step 2 - Dogfood cold/warm comparison (read-only)

```bash
cairn eval dogfood --cold <cold_run_id> --warm <warm_run_id>
```

Record these fields:

- `cold_run_id`, `warm_run_id`
- `cold_comparable`
- `cold_rediscovery_count`, `warm_rediscovery_count`
- `cold_first_expected_command_position`, `warm_first_expected_command_position`
- `command_adopted`
- `improvement`
- `memory_effect_summary` (cold, warm, summary)

The dogfood cold/warm comparison is the stronger behavior metric. `improvement`
requires a comparable cold run with recorded events and a warm run that executed
an expected command. A missing or event-less cold run reports
`cold_comparable=false` and does not count as improvement.

## Step 3 - Verify preflight (read-only for Cairn Memory state)

```bash
cairn verify
# or, when the target uses a qualifier-scoped command:
cairn verify --qualifier <qualifier>
```

`cairn verify` opens SQLite read-only and writes no Cairn Memory state, but it does
execute the selected `uses_test_command`. Record these stable JSON fields:

- `status`: `passed`, `failed`, or `unknown`
- `reason_code`: e.g. `passed`, `failed_exit_code`, `timed_out`, `start_failed`,
  `no_active_test_command`, `ambiguous_active_test_command`, `qualifier_not_found`,
  `ambiguous_qualifier`, or a `parse_error_*` code
- `command`, `qualifier`, `predicate`
- `selection_mode`, `selection_reason`
- `exit_code`, `timed_out`, `duration_ms`
- `stdout_truncated`, `stderr_truncated`

Do not paste the `stdout_excerpt` / `stderr_excerpt` content into the acceptance
record. Record only the status, reason code, exit code, and the truncation flags.
There must be no raw stdout/stderr or artifact payloads in the acceptance report.

## Step 4 - Outcome (approved writer + read-only show)

The verify->outcome write bridge is the only approved way to record a verify
result into the Outcome Log:

```bash
cairn outcome mark-from-verify <run_id> --task-type validation
cairn outcome show <run_id>
```

`cairn outcome mark-from-verify` derives `tests_status` from the verify
`reason_code` only:

- `reason_code=passed` -> `tests_status=passed`
- `reason_code=failed_exit_code` or `timed_out` -> `tests_status=failed`
- `start_failed` and every selection/parse failure -> `tests_status=unknown`

It never infers task success. Outcome `status` is user-marked: it stays
`unknown` unless the human explicitly passes `--success`, `--failed`, or
`--unknown`. Re-running it is idempotent: it preserves `created_at` and advances
`updated_at`.

`cairn outcome show <run_id>` (read-only) records:

- `status`, `tests_status`, `memory_effect`, `task_type`
- `final_command`
- `evidence`: a redacted, bounded verify summary that excludes raw stdout and
  stderr excerpts
- `created_at`, `updated_at`

## Step 5 - Experience and failure extract status (approved writers, explicit)

These are **approved writers** and must be run explicitly by a human. They do
not run automatically as part of this pack. They create reviewable candidate rows
only; nothing renders into memory until a human approves a candidate.

```bash
cairn experience extract <run_id>
cairn failure extract <run_id>
```

Record only the extraction status, not raw payloads:

- experience extract: `created=<N>` and the candidate `kind`/`state` if created
- failure extract: `created=<N>` and the candidate `failure_kind`/`state` if
  created

If you do not want to write candidate rows during evidence packaging, record the
extraction status as `unknown` and skip these writer steps. Do not infer a
candidate exists without running the explicit writer.

## Required semantics

1. Acceptance Pack v0 is evidence packaging, not causal proof.
2. A single-run `memory_effect` can remain `neutral` when memory import is not
   observable as an explicit read event.
3. The dogfood cold/warm comparison is the stronger behavior metric.
4. Outcome `status` is user-marked or explicitly `mark-from-verify` anchored;
   there is no automatic task success inference.
5. `cairn verify` is read-only for Cairn Memory state but executes the selected
   verification command.
6. `cairn experience extract` and `cairn failure extract` are approved writers and
   must be run explicitly by the human.
7. The acceptance report contains no raw stdout/stderr or artifact payloads.
8. Redaction boundaries are preserved; recorded fields come from already-redacted
   command output.

## Acceptance checklist

- [ ] `cairn audit secrets` passed (`ok=true`).
- [ ] `cairn status` reflects the expected project state.
- [ ] `cairn eval run <run_id>` recorded with `memory_effect` and rediscovery
      fields, with the `neutral` caveat noted.
- [ ] `cairn eval dogfood` recorded with `cold_comparable`, `improvement`, and
      `command_adopted`.
- [ ] `cairn verify` recorded with `status`, `reason_code`, and truncation flags
      only (no raw excerpts).
- [ ] `cairn outcome mark-from-verify` run explicitly; `tests_status` derived from
      `reason_code`; `status` not auto-inferred.
- [ ] `cairn outcome show <run_id>` evidence excludes raw stdout/stderr.
- [ ] experience/failure extract status recorded as explicit-writer output or
      `unknown`; no automatic extraction.
- [ ] No new tables, no new memory types, no new runtime features were added.

## Evidence record

Copy [`dogfood-acceptance-record-template.md`](dogfood-acceptance-record-template.md)
for each packaged run. Keep evidence concise and redacted. Do not paste raw
artifacts, raw stderr, secrets, or large transcript content.
