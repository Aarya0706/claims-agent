#!/usr/bin/env python
"""python scripts/compare.py  -> runs/comparison.md (v1 vs v2 development, regressions, improvements)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from claims import report  # noqa: E402
from claims.data import load_gold  # noqa: E402

d = Path("runs")
v1, v2 = (json.loads((d / f"{v}_development.json").read_text(encoding="utf-8")) for v in ("v1", "v2"))
md = report.compare_md(v1, v2, load_gold())
(d / "comparison.md").write_text(md, encoding="utf-8")
print(md)
