# OmniMemory v0.4 Closeout Audit

Date: 2026-06-14 local

Branch base audited: `ea5dc16cebacbc100ccaaa606001fe43a883226e`

Merged PRs:

- `#27` (`Jiarui/v04-start-failed-contract`)
- `#28` (`Jiarui/v04-verify-reason-codes`)

## Scope

This closeout covers OmniMemory v0.4 / Verify Polish.

v0.4 did not add product features, tables, migrations, runtime services,
automatic success inference, automatic failure memory, or automatic memory
evolution. It kept the v0.2/v0.3 loop intact and finished the small Verify
contract polish items.

## What Changed

v0.4 settled the open Verify contract and maintenance items:

- `start_failed` remains `status=failed` and CLI exit code `1`.
- Scripts should distinguish process-start failures by
  `reason_code="start_failed"`.
- Verify reason-code literals now have a single source of truth in `verify.py`.
- A blank active `uses_test_command` fact reports
  `parse_error_empty_command` instead of being collapsed into
  `no_active_test_command`.
- `docs/demo.md` now includes the read-only `omni verify` preflight and the
  approved `omni outcome mark-from-verify` bridge.

## Local Verification

Commands run on merged `main`:

```bash
pytest -q
omni audit secrets
git diff --check
```

Results:

- `pytest -q`: `442 passed, 3 skipped, 1 warning`.
- `omni audit secrets`: `ok=true`, no fixture failures and no `.omni` leaks.
- `git diff --check`: pass.

Read-only smoke:

- A temporary project DB was created with one active `uses_test_command` fact.
- `omni verify` exited 0 and printed `stdout_excerpt=42`.
- The SQLite SHA-256 stayed unchanged before and after:
  `1F8F311669A0D69A7F15A8C3C3F9F3F02A8BB17770D774F090BDB5E15E946AD3`.

## Acceptance Matrix

| Area | Status | Evidence | Boundary |
| --- | --- | --- | --- |
| `start_failed` exit contract | Pass | CLI regression covers exit `1`, `status=failed`, and `reason_code=start_failed`. | No behavior change from v0.2/v0.3; this locks the contract. |
| Reason-code maintainability | Pass | `verify.py` centralizes reason-code constants; tests preserve public JSON values. | Public reason-code strings remain unchanged. |
| Empty configured command | Pass | Active blank command now reports `parse_error_empty_command`. | This is malformed configuration, not command selection absence. |
| Manual acceptance docs | Pass | `docs/demo.md` includes `omni verify` and `outcome mark-from-verify`. | G6 behavior proof still depends on cold/warm evidence, not verify alone. |
| Read-only safety | Pass | Temp-project DB hash was unchanged across `omni verify`. | `outcome mark-from-verify` remains the separate approved writer. |
| Migration governance | Pass | Approved migrations remain exactly 001-006. | No v0.4 tables or migrations. |

## Remaining Non-blocking Items

No blocker, major, or minor issue remains for v0.4 closeout.

Possible future work should start as a new explicitly scoped phase. Do not infer
permission from this closeout to add MCP, vector search, dashboard UI, adapters,
LLM extractors, Computer Use, Soul runtime, automatic success inference,
automatic failure memory, or automatic memory evolution.

## Closeout Verdict

OmniMemory v0.4 / Verify Polish is ready to close.

The defensible claim is narrow: Verify now has a locked `start_failed` contract,
centralized reason-code constants, public coverage for blank configured
commands, manual runbook coverage for the verify bridge, and a current
read-only smoke proving `omni verify` leaves SQLite unchanged.
