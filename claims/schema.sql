CREATE TABLE IF NOT EXISTS runs (
    run_id            uuid PRIMARY KEY,
    split             text NOT NULL CHECK (split IN ('development','check')),
    agent_version     text NOT NULL CHECK (agent_version IN ('v1','v2')),
    prompt_version    text NOT NULL,
    dataset_version   text NOT NULL,
    evaluator_version text NOT NULL,
    fact_version      text NOT NULL,
    provider          text NOT NULL,
    model             text NOT NULL,
    settings          jsonb NOT NULL,
    created_at        timestamptz NOT NULL,
    finished_at       timestamptz,
    source_revision   text,
    file_hashes       jsonb NOT NULL,
    status            text NOT NULL CHECK (status IN ('running','completed','failed')),
    counts            jsonb NOT NULL,
    metrics           jsonb,            -- NULL for check runs
    error             text
);
CREATE TABLE IF NOT EXISTS answer_results (
    id            bigserial PRIMARY KEY,
    run_id        uuid NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    answer_id     text NOT NULL,
    status        text NOT NULL CHECK (status IN ('ok','error')),
    error_type    text,
    error_message text,
    latency_ms    integer,
    trace_ref     text,
    claim_count   integer NOT NULL DEFAULT 0,
    UNIQUE (run_id, answer_id)
);
CREATE TABLE IF NOT EXISTS claim_results (
    id                    bigserial PRIMARY KEY,
    run_id                uuid NOT NULL,
    answer_id             text NOT NULL,
    claim_id              text NOT NULL,
    start_char            integer NOT NULL,
    end_char              integer NOT NULL,
    quote                 text NOT NULL,
    label                 text NOT NULL CHECK (label IN ('supported','contradicted','unknown')),
    fact_ids              text[] NOT NULL DEFAULT '{}',
    reason                text NOT NULL,
    matched_gold_claim_id text,         -- development only
    expected_label        text,         -- development only
    correct               boolean,      -- development only
    UNIQUE (run_id, answer_id, start_char, end_char),
    FOREIGN KEY (run_id, answer_id) REFERENCES answer_results (run_id, answer_id) ON DELETE CASCADE
);
