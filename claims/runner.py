"""Sequential runner: builds a run record (JSON-serialisable dict). Gold joins only AFTER predictions exist."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from . import data
from .agent import DEFAULT_TIMEOUT_S, MAX_TURNS, prompt_version, run_agent_detailed
from .data import Catalogue, default_catalogue
from .errors import AgentError, InfrastructureError
from .models import AgentInput
from .provider import Provider
from .scorer import score

INPUT_FIELDS = ("answer_id", "brand_id", "question", "ai_answer")  # nothing else ever reaches the agent


def scheduled_answers(split: str, answers: list[dict]) -> list[dict]:
    if split not in ("development", "check"):
        raise ValueError("split must be development or check")
    return [a for a in answers if a["split"] == split]


RETRYABLE = {"provider_error", "provider_timeout"}   # transient: re-run on resume. Other errors are kept as results.
MAX_CONSECUTIVE_PROVIDER_FAILURES = 5                # stop early instead of burning quota on a dead provider


def run_split(version: str, split: str, provider: Provider, *, answers: list[dict] | None = None,
              catalogue: Catalogue | None = None, gold: list[dict] | None = None,
              timeout: float = DEFAULT_TIMEOUT_S, limit: int | None = None, progress=None,
              checkpoint=None, resume: dict | None = None) -> dict:
    answers = answers if answers is not None else data.load_answers()
    cat = catalogue or default_catalogue()
    sched = scheduled_answers(split, answers)
    if limit:
        sched = sched[:limit]
    fresh = {
        "run_id": str(uuid.uuid4()), "status": "running", "split": split, "agent_version": version,
        "prompt_version": prompt_version(version), "dataset_version": data.DATASET_VERSION,
        "evaluator_version": data.EVALUATOR_VERSION, "fact_version": data.FACT_VERSION,
        "provider": provider.name, "model": provider.model,
        "settings": {**provider.settings, "provider_timeout_s": timeout, "max_turns": MAX_TURNS, "limit": limit},
        "created_at": datetime.now(timezone.utc).isoformat(), "source_revision": data.source_revision(),
        "file_hashes": data.file_hashes(), "answers": [], "counts": {}, "metrics": None, "error": None,
    }
    prior_s, redo = 0.0, set()
    if resume is None:
        run = fresh
    else:  # continue an interrupted run: only same version/split/model/data/settings may be resumed
        same = (resume["agent_version"] == version and resume["split"] == split and resume["model"] == provider.model
                and resume["provider"] == provider.name and resume["file_hashes"] == fresh["file_hashes"]
                and resume["prompt_version"] == fresh["prompt_version"] and resume["settings"].get("limit") == limit)
        if not same:
            raise InfrastructureError("resume file does not match this version/split/model/data; start a fresh run")
        run, prior_s = resume, float(resume.get("duration_s") or 0)
        run["status"], run["error"] = "running", None
        redo = {r_["answer_id"] for r_ in run["answers"] if r_["status"] == "error" and r_["error"]["type"] in RETRYABLE}
        run.setdefault("resumes", []).append({"at": fresh["created_at"], "retried_provider_errors": sorted(redo)})
    kept = {r_["answer_id"]: r_ for r_ in run["answers"] if r_["answer_id"] not in redo}
    run["answers"] = [kept[a["answer_id"]] for a in sched if a["answer_id"] in kept]
    t_run, streak = time.perf_counter(), 0
    try:
        for i, a in enumerate(sched, 1):
            if a["answer_id"] in kept:
                continue
            inp = AgentInput(**{k: a[k] for k in INPUT_FIELDS})
            t0 = time.perf_counter()
            rec = {"answer_id": a["answer_id"], "status": "ok", "error": None, "trace_ref": None, "claims": []}
            try:
                res = run_agent_detailed(inp, provider, version, catalogue=cat, timeout=timeout)
                rec["claims"] = [c.model_dump() for c in res.output.claims]
                rec["turns"], rec["repairs"] = res.turns, res.repairs
            except AgentError as e:  # preserved, never replaced with 'unknown'
                rec["status"], rec["error"] = "error", {"type": e.type, "message": e.message}
            rec["latency_ms"] = int((time.perf_counter() - t0) * 1000)
            run["answers"].append(rec)
            kept[a["answer_id"]] = rec
            if progress:
                progress(i, len(sched), rec)
            if checkpoint:
                run["answers"].sort(key=lambda x: x["answer_id"])
                checkpoint(run)                       # progress survives crashes, quota stops and Ctrl+C
            streak = streak + 1 if (rec["error"] or {}).get("type") in RETRYABLE else 0
            if streak >= MAX_CONSECUTIVE_PROVIDER_FAILURES:
                raise InfrastructureError(f"{streak} consecutive provider failures (quota/outage?); stopped to save quota. "
                                          "Fix the cause and re-run with --resume")
        run["status"] = "completed"
    except (InfrastructureError, KeyboardInterrupt, Exception) as e:  # interrupted/infra failure: keep partial evidence
        run["status"], run["error"] = "failed", f"{type(e).__name__}: {str(e)[:200]}"
    run["answers"].sort(key=lambda x: x["answer_id"])
    run["duration_s"] = round(prior_s + time.perf_counter() - t_run, 2)
    run["finished_at"] = datetime.now(timezone.utc).isoformat()
    for rec in run["answers"]:
        for c in rec["claims"]:
            c.update(matched_gold_claim_id=None, expected_label=None, correct=None)
    run["counts"] = {
        "scheduled": len(sched), "processed": len(run["answers"]),
        "ok": sum(r["status"] == "ok" for r in run["answers"]),
        "errors": sum(r["status"] == "error" for r in run["answers"]),
        "empty": sum(r["status"] == "ok" and not r["claims"] for r in run["answers"]),
        "claims": sum(len(r["claims"]) for r in run["answers"]),
    }
    if split == "development" and run["status"] == "completed" and not limit:
        gold_rows = gold if gold is not None else data.load_gold()
        metrics, ann = score([a["answer_id"] for a in sched], run["answers"], gold_rows)
        run["metrics"] = metrics
        for rec in run["answers"]:
            for c in rec["claims"]:
                hit = ann.get((rec["answer_id"], c["start_char"], c["end_char"]))
                if hit:
                    c["matched_gold_claim_id"], c["expected_label"], c["correct"] = hit
    if checkpoint:
        checkpoint(run)
    return run  # check split: metrics stay None, no gold is ever read