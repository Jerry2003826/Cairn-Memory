from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_demo_doc_covers_manual_cold_warm_g6_and_definition_of_done() -> None:
    demo = REPO_ROOT / "docs" / "demo.md"

    text = demo.read_text(encoding="utf-8")

    assert "# Cairn Memory Manual Demo" in text
    for command in (
        "cairn audit secrets",
        "cairn init",
        "cairn init --install-claude-hooks --yes",
        "cairn ingest",
        "cairn render --diff",
        "cairn render",
        "cairn inject claude --mode preview",
        "cairn inject claude --mode link",
        "cairn run show <run_id>",
        "cairn verify",
        "cairn outcome mark-from-verify <run_id> --task-type validation",
        "scripts/create_sandbox.ps1",
    ):
        assert command in text

    for phrase in (
        "Cold Run",
        "Warm Run",
        "G6 Robust Criterion",
        "Verify Bridge",
        "reason_code=start_failed",
        "SQLite read-only",
        "S12 Planted Secret Check",
        "raw planted secrets",
        "working-tree-only redaction fixtures",
        "Allowed before first correct test command",
        "Forbidden before first correct test command",
        "first matching test command equals injected command",
        "no forbidden rediscovery event occurred before it",
        "Final Definition Of Done",
        "Windows PowerShell",
    ):
        assert phrase in text

    for checklist_item in (
        "- [ ] G1",
        "- [ ] G2",
        "- [ ] G3",
        "- [ ] G4",
        "- [ ] G5",
        "- [ ] G6",
        "- [ ] G7",
        "- [ ] S12",
    ):
        assert checklist_item in text


def test_week2_sandbox_runbook_covers_required_scenarios() -> None:
    runbook = REPO_ROOT / "docs" / "week2-sandbox-runbook.md"

    text = runbook.read_text(encoding="utf-8")

    for command in (
        "pytest -q",
        "cairn audit secrets",
        "git rev-parse HEAD",
        "claude --version",
        "bash scripts/create_sandbox.sh /tmp/cairn-demo-sandbox",
        "cairn init --install-claude-hooks --yes",
        "cairn status",
        "command -v cairn",
        "where cairn",
        "cairn ingest",
        "cairn run show <run_id>",
    ):
        assert command in text

    for scenario in (
        "S1 Bash success",
        "S2 Bash failure",
        "S3 Edit / Write / Read",
        "S4 permission deny",
        "S5 PreToolUse deny if feasible",
        "S6 subagent if feasible",
        "S7 manual /compact",
        "S8 auto compact if feasible",
        "S9 resume",
        "S10 interrupt Bash",
        "S11 crash / missing SessionEnd",
        "S12 read .env",
    ):
        assert scenario in text

    for phrase in (
        "run it TWICE",
        "events_inserted=0",
        "hook events actually captured",
        "no leftover hook-*.jsonl",
        ".omni/spool/bad/ is empty",
        ".omni/spool/_errors.log is empty",
        "ingest-*.json appeared",
        "byte-identical across two renders",
        "CLAUDE_PROJECT_DIR",
        "not feasible",
        "only *.tmp orphan files are acceptable",
        "cairn ingest <session_id>",
        "withheld stub",
    ):
        assert phrase in text


def test_week2_spike_report_contains_required_pending_sections() -> None:
    report = REPO_ROOT / "docs" / "week2-spike-report.md"

    text = report.read_text(encoding="utf-8")

    for heading in (
        "## 1. Environment",
        "## 2. Hook capture matrix",
        "## 3. Transcript parser matrix",
        "## 4. Bash evidence",
        "## 5. File operation evidence",
        "## 6. Permission / denial behavior",
        "## 7. Subagent behavior",
        "## 8. Compact behavior",
        "## 9. Resume behavior",
        "## 10. Crash / missing SessionEnd behavior",
        "## 11. S12 planted secret result",
        "## 12. Hook latency",
        "## 13. Cold / warm demo",
        "## 14. Go / No-Go decision",
    ):
        assert heading in text

    for phrase in (
        "PENDING HUMAN EVIDENCE",
        "KEYS ONLY",
        "unknown line ratio",
        "tool_use",
        "raw FAKE_AWS value absent",
        "raw OMNI_FAKE_SECRET absent",
        "raw fake GitHub token absent",
        "withheld stub envelope present",
        "in-process capture p50 / p95 / sample count",
        "process-level latency",
        "G6 strict pass/fail",
        "G6 robust pass/fail",
    ):
        assert phrase in text


