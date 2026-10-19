#!/usr/bin/env python
"""Live run:  python scripts/run_eval.py --version v1 --split development
Writes runs/<version>_<split>.json + .md.  --limit N is a smoke test only (never a deliverable)."""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv  # noqa: E402
load_dotenv()
from claims import report, runner  # noqa: E402
from claims.agent import DEFAULT_TIMEOUT_S  # noqa: E402
from claims.provider import make_provider  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("--version", required=True, choices=["v1", "v2"])
p.add_argument("--split", required=True, choices=["development", "check"])
p.add_argument("--provider", choices=["gemini", "anthropic"]); p.add_argument("--model")
p.add_argument("--min-interval", type=float, default=6.5, help="seconds between Gemini requests (free-tier RPM)")
p.add_argument("--temperature", type=float)
p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
p.add_argument("--limit", type=int); p.add_argument("--db", action="store_true", help="also persist to PostgreSQL")
p.add_argument("--out", default="runs")
p.add_argument("--resume", action="store_true", help="continue from runs/<name>.partial.json (after a quota stop / crash)")
a = p.parse_args()

kw = {"min_interval": a.min_interval, "temperature": a.temperature} if (a.provider or __import__("os").getenv("CLAIMS_PROVIDER", "gemini")) == "gemini" else {}
prov = make_provider(a.provider, a.model, **kw)
prog = lambda i, n, r: print(f"[{i}/{n}] {r['answer_id']} {r['status']} claims={len(r['claims'])} {r['latency_ms']}ms "
                             f"{(r['error'] or {}).get('type', '')}", flush=True)
out = Path(a.out); out.mkdir(exist_ok=True)
stem = f"{a.version}_{a.split}" + (f"_limit{a.limit}" if a.limit else "")
partial = out / f"{stem}.partial.json"


def save(path, run):  # atomic write: a crash never leaves a half-written file
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


resume = json.loads(partial.read_text(encoding="utf-8")) if a.resume and partial.exists() else None
if a.resume and resume is None:
    print("no partial file found; starting fresh")
run = runner.run_split(a.version, a.split, prov, timeout=a.timeout, limit=a.limit, progress=prog,
                       checkpoint=lambda r: save(partial, r), resume=resume)
if run["status"] != "completed":
    print(f"\n*** RUN STOPPED: {run['error']}\n*** Progress saved: {partial}\n*** Continue with the SAME command plus --resume")
    sys.exit(2)
save(out / f"{stem}.json", run)
partial.unlink(missing_ok=True)
md = report.run_summary_md(run)
if run["metrics"]:
    from claims.data import load_gold
    md += "\n" + report.error_buckets(run, load_gold())
(out / f"{stem}.md").write_text(md, encoding="utf-8")
print(md)
if a.db:
    from claims import db
    with db.connect() as conn:
        db.init_schema(conn); db.save_run(conn, run)
    print("saved to PostgreSQL:", run["run_id"])