# Cairn Memory Customer Trial Pack

This pack gives a customer a low-risk trial of Cairn Memory without requiring a real agent account, model API key, dashboard, or background service.
It proves the governed brain layer on a disposable sandbox first, then shows where
a real Claude Code, OpenCode, or QwenCode run plugs in.

## What This Trial Proves

- Cairn Memory stores all project state under local `.omni/`.
- `cairn audit secrets` can be run before and after the trial.
- `cairn render` produces deterministic project memory.
- `cairn inject claude`, `cairn inject opencode`, and `cairn inject qwen` wire
  the generated memory into project-local agent context files only.
- `cairn eval dogfood` can show a measurable cold/warm improvement.
- `scripts/mcp_client_acceptance.py` can call `memory_read`, `failure_read`,
  `verify_plan`, and `task_read` through a real stdio MCP client.

## What This Trial Does Not Prove

- It is not a full product dashboard or memory console.
- It does not implement multi-agent handoff or product-level orchestration.
- It does not grant any external write path to agents.
- It does not edit global Claude, OpenCode, or QwenCode configuration.
- It does not prove broad behavioral improvement across every customer repo.

Those are Runtime/Product scope items and remain separate from the trial pack.

## Ten-Minute Local Trial

From this checkout:

```powershell
pip install -e ".[dev]"
bash scripts/customer_trial_demo.sh
```

The script creates a disposable sandbox under the system temp directory unless a
target path is supplied:

```powershell
bash scripts/customer_trial_demo.sh /tmp/cairn-customer-trial
```

The target must not already contain `.omni/`; this prevents accidental reuse of
old trial state.

Expected terminal output includes:

```text
customer_trial_report: <sandbox>/.customer-trial/report.json
sandbox: <sandbox>
```

Open the report JSON to review the result:

```powershell
cat <sandbox>/.customer-trial/report.json
```

The report should show:

- `"ok": true`
- `"dogfood_improvement": true`
- `"mcp_ok": true`
- `"audit_ok": true`
- all four MCP tools listed under `"mcp_tools"`

## Files Created In The Sandbox

The disposable sandbox contains:

- `.omni/` — Cairn Memory local state
- `.omni/generated/memory.md` — rendered governed memory
- `CLAUDE.md` — project-local Claude Code context with the Cairn managed region
- `opencode.json` — project-local OpenCode instructions entry
- `QWEN.md` — project-local QwenCode context with the Cairn managed region
- `.customer-trial/` — synthetic transcripts, command outputs, and report JSON

The synthetic transcripts are intentionally simple. They model a cold run that
rediscovers `README.md` and `package.json` before testing, and a warm run that
uses `memory read` and `verify plan` before testing. They are there so customers
can validate the governed loop without connecting a model account.

## Real-Agent Trial After The Sandbox Passes

After the sandbox report is green, run a real agent trial in a customer repo only
after:

```powershell
cairn audit secrets
```

passes in both this checkout and the target repo.

For Claude Code:

```powershell
cairn init --install-claude-hooks --yes
cairn render
cairn inject claude --mode link
```

For OpenCode:

```powershell
cairn render
cairn inject opencode --mode link
cairn ingest <run_id> --engine opencode --transcript <utf8-jsonl>
```

For QwenCode:

```powershell
cairn render
cairn inject qwen --mode link
cairn ingest <run_id> --engine qwen --transcript <utf8-jsonl>
```

For an MCP-capable client:

```powershell
cairn mcp serve
```

Then have the client call only these read tools:

- `memory_read`
- `failure_read`
- `verify_plan`
- `task_read`

## Safety Story For Customers

- Local-first: no Cairn Memory cloud service is required.
- Redaction-before-write: content written under `.omni/` goes through the
  redactor.
- Human-gated writes: there is no write-capable external surface for agents.
- Read-only MCP: the MCP server exposes only read surfaces.
- Reversible trial: delete the disposable sandbox to remove all trial state.

## Recovery

If the trial fails:

1. Check the report file: `.customer-trial/report.json`.
2. Check command outputs in `.customer-trial/`.
3. Run `cairn doctor` inside the sandbox.
4. Run `cairn audit secrets` inside the sandbox.
5. Delete the sandbox and rerun `bash scripts/customer_trial_demo.sh`.

If a supplied target path already contains `.omni/`, choose a fresh path instead
of reusing old trial state.