def test_week2_go_no_go_doc_defines_gates_and_dogfood_entry() -> None:
    doc = REPO_ROOT / "docs" / "week2-go-no-go.md"

    text = doc.read_text(encoding="utf-8")

    for gate in ("G1", "G2", "G3", "G4", "G5", "G6", "G7"):
        assert f"## {gate}:" in text

    for phrase in (
        "session_id / cwd / timestamp",
        "command + exit_code + stdout/stderr",
        "safely archived with redaction",
        "cairn audit secrets",
        "package manager and test/build commands",
        "first matching test command equals injected command",
        "no forbidden rediscovery event occurred before it",
        "in-process hook capture p95 < 250 ms",
        "process-level latency is sampled separately",
        "Dogfood Entry",
        "G1-G7 pass",
        "no PENDING HUMAN EVIDENCE cells in sections 2, 3, 11",
        "no raw secrets in .omni/**",
        "no uncontrolled modification outside the CLAUDE.md managed region",
    ):
        assert phrase in text


def test_experience_memory_v0_doc_covers_behavior_eval_v0() -> None:
    doc = REPO_ROOT / "docs" / "experience-memory-v0.md"

    text = doc.read_text(encoding="utf-8")

    for phrase in (
        "Behavior Eval v0",
        "cairn eval run <run_id>",
        "cairn eval dogfood --cold <run_id> --warm <run_id>",
        "read-only",
        "no DB writes",
        "no new tables",
        "failed_to_help",
        "unihack negative sample",
        "CLAUDE.md",
        "README.md",
        "package.json",
        "DEPLOY.md",
        "pnpm verification command",
        "heuristic",
        "not causal proof",
        "cold/warm comparison",
        "project-level facts",
        "Outcome Log v0",
        "cairn outcome mark <run_id>",
        "cairn outcome mark-from-verify <run_id>",
        "cairn outcome show <run_id>",
        "user-marked",
        "does not infer task",
        "Verify-to-Outcome helper v0",
        "Verify Hardening v0.3",
        "cairn verify --qualifier <qualifier>",
        "cairn outcome mark-from-verify <run_id> --qualifier <qualifier>",
        "reason_code",
        "selection_mode",
        "selection_reason",
        "Verify Polish v0.4",
        "start_failed",
        "does not store stdout or stderr excerpts",
        "anchor for future experience and failure memory",
        "Experience Candidate v0",
        "cairn experience extract <run_id>",
        "cairn experience ls",
        "cairn experience show <exp_cand_id>",
        "cairn experience approve <exp_cand_id>",
        "cairn experience reject <exp_cand_id>",
        "reviewable only",
        "Experience Notes + Renderer v0",
        "approved candidates into active experience",
        "active notes can affect future agent behavior",
        "Failure Memory v0 Pointer",
        "cairn failure extract",
        "cairn failure approve",
        "cairn failure pattern retire",
        "Known Failures Renderer v0",
        "renders only active failure patterns",
        "Pattern Lifecycle v0",
        "pending and rejected",
        "not Soul runtime",
        "review-gated",
        "bridge from eval/outcome evidence to future memory rendering",
    ):
        assert phrase in text


def test_experience_memory_v0_doc_covers_verify_v05_hardening() -> None:
    doc = REPO_ROOT / "docs" / "experience-memory-v0.md"

    text = doc.read_text(encoding="utf-8")

    for phrase in (
        "Verify v0.5 / Outcome-from-Verify Hardening",
        "stays SQLite read-only",
        "only write bridge",
        "requires an existing `run_id`",
        "raw stdout and stderr excerpts",
        "derives `tests_status` from the stable verify `reason_code`",
        "`reason_code=passed` → `tests_status=passed`",
        "`reason_code=start_failed`",
        "automatically infer task success",
        "idempotent",
        "preserving `created_at`",
    ):
        assert phrase in text


