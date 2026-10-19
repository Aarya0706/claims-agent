"""Deterministic harness scorer. Exact (answer_id, start, end) match only; no fuzzy matching, no LLM judge.
Gold is used ONLY here, after predictions are saved."""
from __future__ import annotations


class ScoringError(ValueError):
    pass


def _prf(m: int, p: int, g: int) -> dict:
    return {"precision": m / p if p else 0.0, "recall": m / g if g else 0.0,
            "f1": 2 * m / (p + g) if (p + g) else 0.0}


def null_metrics() -> None:
    return None


def score(scheduled_ids: list[str], outcomes: list[dict], gold_rows: list[dict]) -> tuple[dict | None, dict]:
    """outcomes: [{answer_id,status,claims:[{claim_id,start_char,end_char,quote,label}]}].
    Returns (metrics, annotations) where annotations[(aid,s,e)] = (gold_claim_id, expected_label, correct)."""
    ids = [o["answer_id"] for o in outcomes]
    if len(ids) != len(set(ids)):
        raise ScoringError("duplicated answer outcome")
    if set(ids) != set(scheduled_ids) or len(ids) != len(scheduled_ids):
        raise ScoringError("missing or unscheduled answer outcome")
    gold = {(g["answer_id"], g["start_char"], g["end_char"]): g for g in gold_rows if g["answer_id"] in set(scheduled_ids)}
    G = len(gold)
    if not scheduled_ids or G == 0:
        return None, {}
    P = M = C = 0
    matched, correct, wrong, unmatched, errors = set(), set(), [], [], []
    ann: dict = {}
    for o in outcomes:
        if o["status"] == "error":
            errors.append(o["answer_id"])
            continue  # accepted predictions: none
        for c in o["claims"]:
            P += 1
            key = (o["answer_id"], c["start_char"], c["end_char"])
            g = gold.get(key)
            if g is None or key in matched or c["quote"] != g["quote"]:
                unmatched.append(c["claim_id"])
                continue
            matched.add(key)
            M += 1
            ok = c["label"] == g["expected_label"]
            ann[key] = (g["claim_id"], g["expected_label"], ok)
            if ok:
                C += 1
                correct.add(g["claim_id"])
            else:
                wrong.append(g["claim_id"])
    gid = lambda k: gold[k]["claim_id"]
    matched_ids = sorted(gid(k) for k in matched)
    return {
        "G": G, "P": P, "M": M, "C": C,
        "extraction": _prf(M, P, G), "joint": _prf(C, P, G),
        "gold_claim_coverage": C / G,
        "missed_gold_ids": sorted(g["claim_id"] for k, g in gold.items() if k not in matched),
        "unmatched_prediction_ids": sorted(unmatched),
        "wrong_label_ids": sorted(wrong),
        "matched_gold_ids": matched_ids, "correct_gold_ids": sorted(correct),
        "answer_error_count": len(errors), "error_answer_ids": sorted(errors),
    }, ann
