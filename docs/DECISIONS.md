# Decisions

## `.omni/` is local-only

Decision: the entire `.omni/` directory is local-only, ignored by git, and
should not be committed. There are no exceptions for `.omni/project_id`.

Rationale: OmniMemory uses this file as the durable local project identity after
`omni init`. On first creation, `omni init` bootstraps the value from the git
remote origin hash when a `git remote origin` URL is available; otherwise it
creates a random `proj_` id. After the file exists, the file wins over git
remote origin so moving the repo path or changing the remote later does not
silently change `project_id`.

## Week-1 spool and status limits

Decision: Week-1 writes one ingest request file per hook stop event instead of
appending to a shared queue file. This avoids concurrent append corruption while
keeping hook capture stdlib-only and redaction-before-write.

Rationale: the hook must remain an observer and exit 0. Per-request files are
good enough for Week-1, but a later version should make drain processing more
durable if crash recovery during ingest becomes a requirement.

Decision: `omni status` computes hook latency p50/p95 by scanning hook spool
files in Week-1.

Rationale: this is acceptable for short sandbox runs. Future versions should
summarize on ingest or archive processed spool files so status does not scan an
ever-growing spool tree.