def test_verify_v05_closeout_records_audit_and_dogfood_bridge() -> None:
    doc = REPO_ROOT / "docs" / "v05-closeout-audit-2026-06-14.md"

    text = doc.read_text(encoding="utf-8")

    for phrase in (
        "Verify v0.5 Closeout Audit - 2026-06-14",
        "outcome-from-verify hardening",
        "`omni verify` remains SQLite read-only",
        "`omni outcome mark-from-verify` remains the explicit write bridge",
        "No new tables",
        "reason_code=passed",
        "tests_status=passed",
        "reason_code=start_failed",
        "tests_status=unknown",
        "Outcome `status` is not inferred from verify",
        "Stored verify evidence excludes stdout and stderr excerpts",
        "pytest -q: 457 passed, 3 skipped",
        "5bba6758-75e8-4643-bfae-8818bb84f982",
        "status: success",
        "evidence.verify.reason_code: passed",
        "does not include stdout or stderr excerpts",
        "READY_TO_CLOSE",
    ):
        assert phrase in text

    assert "C:\\Users" not in text
    assert "Jiarui" not in text


def test_failure_memory_v0_doc_covers_candidate_only_scope() -> None:
    doc = REPO_ROOT / "docs" / "failure-memory-v0.md"

    text = doc.read_text(encoding="utf-8")

    for phrase in (
        "Failure Memory v0",
        "Failure Candidate v0",
        "cairn failure extract <run_id>",
        "cairn failure ls",
        "cairn failure show <failure_cand_id>",
        "cairn failure approve <failure_cand_id>",
        "cairn failure reject <failure_cand_id>",
        "cairn failure pattern ls",
        "cairn failure pattern show <pattern_id>",
        "cairn failure pattern retire <pattern_id>",
        "Failure Pattern v0",
        "Pattern Lifecycle v0",
        "Known Failures Renderer v0",
        "human approval step",
        "human-provided",
        "does not use an LLM",
        "does not run verification",
        "does not infer task success",
        "does not read or",
        "pending or rejected",
        "excludes pattern ids",
        "raw stderr",
        "cairn render --diff",
        "Retiring an already-retired pattern is idempotent",
        "`lifecycle` summary",
        "`renders=true`",
        "`can_reactivate=false`",
        "`supersede_supported=false`",
        "v0 does not silently",
        "does not implement supersede",
        "does not use an LLM",
        "does not parse raw artifacts",
        "redacted event metadata",
        "PostToolUseFailure",
        "non-zero exit codes",
        "interrupted",
        "error_signature_hash",
        "Rejected candidates are not recreated",
        "Behavior Eval v0",
        "Outcome Log v0",
        "Experience Notes Renderer v0",
    ):
        assert phrase in text


def test_known_failure_ab_dogfood_template_covers_control_treatment_verdicts() -> None:
    doc = REPO_ROOT / "docs" / "dogfood-known-failure-ab-template.md"

    text = doc.read_text(encoding="utf-8")

    for phrase in (
        "# Known Failure A/B Dogfood Template",
        "## Context",
        "Cairn Memory commit:",
        "project:",
        "failure pattern id:",
        "old failed run id:",
        "known failure memory line:",
        "## Control / cold run",
        "memory disabled or Known Failure absent:",
        "did it use old failed command:",
        "failure extract created:",
        "audit result:",
        "## Treatment / warm run",
        "Known Failure present:",
        "did it avoid old failed command:",
        "## Verdict",
        "PASS",
        "PARTIAL",
        "FAIL",
        "INCONCLUSIVE",
        "cold/control reproduces or attempts the old failed path",
        "warm/treatment avoids the old failed path",
        "warm uses the safer command family",
        "audit secrets passes",
        "created=0 is necessary but not sufficient by itself",
        "Do not claim causal proof without controlled cold/warm evidence",
    ):
        assert phrase in text


