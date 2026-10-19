import csv
from claims import data


def test_counts_and_split():
    A, F, G = data.load_answers(), data.load_facts(), data.load_gold()
    assert (len(A), len(F), len(G)) == (50, 132, 376)
    assert sum(a["split"] == "development" for a in A) == 40 and sum(a["split"] == "check" for a in A) == 10


def test_ai_answer_preserved_exactly_incl_newlines():
    raw = list(csv.DictReader(open(data.DATA_DIR / "answers.csv", encoding="utf-8", newline="")))
    A = data.load_answers()
    assert [a["ai_answer"] for a in A] == [r["ai_answer"] for r in raw]
    assert sum("\n" in a["ai_answer"] for a in A) > 0          # embedded line breaks are data
    assert len({a["answer_id"] for a in A}) == 50              # not split by line


def test_gold_quotes_equal_answer_slices():
    A = {a["answer_id"]: a["ai_answer"] for a in data.load_answers()}
    for g in data.load_gold():
        assert A[g["answer_id"]][g["start_char"]:g["end_char"]] == g["quote"]


def test_typed_values_and_blanks():
    assert data.typed_value("false", "boolean") is False and data.typed_value("true", "boolean") is True
    assert data.typed_value("1299", "number") == 1299 and data.typed_value("7.5", "number") == 7.5
    F = data.load_facts()
    assert all(isinstance(f["value"], bool) for f in F if f["value_type"] == "boolean")
    assert any(f["unit"] is None for f in F) and any(f["condition"] is None for f in F)
    try:
        data.typed_value("maybe", "boolean")
        assert False
    except ValueError:
        pass


def test_hashes_present():
    assert set(data.file_hashes()) == {"answers", "facts", "gold"}
