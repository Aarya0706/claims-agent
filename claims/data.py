"""CSV loading. Proper csv parser, UTF-8, newline='' so embedded line breaks stay data.
ai_answer is never stripped, normalised or re-saved."""
from __future__ import annotations

import csv
import hashlib
import os
import subprocess
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
DATASET_VERSION = "long-brand-answers-50-v4"
FACT_VERSION = "speaker-catalogue-v4"
EVALUATOR_VERSION = "sentence-spans-and-labels-v4"
FILES = {"answers": "answers.csv", "facts": "brand_facts.csv", "gold": "development_gold.csv"}


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def typed_value(value: str, value_type: str):
    if value_type == "number":
        f = float(value)
        return int(f) if f.is_integer() else f
    if value_type == "boolean":
        v = value.strip().lower()
        if v == "true":
            return True
        if v == "false":
            return False
        raise ValueError(f"bad boolean {value!r}")
    if value_type == "string":
        return value
    raise ValueError(f"bad value_type {value_type!r}")


def blank_to_none(v):
    return None if v is None or v == "" else v


def load_answers(data_dir: Path | None = None) -> list[dict]:
    return read_csv((data_dir or DATA_DIR) / FILES["answers"])


def load_facts(data_dir: Path | None = None) -> list[dict]:
    out = []
    for r in read_csv((data_dir or DATA_DIR) / FILES["facts"]):
        out.append({
            "fact_id": r["fact_id"], "brand_id": r["brand_id"], "model_id": r["model_id"],
            "field": r["field"], "value": typed_value(r["value"], r["value_type"]),
            "value_type": r["value_type"], "unit": blank_to_none(r["unit"]),
            "condition": blank_to_none(r["condition"]),
            "valid_from": r["valid_from"], "valid_to": r["valid_to"],
        })
    return out


def load_gold(data_dir: Path | None = None) -> list[dict]:
    rows = read_csv((data_dir or DATA_DIR) / FILES["gold"])
    for r in rows:
        r["start_char"] = int(r["start_char"])
        r["end_char"] = int(r["end_char"])
    return rows


def file_hashes(data_dir: Path | None = None) -> dict:
    d = data_dir or DATA_DIR
    return {k: hashlib.sha256((d / v).read_bytes()).hexdigest() for k, v in FILES.items()}


def source_revision():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL, text=True).strip() or None
    except Exception:
        return None


class Catalogue:
    """The only factual authority; read-only get_brand_facts lookup."""

    def __init__(self, facts: list[dict]):
        self.by_brand: dict[str, list[dict]] = {}
        for f in facts:
            self.by_brand.setdefault(f["brand_id"], []).append(f)
        self.brands = set(self.by_brand)
        self.fact_ids = {f["fact_id"] for f in facts}

    def get_brand_facts(self, brand_id: str) -> dict:
        return {"fact_version": FACT_VERSION, "brand_id": brand_id, "facts": self.by_brand[brand_id]}


@lru_cache(maxsize=1)
def default_catalogue() -> Catalogue:
    return Catalogue(load_facts())