def test_dogfood_acceptance_pack_covers_real_project_loop_and_record_template() -> None:
    pack = REPO_ROOT / "docs" / "dogfood-acceptance-pack-v0.md"
    template = REPO_ROOT / "docs" / "dogfood-acceptance-record-template.md"
    stage_record = REPO_ROOT / "docs" / "dogfood-stage-acceptance-2026-06-14.md"

    pack_text = pack.read_text(encoding="utf-8")
    template_text = template.read_text(encoding="utf-8")
    stage_text = stage_record.read_text(encoding="utf-8")

    for phrase in (
        "Dogfood Acceptance Pack v0",
        "rendered memory -> Claude Code warm run -> ingest -> eval -> verify -> outcome",
        "Single runs are not causal proof",
        "cairn audit secrets",
        "cairn render --diff",
        "cairn render",
        "cairn inject claude --mode preview",
        "cairn inject claude --mode link",
        "Please validate this project and tell me whether the current setup works",
        "cairn ingest",
        "cairn eval run <warm_run_id>",
        "cairn verify",
        "cairn outcome mark-from-verify <warm_run_id> --task-type validation",
        "cairn eval dogfood --cold <cold_run_id> --warm <warm_run_id>",
        "PASS",
        "PARTIAL",
        "FAIL",
        "INCONCLUSIVE",
        "Do not claim universal causal proof",
        "cairn failure extract <warm_run_id>",
        "cairn experience extract <warm_run_id>",
        "docs/dogfood-stage-acceptance-2026-06-14.md",
    ):
        assert phrase in pack_text

    for phrase in (
        "Dogfood Acceptance Record",
        "Cairn Memory commit:",
        "Target project commit:",
        "Cold or old negative run id:",
        "Warm run id:",
        "memory_effect:",
        "expected_verification_executed:",
        "first_expected_command:",
        "rediscovery_count:",
        "dogfood improvement:",
        "verify reason_code:",
        "outcome tests_status:",
        "Verdict: PASS | PARTIAL | FAIL | INCONCLUSIVE",
    ):
        assert phrase in template_text

    for phrase in (
        "Stage Dogfood Acceptance - 2026-06-14",
        "does not add a new Claude Code run",
        "<DOGFOOD_PROJECT>",
        "<PYTHON_SCRIPTS>\\omni.exe",
        "fcdefb4a-2d39-46ed-ab1e-a1cae466e861",
        "87722242-c373-4713-abe9-4288edc71982",
        "memory_effect: failed_to_help",
        "first_expected_command: pnpm run test",
        "rediscovery_count: 0",
        "improvement: true",
        "reason_code: passed",
        "tests_status: passed",
        "lifecycle.renders: true",
        "lifecycle.can_reactivate: false",
        "Verdict: PASS",
        "Fresh Follow-up Warm Run",
        "6ecbde84-e13f-4d75-97bd-3e3a7d4c2b3b",
        "4a0ab86d-d25c-4b61-9aac-a27fde35868f",
        "permission mode: bypassPermissions",
        "first_expected_command: pnpm run build",
        "observed commands: pnpm run build, pnpm run test, pnpm run lint",
        "warm_rediscovery_count: 0",
        "command_adopted: true",
        "omni verify: status=passed, reason_code=passed, command=pnpm run test",
        "Fresh follow-up verdict: PARTIAL",
        "test-first ordering is not stable",
        "Test-first Renderer Retune",
        "do not start with build or lint; first run `pnpm run test`",
        "post-test checks only",
        "After validation tests pass, use pnpm run build to build Node.",
        "7a4cfff4-ce0d-410b-997e-e0bd9485296a",
        "still chose",
        "Post-test Wording Fresh Warm Run",
        "2d6294a5d39a7ba86de6c1c622507904d3b2b67d",
        "5bba6758-75e8-4643-bfae-8818bb84f982",
        "Final fresh follow-up verdict: PASS",
        "observed commands: pnpm run test, pnpm run build, pnpm run lint",
        "failure extract: created=0",
        "experience extract: created=0",
        "not a universal proof",
    ):
        assert phrase in stage_text
    assert "C:\\Users" not in stage_text
    assert "Jiarui" not in stage_text


def test_acceptance_pack_v0_doc_covers_readonly_writer_and_semantics() -> None:
    doc = REPO_ROOT / "docs" / "acceptance-pack-v0.md"

    text = doc.read_text(encoding="utf-8")

    # Documented commands for an already-ingested run.
    for command in (
        "cairn audit secrets",
        "cairn status",
        "cairn eval run <run_id>",
        "cairn eval dogfood --cold <cold_run_id> --warm <warm_run_id>",
        "cairn verify",
        "cairn outcome mark-from-verify <run_id> --task-type validation",
        "cairn outcome show <run_id>",
        "cairn experience extract <run_id>",
        "cairn failure extract <run_id>",
    ):
        assert command in text

    for phrase in (
        # read-only vs writer classification
        "Read-only vs writer commands",
        "approved writer",
        "read-only for Cairn Memory state but executes",
        # dogfood comparison fields
        "cold_comparable",
        "command_adopted",
        "improvement",
        "memory_effect_summary",
        "stronger behavior metric",
        # verify/outcome bridge
        "verify->outcome write bridge",
        "`reason_code=passed` -> `tests_status=passed`",
        "`start_failed` and every selection/parse failure -> `tests_status=unknown`",
        # experience/failure extract explicit write status
        "approved writers",
        "must be run explicitly by a human",
        "reviewable candidate rows",
        # neutral memory_effect caveat
        "can remain `neutral`",
        # no causal overclaim
        "evidence packaging, not causal proof",
        # safety / redaction boundaries
        "no raw stdout/stderr or artifact payloads",
        # no new tables / features
        "No new tables, no new memory types",
    ):
        assert phrase in text

    # The runbook itself must not leak local paths or identities.
    assert "C:\\Users" not in text
    assert "Jiarui" not in text


