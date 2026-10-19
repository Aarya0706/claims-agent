import pytest
from claims.agent import split_sentences, validate_claims, make_claim
from claims.errors import InvalidOutputError
from claims.models import Claim

A = "One is here. Two is here. Three is here."
IDS = {"f.1"}


def c(s, e, label="unknown", ids=(), quote=None):
    return Claim(claim_id=f"X:{s}:{e}", start_char=s, end_char=e, quote=A[s:e] if quote is None else quote,
                 label=label, fact_ids=list(ids), reason="r")


def test_valid():
    validate_claims(A, [c(0, 12), c(13, 25)], IDS)
    validate_claims(A, [], IDS)  # valid empty list


@pytest.mark.parametrize("bad", [c(0, 99), c(-1, 5, quote="x"), c(5, 5, quote="")])
def test_bad_bounds(bad):
    with pytest.raises(InvalidOutputError):
        validate_claims(A, [bad], IDS)


def test_quote_mismatch_and_whitespace():
    with pytest.raises(InvalidOutputError):
        validate_claims(A, [c(0, 12, quote="One is HERE.")], IDS)
    with pytest.raises(InvalidOutputError):
        validate_claims(A, [c(12, 25)], IDS)  # leading space in slice


def test_duplicate_and_overlap_and_order():
    with pytest.raises(InvalidOutputError):
        validate_claims(A, [c(0, 12), c(0, 12)], IDS)
    with pytest.raises(InvalidOutputError):
        validate_claims(A, [c(0, 12), c(4, 12)], IDS)
    with pytest.raises(InvalidOutputError):
        validate_claims(A, [c(13, 25), c(0, 12)], IDS)


def test_fact_ids_must_exist():
    validate_claims(A, [c(0, 12, ids=["f.1"])], IDS)
    with pytest.raises(InvalidOutputError):
        validate_claims(A, [c(0, 12, ids=["f.nope"])], IDS)


def test_claim_id_derivation_and_reason_trim():
    cl = make_claim("A01", 0, 12, A[:12], "unknown", [], "One. Two. Three.")
    assert cl.claim_id == "A01:0:12" and cl.reason == "One. Two."


def test_split_sentences_whitespace_trimmed():
    t = "A b.\n\n  C d! E?  F"
    sp = split_sentences(t)
    assert [t[a:b] for a, b in sp] == ["A b.", "C d!", "E?", "F"]
