"""Local reports: run summary, error buckets by difficulty tag, v1-vs-v2 comparison. Harness-side only."""
from __future__ import annotations

from collections import Counter, defaultdict


def _f(x):
    return "n/a" if x is None else f"{x:.3f}"


def run_summary_md(run: dict) -> str:
    m, c = run.get("metrics"), run["counts"]
    L = [f"# {run['agent_version']} / {run['split']}  (run {run['run_id']})",
         f"- status: **{run['status']}**  provider: {run['provider']} / {run['model']}  duration: {run.get('duration_s')}s",
         f"- prompt: {run['prompt_version']}  dataset: {run['dataset_version']}  facts: {run['fact_version']}  "
         f"evaluator: {run['evaluator_version']}  revision: {run.get('source_revision')}",
         f"- settings: `{run['settings']}`",
         f"- answers: scheduled {c['scheduled']}, ok {c['ok']}, errors {c['errors']}, empty {c['empty']}; accepted predictions {c['claims']}"]
    if m:
        L += [f"- G={m['G']} P={m['P']} M={m['M']} C={m['C']}",
              f"- **Joint F1 {_f(m['joint']['f1'])}** (P {_f(m['joint']['precision'])}, R {_f(m['joint']['recall'])})",
              f"- Extraction F1 {_f(m['extraction']['f1'])} (P {_f(m['extraction']['precision'])}, R {_f(m['extraction']['recall'])})",
              f"- gold coverage C/G {_f(m['gold_claim_coverage'])}; missed {len(m['missed_gold_ids'])}; "
              f"unmatched predictions {len(m['unmatched_prediction_ids'])}; matched wrong-label {len(m['wrong_label_ids'])}; "
              f"answer errors {m['answer_error_count']} {m['error_answer_ids']}"]
    else:
        L.append("- quality metrics: null (check split has no labels here)")
    errs = [(r["answer_id"], r["error"]) for r in run["answers"] if r["status"] == "error"]
    for aid, e in errs:
        L.append(f"  - {aid}: {e['type']}: {e['message']}")
    return "\n".join(L) + "\n"


def error_buckets(run: dict, gold_rows: list[dict]) -> str:
    """Where does v1 fail? Group missed / wrong-label gold claims by difficulty tag and (expected->predicted) label."""
    m = run["metrics"]
    g = {r["claim_id"]: r for r in gold_rows}
    pred = {c["matched_gold_claim_id"]: c for r in run["answers"] for c in r["claims"] if c["matched_gold_claim_id"]}
    tags_missed, tags_wrong, confusion = Counter(), Counter(), Counter()
    for cid in m["missed_gold_ids"]:
        tags_missed.update(g[cid]["difficulty_tags"].split("|"))
    for cid in m["wrong_label_ids"]:
        tags_wrong.update(g[cid]["difficulty_tags"].split("|"))
        confusion[(g[cid]["expected_label"], pred[cid]["label"])] += 1
    L = ["## Error buckets", "", "Missed gold claims by tag: " + ", ".join(f"{t}={n}" for t, n in tags_missed.most_common()),
         "", "Wrong-label (matched) by tag: " + ", ".join(f"{t}={n}" for t, n in tags_wrong.most_common()),
         "", "Label confusion (expected -> predicted): " + ", ".join(f"{a}->{b}={n}" for (a, b), n in confusion.most_common()),
         "", "Unmatched predictions (extras / bad boundaries): " + ", ".join(m["unmatched_prediction_ids"][:40])]
    return "\n".join(L) + "\n"


def compare_md(v1: dict, v2: dict, gold_rows: list[dict]) -> str:
    a, b = v1["metrics"], v2["metrics"]
    rows = [("Joint F1", a["joint"]["f1"], b["joint"]["f1"]), ("Joint precision", a["joint"]["precision"], b["joint"]["precision"]),
            ("Joint recall", a["joint"]["recall"], b["joint"]["recall"]), ("Extraction F1", a["extraction"]["f1"], b["extraction"]["f1"]),
            ("Gold coverage C/G", a["gold_claim_coverage"], b["gold_claim_coverage"])]
    L = ["# v1 vs v2 (development, identical inputs & scoring)", "", "| metric | v1 | v2 | delta |", "|---|---|---|---|"]
    L += [f"| {n} | {x:.3f} | {y:.3f} | {y - x:+.3f} |" for n, x, y in rows]
    L += ["", f"| count | v1 | v2 |", "|---|---|---|"]
    for k in ("G", "P", "M", "C", "answer_error_count"):
        L.append(f"| {k} | {a[k]} | {b[k]} |")
    c1, c2 = set(a["correct_gold_ids"]), set(b["correct_gold_ids"])
    g = {r["claim_id"]: r for r in gold_rows}
    fmt = lambda ids: "\n".join(f"- {i} [{g[i]['difficulty_tags']}] {g[i]['quote'][:110]}" for i in sorted(ids)) or "- none"
    L += ["", f"## Regressions (correct in v1, not in v2): {len(c1 - c2)}", fmt(c1 - c2),
          "", f"## Improvements (correct in v2, not in v1): {len(c2 - c1)}", fmt(c2 - c1)]
    e1, e2 = set(a["unmatched_prediction_ids"]), set(b["unmatched_prediction_ids"])
    L += ["", f"## Extra/unmatched predictions: v1 {len(e1)}, v2 {len(e2)}; only in v2: {len(e2 - e1)}"]
    return "\n".join(L) + "\n"
