# Week-2 Go / No-Go Gates

These gates decide whether OmniMemory can move from sandbox validation to
dogfood. They are evidence gates, not assumptions. Do not mark any gate passed
until a human-run Claude Code sandbox session provides the evidence in
`docs/week2-spike-report.md`.

## G1: Run identity

PASS requires session_id / cwd / timestamp evidence that is sufficient to
identify each run and distinguish resumed or crashed sessions.

FAIL if runs cannot be tied back to a specific sandbox session.

## G2: Bash evidence chain

PASS requires a Bash evidence chain with command + exit_code + stdout/stderr
available from hook, transcript, or reconciled event data.

FAIL if Bash success, failure, or interrupt scenarios cannot be inspected well
enough to explain what command ran and what happened.

## G3: Transcript unknown lines

PASS requires unknown transcript lines to be low enough for practical parsing or
safely archived with redaction.

FAIL if unknown transcript rows are dropped silently, crash parsing, or preserve
raw sensitive content.

## G4: Real-session audit

PASS requires `omni audit secrets` to exit 0 after the real sandbox session and
after S12 planted-secret validation.

FAIL if any raw planted secret or detected secret remains under `.omni/**`.

## G5: Deterministic extraction

PASS requires deterministic extraction to produce the correct package manager and test/build commands from the sandbox.

FAIL if the generated memory points Claude Code at the wrong package manager,
test command, or build command.

## G6: Warm-run robust behavior

PASS requires the warm run robust criterion:

```text
first matching test command equals injected command
AND no forbidden rediscovery event occurred before it
```

Forbidden and allowed rediscovery events are defined in `docs/demo.md`.

FAIL if Claude Code reads package manager files or enumerates scripts before
using the injected command, or if the first matching test command differs from
the injected command.

## G7: Hook latency

PASS requires in-process hook capture p95 < 250 ms from `omni status`.

process-level latency is sampled separately and recorded in
`docs/week2-spike-report.md`; it is not the G7 gate.

FAIL if in-process capture p95 is 250 ms or higher after excluding unrelated
process startup measurement.

## Dogfood Entry

Dogfood entry requires all of the following:

- G1-G7 pass.
- The spike report is completed.
- There are no PENDING HUMAN EVIDENCE cells in sections 2, 3, 11 of `docs/week2-spike-report.md`.
- There are no raw secrets in .omni/**.
- There is no uncontrolled modification outside the CLAUDE.md managed region.

If any item fails, the decision is No-Go. Fix only the minimal failing
adapter/parser/render/inject behavior proven by the sandbox evidence, then rerun
the affected scenario and the full verification suite.
