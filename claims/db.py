"""PostgreSQL persistence (psycopg3, parameterised SQL only)."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from .errors import InfrastructureError

SCHEMA = (Path(__file__).parent / "schema.sql").read_text()


def connect(url: str | None = None) -> psycopg.Connection:
    url = url or os.getenv("DATABASE_URL")
    if not url:
        raise InfrastructureError("DATABASE_URL is not set")
    try:
        return psycopg.connect(url, autocommit=False)
    except psycopg.Error as e:
        raise InfrastructureError("database connection failed") from e


def init_schema(conn) -> None:
    with conn.transaction():
        conn.execute(SCHEMA)


def save_run(conn, run: dict) -> None:
    with conn.transaction():
        conn.execute(
            """INSERT INTO runs (run_id, split, agent_version, prompt_version, dataset_version, evaluator_version,
               fact_version, provider, model, settings, created_at, finished_at, source_revision, file_hashes,
               status, counts, metrics, error)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (run["run_id"], run["split"], run["agent_version"], run["prompt_version"], run["dataset_version"],
             run["evaluator_version"], run["fact_version"], run["provider"], run["model"], Jsonb(run["settings"]),
             datetime.fromisoformat(run["created_at"]),
             datetime.fromisoformat(run["finished_at"]) if run.get("finished_at") else None,
             run["source_revision"], Jsonb(run["file_hashes"]), run["status"], Jsonb(run["counts"]),
             Jsonb(run["metrics"]) if run["metrics"] is not None else None, run["error"]))
        for a in run["answers"]:
            e = a["error"] or {}
            conn.execute(
                """INSERT INTO answer_results (run_id, answer_id, status, error_type, error_message, latency_ms,
                   trace_ref, claim_count) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (run["run_id"], a["answer_id"], a["status"], e.get("type"), e.get("message"),
                 a.get("latency_ms"), a.get("trace_ref"), len(a["claims"])))
            for c in a["claims"]:
                conn.execute(
                    """INSERT INTO claim_results (run_id, answer_id, claim_id, start_char, end_char, quote, label,
                       fact_ids, reason, matched_gold_claim_id, expected_label, correct)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (run["run_id"], a["answer_id"], c["claim_id"], c["start_char"], c["end_char"], c["quote"],
                     c["label"], c["fact_ids"], c["reason"], c.get("matched_gold_claim_id"),
                     c.get("expected_label"), c.get("correct")))


def load_run(conn, run_id: str) -> dict | None:
    r = conn.execute(
        """SELECT run_id::text, split, agent_version, prompt_version, dataset_version, evaluator_version, fact_version,
           provider, model, settings, created_at, finished_at, source_revision, file_hashes, status, counts, metrics, error
           FROM runs WHERE run_id = %s""", (run_id,)).fetchone()
    if r is None:
        return None
    keys = ["run_id", "split", "agent_version", "prompt_version", "dataset_version", "evaluator_version",
            "fact_version", "provider", "model", "settings", "created_at", "finished_at", "source_revision",
            "file_hashes", "status", "counts", "metrics", "error"]
    run = dict(zip(keys, r))
    run["created_at"] = run["created_at"].isoformat()
    run["finished_at"] = run["finished_at"].isoformat() if run["finished_at"] else None
    rows = conn.execute(
        """SELECT a.answer_id, a.status, a.error_type, a.error_message, a.latency_ms, a.trace_ref,
                  c.claim_id, c.start_char, c.end_char, c.quote, c.label, c.fact_ids, c.reason,
                  c.matched_gold_claim_id, c.expected_label, c.correct
           FROM answer_results a
           LEFT JOIN claim_results c ON c.run_id = a.run_id AND c.answer_id = a.answer_id
           WHERE a.run_id = %s ORDER BY a.answer_id, c.start_char""", (run_id,)).fetchall()
    answers: dict[str, dict] = {}
    for (aid, st, et, em, lat, tr, cid, s, e, q, lab, fids, reason, mg, ex, cor) in rows:
        a = answers.setdefault(aid, {"answer_id": aid, "status": st, "latency_ms": lat, "trace_ref": tr,
                                     "error": {"type": et, "message": em} if st == "error" else None, "claims": []})
        if cid is not None:
            a["claims"].append({"claim_id": cid, "start_char": s, "end_char": e, "quote": q, "label": lab,
                                "fact_ids": list(fids), "reason": reason, "matched_gold_claim_id": mg,
                                "expected_label": ex, "correct": cor})
    run["answers"] = list(answers.values())
    return run