def test_acceptance_pack_v0_closeout_records_scope_and_validation() -> None:
    doc = REPO_ROOT / "docs" / "acceptance-pack-v0-closeout-2026-06-15.md"

    text = doc.read_text(encoding="utf-8")

    for phrase in (
        "Acceptance Pack v0 Closeout",
        "Date: 2026-06-15 local",
        "Scope A (docs-only)",
        "adds no runtime code",
        "evidence packaging, not causal proof",
        "Read-only vs writer confirmation",
        "Approved writers, run explicitly by a human",
        "no automatic task success inference",
        "still 001-006",
        "No new memory types",
        "No Behavior Eval classification change",
        "pytest -q",
        "omni audit secrets",
        "git diff --check",
        "ready to close",
    ):
        assert phrase in text

    assert "C:\\Users" not in text
    assert "Jiarui" not in text


def test_phase_c_final_delivery_doc_records_multisample_opencode_proof() -> None:
    doc = REPO_ROOT / "docs" / "phase-c-final-delivery-2026-06-16.md"
    plan = REPO_ROOT / "docs" / "superpowers" / "plans" / "2026-06-16-phase-c-final-delivery.md"

    text = doc.read_text(encoding="utf-8")
    plan_text = plan.read_text(encoding="utf-8")

    for phrase in (
        "Cairn Memory Phase C Final Delivery Evidence",
        "Scope: approved Phase C only",
        "OpenCode multi-sample dogfood",
        "read-only consumer",
        "No MCP server",
        "No external write path",
        "redaction-before-write",
        "hook never writes DB",
        "read-only commands never migrate",
        "human-gated CLI writer",
        "cairn memory read",
        "cairn failure read",
        "cairn verify plan",
        "cairn task read",
        "cairn ingest --engine opencode --transcript",
        "runs.engine = \"opencode\"",
        "Resolved OpenCode version: `1.17.7`",
        "`phasec_opencode_test`",
        "`phasec_opencode_build`",
        "OpenCode follow-up dogfood: bugfix, refactor, and known-failure recovery",
        "qwen-apiyi/glm-5.1",
        "qwen-apiyi",
        "qwen-deepseek",
        "`opencode_dogfood_bugfix`",
        "`opencode_dogfood_refactor`",
        "`opencode_dogfood_known_failure_recovery`",
        "opencode_known_failure_seed",
        "failure_cand_aa0596e1256c434c835509be96249c12",
        "non-empty known failure",
        "OpenCode real-project controlled cold/warm dogfood",
        "`/Users/lijiarui/Downloads/qwen-code-cairn-real-dogfood`",
        "`9ec5bf2a2`",
        "`@qwen-code/acp-bridge`",
        "`opencode_real_cold_bugfix`",
        "`opencode_real_warm_bugfix`",
        "failure_cand_f7d56639ea3547c7b43b4c8f5e2c051d",
        "failure_pattern_23325bdf07d344368a3e66721d1ea3ac",
        "machine_read_adopted",
        "warm used machine-read surfaces and reduced rediscovery",
        "`improvement=true`",
        "Package-local verify planning",
        "\"subject\": \"packages/acp-bridge\"",
        "\"command\": \"npm run test --workspace=@qwen-code/acp-bridge\"",
        "139 passed",
        "OpenCode local repair",
        "`opencode db path` failed with `no such column: name`",
        "db-backup-20260616-220809",
        "opencode.json.backup-20260616-221858",
        "`global-config-smoke-ok`",
        "OpenCode second real-project controlled cold/warm dogfood",
        "`/Users/lijiarui/Downloads/Cairn-Memory-real-dogfood-2`",
        "`387ae64`",
        "`opencode_cairn_self_cold_bugfix`",
        "`opencode_cairn_self_warm_bugfix`",
        "failure_cand_42c8609aaab14219a63605671d2aeea3",
        "\"memory_effect\": \"helped\"",
        "two focused tests passed",
        "OpenCode additional real-project controlled cold/warm samples",
        "`cardgame3077`",
        "`lite-cv-ai`",
        "`cakephp-app`",
        "`opencode_cardgame_cold_bugfix`",
        "`opencode_cardgame_warm_bugfix`",
        "failure_pattern_6c65f86202554e3298c868b8348be4a1",
        "`opencode_lite_cv_cold_build`",
        "`opencode_lite_cv_warm_build`",
        "failure_pattern_d8998fe3f6554242b05137a07ba6265a",
        "`opencode_cakephp_cold_bugfix`",
        "`opencode_cakephp_warm_bugfix`",
        "failure_pattern_690718700e26464aafbdb5b31640e166",
        "TS2613",
        "OK (6 tests, 6 assertions)",
        "five real-project controlled cold/warm pairs",
        "MCP client acceptance harness",
        "scripts/mcp_client_acceptance.py",
        "calls every tool through `tools/call`",
        "\"memory_read\"",
        "\"failure_read\"",
        "\"verify_plan\"",
        "\"task_read\"",
        "\"ok\": true",
        "does not add any write-capable MCP tool",
        "SDK dependency",
        "events_inserted=21",
        "events_inserted=14",
        "events_inserted=17",
        "events_inserted=13",
        "pnpm run test:unit",
        "edit `math.js`",
        "edit `format.js`",
        "edit `pnpm-lock.yaml`",
        "Follow-up outcome summary",
        "Canonical observed writer path",
        "`python -m pytest tests/test_docs.py -q`: 14 passed",
        "`python -m pytest tests/test_cli_smoke.py tests/test_db.py tests/test_task.py -q`: 134 passed",
        "`pytest -q`: 638 passed",
        "`git diff --check`: pass",
        "`python -m omni.cli audit secrets`: ok=true",
        "`npx -y opencode-ai@latest --version`: 1.17.7",
        "evidence is stronger than the original single C-2 sample",
        "does not prove broad behavioral improvement",
        "Implemented and verified",
        "Remaining caveats after expanded dogfood",
        "Explicitly not implemented",
        "Next smallest high-value tasks",
    ):
        assert phrase in text

    for command in (
        "pytest -q",
        "git diff --check",
        "python -m omni.cli audit secrets",
        "python -m omni.cli memory read",
        "python -m omni.cli failure read",
        "python -m omni.cli verify plan",
        "python -m omni.cli task read",
    ):
        assert command in text

    assert "PENDING" not in text
    assert "C:\\Users" not in text
    assert "Jiarui" not in text
    assert "C:\\Users" not in plan_text
    assert "Jiarui" not in plan_text


