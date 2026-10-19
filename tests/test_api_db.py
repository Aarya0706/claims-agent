"""API validation + real PostgreSQL persistence. DB tests need TEST_DATABASE_URL (skipped otherwise - and reported as skipped)."""
import json
import os
import uuid

import pytest
from fastapi.testclient import TestClient

from claims import api, db, data
from claims.errors import ProviderError, ProviderTimeout
from claims.provider import FakeProvider
from tests.conftest import ANSWER, S2, final, item, tool

DB_URL = os.getenv("TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")
BODY = {"answer_id": "T01", "brand_id": "cleartrail", "question": "q", "ai_answer": ANSWER, "agent_version": "v1"}


def client(provider, conn_factory=None):
    api.app.dependency_overrides[api.get_provider] = lambda: (lambda: provider)
    if conn_factory:
        api.app.dependency_overrides[api.get_connect] = lambda: conn_factory
    return TestClient(api.app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clean():
    yield
    api.app.dependency_overrides.clear()


def test_classify_200():
    r = client(FakeProvider([tool(), final([item(S2)])])).post("/classify", json=BODY)
    assert r.status_code == 200 and r.json()["claims"][0]["quote"] == S2


@pytest.mark.parametrize("extra", [{"claims": []}, {"expected_label": "supported"}, {"evidence_fact_ids": "x"}])
def test_classify_rejects_gold_or_claim_fields_422(extra):
    r = client(FakeProvider([])).post("/classify", json={**BODY, **extra})
    assert r.status_code == 422 and ANSWER[:30] not in r.text      # no echo of submitted text


@pytest.mark.parametrize("patch", [{"agent_version": "v3"}, {"ai_answer": ""}, {"brand_id": None}])
def test_classify_invalid_422(patch):
    assert client(FakeProvider([])).post("/classify", json={**BODY, **patch}).status_code == 422


def test_classify_missing_field_422():
    b = dict(BODY); b.pop("question")
    assert client(FakeProvider([])).post("/classify", json=b).status_code == 422


def test_unknown_primary_brand_404():
    assert client(FakeProvider([])).post("/classify", json={**BODY, "brand_id": "acme"}).status_code == 404


def test_provider_error_502_timeout_504_invalid_502():
    assert client(FakeProvider([ProviderError("x")])).post("/classify", json=BODY).status_code == 502
    r = client(FakeProvider([ProviderTimeout("x")])).post("/classify", json=BODY)
    assert r.status_code == 504 and r.json()["error"]["type"] == "provider_timeout"
    assert client(FakeProvider([tool(), final([item("not in answer")])])).post("/classify", json=BODY).status_code == 502


def test_invalid_uuid_422():
    assert client(FakeProvider([])).get("/evaluation-runs/not-a-uuid").status_code == 422


# ---- PostgreSQL (real) ----
@pytest.fixture
def conn_factory():
    c0 = db.connect(DB_URL)
    c0.execute("DROP TABLE IF EXISTS claim_results, answer_results, runs CASCADE"); c0.commit()
    db.init_schema(c0); c0.close()

    return lambda: db.connect(DB_URL)


def mixed_provider():
    """answers alternate: valid claims, valid empty, provider error -> exercises success/empty/error rows."""
    state = {"n": 0}

    def script(messages):
        if len(messages) == 1:
            state["n"] += 1
            if state["n"] % 3 == 0:
                raise ProviderError("boom")
            return tool()
        return final([]) if state["n"] % 3 == 2 else final(
            [item(m, "unknown", []) for m in _first_sentence(messages[0]["content"])])
    return FakeProvider(script)


def _first_sentence(content):
    body = content.split("<answer>\n", 1)[1].rsplit("\n</answer>", 1)[0]
    return [body[: body.index(". ") + 1]]


@needs_db
def test_dev_run_persist_and_joined_retrieval(conn_factory):
    c = client(mixed_provider(), conn_factory)
    r = c.post("/evaluation-runs", json={"agent_version": "v1", "split": "development"})
    assert r.status_code == 201
    j = r.json(); assert j["status"] == "completed" and j["counts"]["scheduled"] == 40 and j["counts"]["errors"] > 0
    assert j["metrics"]["G"] == 376 and j["metrics"]["answer_error_count"] == j["counts"]["errors"]
    g = c.get(f"/evaluation-runs/{j['run_id']}").json()
    ids = [a["answer_id"] for a in g["answers"]]
    assert ids == sorted(ids) and len(ids) == 40                       # one terminal row per scheduled answer
    st = {a["status"] for a in g["answers"]}; assert st == {"ok", "error"}
    assert any(a["status"] == "ok" and a["claims"] == [] for a in g["answers"])           # valid empty
    assert all(a["claims"] == [] and a["error"]["type"] == "provider_error" for a in g["answers"] if a["status"] == "error")
    for a in g["answers"]:
        starts = [x["start_char"] for x in a["claims"]]; assert starts == sorted(starts)
    assert g["metrics"] == j["metrics"] and g["file_hashes"] == data.file_hashes()


@needs_db
def test_check_run_metrics_null_and_no_gold_fields(conn_factory):
    c = client(mixed_provider(), conn_factory)
    j = c.post("/evaluation-runs", json={"agent_version": "v2", "split": "check"})
    assert j.status_code == 201 and j.json()["metrics"] is None and j.json()["counts"]["scheduled"] == 10
    g = c.get(f"/evaluation-runs/{j.json()['run_id']}").json()
    assert g["metrics"] is None
    assert all(x["matched_gold_claim_id"] is None and x["expected_label"] is None and x["correct"] is None
               for a in g["answers"] for x in a["claims"])


@needs_db
def test_missing_run_404_and_constraints(conn_factory):
    c = client(FakeProvider([]), conn_factory)
    assert c.get(f"/evaluation-runs/{uuid.uuid4()}").status_code == 404
    import psycopg
    run = __import__("claims.runner", fromlist=["x"]).run_split("v1", "check", mixed_provider(), limit=1)
    conn = db.connect(DB_URL); db.save_run(conn, run)
    with pytest.raises(psycopg.errors.UniqueViolation):                      # (run_id, answer_id) unique
        with conn.transaction():
            conn.execute("INSERT INTO answer_results (run_id, answer_id, status) VALUES (%s,%s,'ok')",
                         (run["run_id"], run["answers"][0]["answer_id"]))
    with pytest.raises(psycopg.errors.ForeignKeyViolation):                  # claims need an answer row
        with conn.transaction():
            conn.execute("INSERT INTO claim_results (run_id,answer_id,claim_id,start_char,end_char,quote,label,reason) "
                         "VALUES (%s,'ZZZ','c',0,1,'q','unknown','r')", (run["run_id"],))
    conn.close()
