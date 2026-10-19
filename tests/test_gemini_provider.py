"""GeminiProvider against a stub client built from the REAL google-genai types (no network)."""
import json
import httpx
import pytest
from google.genai import errors, types

from claims import provider as P
from claims.agent import run_agent, TOOL_SPEC
from claims.errors import InfrastructureError, ProviderError, ProviderTimeout
from tests.conftest import INP, S2, item


def resp(*parts):
    return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role="model", parts=list(parts)))])


def fcall(brand="cleartrail", sig=b"SIG"):
    return types.Part(function_call=types.FunctionCall(name="get_brand_facts", args={"brand_id": brand}), thought_signature=sig)


def text(t, thought=False):
    return types.Part(text=t, thought=thought or None)


class Stub:
    def __init__(self, *script):
        self.script, self.calls = list(script), []
        self.models = self

    def generate_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        x = self.script.pop(0)
        if isinstance(x, Exception):
            raise x
        return x


def prov(*script, **kw):
    s = Stub(*script)
    return P.GeminiProvider(client=s, min_interval=0, **kw), s


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(P.time, "sleep", lambda s: None)


def api_err(code, msg):
    return errors.APIError(code, {"error": {"code": code, "message": msg, "status": "X"}})


def test_full_agent_loop_through_gemini_replays_raw_thought_signature():
    final = json.dumps({"claims": [item(S2)]})
    p, stub = prov(resp(text("thinking...", thought=True), fcall()), resp(text(final)))
    out = run_agent(INP, p, "v1")
    assert out.claims[0].quote == S2
    c1, c2 = stub.calls
    assert c1["config"].tool_config.function_calling_config.mode == "ANY"      # forced tool use on turn 1
    assert c2["config"].tool_config.function_calling_config.mode == "AUTO"
    replay = c2["contents"][1]                                                  # model turn replayed verbatim
    assert replay.parts[-1].thought_signature == b"SIG"
    fr = c2["contents"][2].parts[0].function_response
    assert fr.name == "get_brand_facts" and fr.response["result"]["fact_version"] == "speaker-catalogue-v4"
    assert c2["config"].http_options.timeout == 90000 and c1["config"].tools[0].function_declarations[0].name == "get_brand_facts"


def test_thought_parts_not_returned_as_text():
    r = prov(resp(text("secret reasoning", thought=True), text("{\"claims\": []}")))[0].complete(
        system="s", messages=[{"role": "user", "content": "x"}], tools=[TOOL_SPEC], timeout=5, force_tool=False)
    assert r.text == '{"claims": []}'


def test_multiple_tool_calls_one_turn():
    p, _ = prov(resp(fcall("cleartrail"), fcall("stonewave", sig=None)))
    r = p.complete(system="s", messages=[{"role": "user", "content": "x"}], tools=[TOOL_SPEC], timeout=5, force_tool=True)
    assert [c.arguments["brand_id"] for c in r.tool_calls] == ["cleartrail", "stonewave"] and len({c.id for c in r.tool_calls}) == 2


def call(p):
    return p.complete(system="s", messages=[{"role": "user", "content": "x"}], tools=[TOOL_SPEC], timeout=5, force_tool=False)


def test_429_is_retried_then_succeeds():
    p, s = prov(api_err(429, "quota. Please retry in 7.2s"), resp(text("ok")))
    assert call(p).text == "ok" and len(s.calls) == 2


def test_429_exhausted_is_answer_level_provider_error():
    p, _ = prov(*[api_err(429, "slow down")] * 4, max_retries=3)
    with pytest.raises(ProviderError):
        call(p)


def test_daily_quota_fails_the_run_not_one_answer():
    p, s = prov(api_err(429, "Quota exceeded for metric ... RequestsPerDay"))
    with pytest.raises(InfrastructureError):
        call(p)
    assert len(s.calls) == 1                                                    # no pointless retries


@pytest.mark.parametrize("code,msg", [(401, "bad"), (403, "denied"), (400, "API key not valid")])
def test_auth_is_infrastructure(code, msg):
    with pytest.raises(InfrastructureError):
        call(prov(api_err(code, msg))[0])


def test_unknown_model_is_infrastructure_with_hint():
    with pytest.raises(InfrastructureError, match="list_models"):
        call(prov(api_err(404, "model not found"))[0])


def test_timeouts_map_to_provider_timeout():
    with pytest.raises(ProviderTimeout):
        call(prov(httpx.ReadTimeout("t"))[0])
    with pytest.raises(ProviderTimeout):
        call(prov(api_err(504, "DEADLINE_EXCEEDED"))[0])


def test_5xx_retried_and_empty_response_is_provider_error():
    p, s = prov(api_err(503, "overloaded"), resp(text("ok")))
    assert call(p).text == "ok" and len(s.calls) == 2
    with pytest.raises(ProviderError):
        call(prov(types.GenerateContentResponse(candidates=[]))[0])


def test_missing_key_message_and_factory(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False); monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(InfrastructureError, match="aistudio"):
        P.make_provider("gemini")
    with pytest.raises(InfrastructureError):
        P.make_provider("nope")


def test_throttle_spaces_requests(monkeypatch):
    t = {"now": 100.0, "slept": []}
    monkeypatch.setattr(P.time, "monotonic", lambda: t["now"])
    monkeypatch.setattr(P.time, "sleep", lambda s: (t["slept"].append(s), t.__setitem__("now", t["now"] + s)))
    P.GeminiProvider._last_call = 100.0
    p = P.GeminiProvider(client=Stub(resp(text("a")), resp(text("b"))), min_interval=6.5)
    call(p); call(p)
    assert t["slept"][0] == pytest.approx(6.5) and t["slept"][1] == pytest.approx(6.5)
