import pytest
from claims.scorer import score, ScoringError


def gold(aid, spans):  # spans: [(s,e,label)]
    return [{"answer_id": aid, "claim_id": f"{aid}:{s}:{e}", "start_char": s, "end_char": e,
             "quote": f"q{s}", "expected_label": l} for s, e, l in spans]


def pred(aid, s, e, l):
    return {"claim_id": f"{aid}:{s}:{e}", "start_char": s, "end_char": e, "quote": f"q{s}", "label": l}


def out(aid, claims, status="ok"):
    return {"answer_id": aid, "status": status, "claims": claims}


G = gold("A", [(0, 10, "supported"), (11, 20, "unknown"), (21, 30, "contradicted")])


def test_perfect():
    m, _ = score(["A"], [out("A", [pred("A", 0, 10, "supported"), pred("A", 11, 20, "unknown"), pred("A", 21, 30, "contradicted")])], G)
    assert (m["G"], m["P"], m["M"], m["C"]) == (3, 3, 3, 3) and m["joint"]["f1"] == 1.0 and m["extraction"]["f1"] == 1.0


def test_missed_claim_hurts_recall():
    m, _ = score(["A"], [out("A", [pred("A", 0, 10, "supported")])], G)
    assert m["extraction"]["recall"] == pytest.approx(1 / 3) and m["extraction"]["precision"] == 1.0
    assert m["missed_gold_ids"] == ["A:11:20", "A:21:30"]


def test_extra_advice_hurts_precision():
    m, _ = score(["A"], [out("A", [pred("A", 0, 10, "supported"), pred("A", 11, 20, "unknown"),
                                   pred("A", 21, 30, "contradicted"), pred("A", 31, 40, "unknown")])], G)
    assert m["P"] == 4 and m["extraction"]["precision"] == 0.75 and m["unmatched_prediction_ids"] == ["A:31:40"]


def test_wrong_label_matches_extraction_not_joint():
    m, ann = score(["A"], [out("A", [pred("A", 0, 10, "unknown"), pred("A", 11, 20, "unknown"), pred("A", 21, 30, "contradicted")])], G)
    assert m["M"] == 3 and m["C"] == 2 and m["wrong_label_ids"] == ["A:0:10"]
    assert ann[("A", 0, 10)] == ("A:0:10", "supported", False)


def test_partial_span_is_unmatched():
    m, _ = score(["A"], [out("A", [pred("A", 0, 9, "supported")])], G)
    assert m["M"] == 0 and m["P"] == 1


def test_error_answer_keeps_gold_as_missed_and_adds_no_predictions():
    g = G + gold("B", [(0, 5, "unknown")])
    m, _ = score(["A", "B"], [out("A", [pred("A", 0, 10, "supported"), pred("A", 11, 20, "unknown"), pred("A", 21, 30, "contradicted")]),
                              out("B", [], "error")], g)
    assert m["G"] == 4 and m["P"] == 3 and m["answer_error_count"] == 1 and "B:0:5" in m["missed_gold_ids"]
    assert m["joint"]["recall"] == 0.75


def test_valid_empty_prediction_zero_credit():
    m, _ = score(["A"], [out("A", [])], G)
    assert m["P"] == 0 and m["joint"]["f1"] == 0.0 and m["extraction"]["precision"] == 0.0


def test_spec_example_G10_P10_M8_C7():
    gs = gold("A", [(i * 10, i * 10 + 9, "supported") for i in range(10)])
    ps = [pred("A", i * 10, i * 10 + 9, "supported") for i in range(7)]
    ps.append(pred("A", 70, 79, "unknown"))                        # matched, wrong label
    ps += [pred("A", 500, 509, "unknown"), pred("A", 510, 519, "unknown")]  # extras
    m, _ = score(["A"], [out("A", ps)], gs)
    assert (m["G"], m["P"], m["M"], m["C"]) == (10, 10, 8, 7)
    assert m["extraction"]["precision"] == m["extraction"]["recall"] == m["extraction"]["f1"] == pytest.approx(0.8)
    assert m["joint"]["precision"] == m["joint"]["recall"] == m["joint"]["f1"] == pytest.approx(0.7)
    assert 7 / 8 != m["joint"]["f1"]  # matched-only accuracy is not the score


def test_missing_or_duplicate_outcomes_rejected():
    with pytest.raises(ScoringError):
        score(["A", "B"], [out("A", [])], G)
    with pytest.raises(ScoringError):
        score(["A"], [out("A", []), out("A", [])], G)
    with pytest.raises(ScoringError):
        score(["A"], [out("A", []), out("Z", [])], G)


def test_empty_split_null_metrics():
    assert score([], [], [])[0] is None
