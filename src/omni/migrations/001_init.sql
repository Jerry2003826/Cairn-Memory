-- migrations/001_init.sql
-- PRAGMAs are set in db.connect(), not here:
-- PRAGMA journal_mode=WAL;
-- PRAGMA busy_timeout=5000;
-- PRAGMA foreign_keys=ON;

CREATE TABLE meta(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

INSERT INTO meta(key, value) VALUES
  ('schema_version', '1'),
  ('commit_seq', '0'),
  ('redaction_ver', '1');

CREATE TABLE runs(
  run_id TEXT PRIMARY KEY,
  parent_run_id TEXT,
  project_id TEXT NOT NULL,
  engine TEXT NOT NULL DEFAULT 'claude_code',
  engine_version TEXT,
  model_version TEXT,
  cwd TEXT,
  git_branch TEXT,
  transcript_path TEXT,
  snapshot_seq INTEGER NOT NULL,
  started_at TEXT,
  ended_at TEXT,
  end_reason TEXT,
  status TEXT NOT NULL DEFAULT 'open'
);

CREATE TABLE events(
  event_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id),
  seq INTEGER NOT NULL,
  hook_seq INTEGER,
  ts TEXT NOT NULL,
  event_type TEXT NOT NULL,
  tool TEXT,
  tool_use_id TEXT,
  input_ref TEXT,
  output_ref TEXT,
  exit_code INTEGER,
  duration_ms INTEGER,
  redaction_status TEXT NOT NULL DEFAULT 'clean',
  redaction_ver INTEGER NOT NULL,
  source TEXT NOT NULL,
  meta JSON,
  UNIQUE(run_id, seq)
);

CREATE INDEX idx_events_tooluse ON events(tool_use_id);
CREATE INDEX idx_events_run ON events(run_id, event_type);

CREATE TABLE artifacts(
  hash TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  byte_len INTEGER,
  line_count INTEGER,
  redaction_status TEXT NOT NULL,
  redaction_ver INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE facts(
  fact_id TEXT PRIMARY KEY,
  scope TEXT NOT NULL,
  subject TEXT NOT NULL,
  predicate TEXT NOT NULL,
  qualifier TEXT NOT NULL DEFAULT 'default',
  object_norm TEXT NOT NULL,
  value_type TEXT NOT NULL,
  claim TEXT NOT NULL,
  trust INTEGER NOT NULL,
  confidence REAL,
  sensitivity TEXT NOT NULL DEFAULT 'low',
  origin TEXT NOT NULL,
  pinned INTEGER NOT NULL DEFAULT 0,
  created_seq INTEGER NOT NULL,
  retired_seq INTEGER,
  superseded_by TEXT,
  last_confirmed_at TEXT,
  created_at TEXT NOT NULL,
  evidence JSON NOT NULL
);

CREATE INDEX idx_facts_key ON facts(scope, subject, predicate, qualifier);

CREATE UNIQUE INDEX uq_fact_active
ON facts(scope, subject, predicate, qualifier, object_norm)
WHERE retired_seq IS NULL;

CREATE TABLE fact_candidates(
  cand_id TEXT PRIMARY KEY,
  run_id TEXT,
  scope TEXT NOT NULL,
  subject TEXT NOT NULL,
  predicate TEXT NOT NULL,
  qualifier TEXT NOT NULL DEFAULT 'default',
  object_norm TEXT NOT NULL,
  value_type TEXT NOT NULL,
  claim TEXT NOT NULL,
  trust INTEGER NOT NULL,
  evidence JSON NOT NULL,
  extractor_version TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending',
  conflict_with TEXT,
  created_at TEXT NOT NULL,
  reviewed_at TEXT,
  review_note TEXT
);

CREATE TABLE suppressions(
  scope TEXT,
  subject TEXT,
  predicate TEXT,
  qualifier TEXT,
  object_norm TEXT,
  created_at TEXT NOT NULL,
  PRIMARY KEY(scope, subject, predicate, qualifier, object_norm)
);

CREATE TABLE blocks(
  block_id TEXT PRIMARY KEY,
  scope TEXT NOT NULL,
  render_ver INTEGER NOT NULL,
  content_hash TEXT,
  body TEXT,
  dirty INTEGER NOT NULL DEFAULT 1,
  updated_at TEXT
);

CREATE TABLE block_deps(
  block_id TEXT NOT NULL,
  dep_kind TEXT NOT NULL,
  dep_id TEXT NOT NULL,
  dep_line_hash TEXT NOT NULL,
  PRIMARY KEY(block_id, dep_kind, dep_id)
);

CREATE INDEX idx_deps_rev ON block_deps(dep_kind, dep_id);