def test_qwen_code_v0_adapter_doc_records_boundary_and_acceptance() -> None:
    doc = REPO_ROOT / "docs" / "qwen-code-v0-adapter-2026-06-17.md"

    text = doc.read_text(encoding="utf-8")

    for phrase in (
        "QwenCode v0 Adapter Evidence",
        "cairn inject qwen --mode preview|link",
        "project-local `QWEN.md` managed-region injection",
        "cairn ingest --engine qwen --transcript",
        "qwen --output-format stream-json",
        "message.content[].type == \"tool_use\"",
        "message.content[].type == \"tool_result\"",
        "no QwenCode hook installer",
        "no global `~/.qwen` edits",
        "no new migration",
        "no Codex or Cursor adapter",
        "visible version: `0.16.2`",
        "50 passed",
        "649 passed",
        "symlinked `QWEN.md` is rejected before write",
        "run show can display",
    ):
        assert phrase in text

    assert "PENDING" not in text
    assert "C:\\Users" not in text
    assert "Jiarui" not in text


def test_minimal_linux_ci_workflow_runs_pytest_on_311_and_312() -> None:
    workflow = REPO_ROOT / ".github" / "workflows" / "ci.yml"

    text = workflow.read_text(encoding="utf-8")

    for phrase in (
        "ubuntu-latest",
        "3.11",
        "3.12",
        'pip install -e ".[dev]"',
        "pytest -q",
    ):
        assert phrase in text
