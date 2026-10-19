import json
import pytest
from claims.models import AgentInput
from claims.provider import FakeProvider, ProviderResponse, ToolCall

ANSWER = ("Start with the model name. ClearTrail Mini is listed at INR 1,299 for 2026. "
          "Do you need it for travel? ClearTrail Mini has IPX4 water resistance. Great sound, honestly.")
INP = AgentInput(answer_id="T01", brand_id="cleartrail", question="q", ai_answer=ANSWER)
S2 = "ClearTrail Mini is listed at INR 1,299 for 2026."
S4 = "ClearTrail Mini has IPX4 water resistance."


def tool(brand="cleartrail", name="get_brand_facts", args=None, id="t1"):
    return ProviderResponse(tool_calls=[ToolCall(id, name, {"brand_id": brand} if args is None else args)])


def final(items):
    return ProviderResponse(text=json.dumps({"claims": items}))


def item(q, label="supported", ids=("cleartrail.mini.price_2026",), reason="ok."):
    return {"quote": q, "label": label, "fact_ids": list(ids), "reason": reason}


@pytest.fixture
def inp():
    return INP


def fake(*script):
    return FakeProvider(list(script))
