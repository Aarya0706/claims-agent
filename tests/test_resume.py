"""Quota-stop / resume behaviour (the main deadline risk)."""
import copy
import json
import pytest
from claims import runner
from claims.errors import InfrastructureError, ProviderError
from claims.provider import FakeProvider
from tests.conftest import final, tool


def good_script(messages):
    return tool() if len(messages) == 1 else final([])


class StopAfter:
    """Works for n answers (2 requests each), then the daily quota is gone."""
    def __init__(self, n): self.n, self.seen = n, 0
    def __call__(self, messages):
        if len(messages) == 1:
            self.seen += 1
            if self.seen > self.n:
                raise InfrastructureError("daily quota exhausted")
            return tool()
        return final([])


def test_quota_stop_saves_partial_then_resume_completes_without_redoing_work():
    saved = []
    p1 = FakeProvider(StopAfter(5))
    run = runner.run_split("v1", "development", p1, checkpoint=lambda r: saved.append(copy.deepcopy(r)))
    assert run["status"] == "failed" and "quota" in run["error"] and len(run["answers"]) == 5
    assert run["metrics"] is None                                   # no scoring of an incomplete run
    assert len(saved) >= 5 and len(saved[4]["answers"]) == 5        # checkpoint after EVERY answer

    p2 = FakeProvider(good_script)
    done = runner.run_split("v1", "development", p2, resume=json.loads(json.dumps(run)))
    assert done["status"] == "completed" and done["run_id"] == run["run_id"]
    assert len(done["answers"]) == 40 and done["metrics"]["G"] == 376
    assert len(p2.calls) == 35 * 2                                  # only the 35 missing answers were requested
    assert [a["answer_id"] for a in done["answers"]] == sorted(a["answer_id"] for a in done["answers"])
    assert len(done["resumes"]) == 1


def test_resume_retries_transient_provider_errors_but_keeps_other_errors():
    n = {"i": 0}

    def script(messages):
        if len(messages) == 1:
            n["i"] += 1
            if n["i"] == 2:
                raise ProviderError("429 blip")
            return tool()
        return ProviderResponse_text_bad() if n["i"] == 3 else final([])
    from claims.provider import ProviderResponse
    ProviderResponse_text_bad = lambda: ProviderResponse(text="not json")      # invalid_output -> a real result
    run = runner.run_split("v1", "development", FakeProvider(script), limit=4)
    types = {a["answer_id"]: (a["error"] or {}).get("type") for a in run["answers"]}
    assert types["A02"] == "provider_error" and types["A03"] == "invalid_output"
    p2 = FakeProvider(good_script)
    done = runner.run_split("v1", "development", p2, limit=4, resume=run)
    t2 = {a["answer_id"]: a["status"] for a in done["answers"]}
    assert t2["A02"] == "ok"                                          # transient error re-run
    assert t2["A03"] == "error"                                       # invalid_output preserved, not re-rolled
    assert len(p2.calls) == 2 and done["resumes"][0]["retried_provider_errors"] == ["A02"]


def test_circuit_breaker_stops_after_5_consecutive_provider_failures():
    p = FakeProvider([ProviderError("429")])
    run = runner.run_split("v1", "development", p)
    assert run["status"] == "failed" and len(run["answers"]) == 5 and "consecutive" in run["error"]
    assert len(p.calls) == 5                                          # did not burn 40 requests on a dead provider


def test_resume_refuses_mismatched_run():
    run = runner.run_split("v1", "development", FakeProvider(StopAfter(2)))
    for bad in [dict(version="v2", split="development"), dict(version="v1", split="check")]:
        with pytest.raises(InfrastructureError):
            runner.run_split(bad["version"], bad["split"], FakeProvider(good_script), resume=run)
    tampered = copy.deepcopy(run); tampered["file_hashes"]["answers"] = "x"
    with pytest.raises(InfrastructureError):
        runner.run_split("v1", "development", FakeProvider(good_script), resume=tampered)


def test_check_split_resume_keeps_metrics_null():
    run = runner.run_split("v2", "check", FakeProvider(StopAfter(3)))
    assert run["status"] == "failed" and len(run["answers"]) == 3
    done = runner.run_split("v2", "check", FakeProvider(good_script), resume=run)
    assert done["status"] == "completed" and done["metrics"] is None and len(done["answers"]) == 10