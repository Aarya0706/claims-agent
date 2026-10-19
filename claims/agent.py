"""The agent: <=3 model turns, real tool calling, strict validation, Python-computed offsets."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pydantic import ValidationError

from .data import Catalogue, default_catalogue
from .errors import (IllegalToolError, InvalidOutputError, TurnLimitError, UnknownBrandError)
from .models import AgentInput, AgentOutput, Claim, ModelClaim, ModelClaimIdx
from .prompts import PROMPT_VERSION, SYSTEM
from .provider import Provider

TOOL_SPEC = {
    "name": "get_brand_facts",
    "description": "Read-only lookup. Returns every catalogue fact row for one brand "
                   "(brand ids: cleartrail, stonewave, cloudnote) with fact_version speaker-catalogue-v4.",
    "input_schema": {"type": "object",
                     "properties": {"brand_id": {"type": "string", "description": "e.g. cleartrail"}},
                     "required": ["brand_id"]},
}
MAX_TURNS = 3
DEFAULT_TIMEOUT_S = 90.0  # per provider request; documented in README


# ---------- sentence segmentation (used by v2 and by tests) ----------
def split_sentences(text: str) -> list[tuple[int, int]]:
    """Spans (start, end) of sentences: ends at . ! ? followed by whitespace/end. Whitespace-trimmed."""
    spans, s = [], 0
    for m in re.finditer(r"[.!?](?=\s|$)", text):
        spans.append((s, m.end()))
        s = m.end()
    spans.append((s, len(text)))
    out = []
    for a, b in spans:
        seg = text[a:b]
        st = a + (len(seg) - len(seg.lstrip()))
        en = b - (len(seg) - len(seg.rstrip()))
        if en > st:
            out.append((st, en))
    return out


# ---------- validation ----------
def validate_claims(answer: str, claims: list[Claim], fact_ids: set[str]) -> None:
    seen_ids, last_end, last_start = set(), 0, -1
    for c in claims:
        if not (0 <= c.start_char < c.end_char <= len(answer)):
            raise InvalidOutputError(f"span out of bounds: {c.claim_id}")
        if c.quote != answer[c.start_char:c.end_char]:
            raise InvalidOutputError(f"quote does not equal answer slice: {c.claim_id}")
        if c.quote != c.quote.strip():
            raise InvalidOutputError(f"quote has leading/trailing whitespace: {c.claim_id}")
        if c.claim_id in seen_ids:
            raise InvalidOutputError(f"duplicate claim_id: {c.claim_id}")
        seen_ids.add(c.claim_id)
        if c.start_char < last_start:
            raise InvalidOutputError("claims not in increasing start_char order")
        if c.start_char < last_end:
            raise InvalidOutputError(f"overlapping claims at {c.claim_id}")
        last_start, last_end = c.start_char, c.end_char
        bad = [f for f in c.fact_ids if f not in fact_ids]
        if bad:
            raise InvalidOutputError(f"unknown fact_id: {bad[0][:60]}")


def trim_reason(reason: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", reason.strip())
    return " ".join(parts[:2])


def make_claim(answer_id: str, start: int, end: int, quote: str, label, fact_ids, reason) -> Claim:
    return Claim(claim_id=f"{answer_id}:{start}:{end}", start_char=start, end_char=end, quote=quote,
                 label=label, fact_ids=list(fact_ids), reason=trim_reason(reason))


def parse_final_json(text: str) -> list[dict]:
    t = text.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", t, re.S)
    if m:
        t = m.group(1)
    try:
        obj = json.loads(t)
    except Exception:
        raise InvalidOutputError("final response is not valid JSON")
    if not isinstance(obj, dict) or not isinstance(obj.get("claims"), list):
        raise InvalidOutputError("final JSON must be an object with a 'claims' list")
    return obj["claims"]


def build_claims_v1(inp: AgentInput, items: list[dict]) -> list[Claim]:
    claims, cursor = [], 0
    for n, raw in enumerate(items):
        try:
            mc = ModelClaim.model_validate(raw)
        except ValidationError as e:
            raise InvalidOutputError(f"claim #{n} failed schema: field {e.errors()[0]['loc']} is {e.errors()[0]['type']}; "
                                     "every claim needs quote, label, fact_ids, reason")
        if not mc.quote or mc.quote != mc.quote.strip():
            raise InvalidOutputError("empty quote or quote with surrounding whitespace")
        i = inp.ai_answer.find(mc.quote, cursor)  # repeated quotes: next occurrence after previous claim
        if i < 0:
            raise InvalidOutputError("quote not found in answer (or out of order)")
        claims.append(make_claim(inp.answer_id, i, i + len(mc.quote), mc.quote, mc.label, mc.fact_ids, mc.reason))
        cursor = i + len(mc.quote)
    return claims


def build_claims_v2(inp: AgentInput, items: list[dict]) -> list[Claim]:
    spans, claims, last = split_sentences(inp.ai_answer), [], -1
    for n, raw in enumerate(items):
        try:
            mc = ModelClaimIdx.model_validate(raw)
        except ValidationError as e:
            raise InvalidOutputError(f"claim #{n} failed schema: field {e.errors()[0]['loc']} is {e.errors()[0]['type']}; "
                                     "every claim needs sentence_index, label, fact_ids, reason")
        if not (0 <= mc.sentence_index < len(spans)) or mc.sentence_index <= last:
            raise InvalidOutputError("sentence_index out of range, duplicated or out of order")
        last = mc.sentence_index
        a, b = spans[mc.sentence_index]
        claims.append(make_claim(inp.answer_id, a, b, inp.ai_answer[a:b], mc.label, mc.fact_ids, mc.reason))
    return claims


def build_user_message(inp: AgentInput, version: str) -> str:
    head = (f"answer_id: {inp.answer_id}\nprimary brand_id: {inp.brand_id}\nquestion: {inp.question}\n")
    if version == "v2":
        body = "\n".join(f"[{i}] {inp.ai_answer[a:b]}" for i, (a, b) in enumerate(split_sentences(inp.ai_answer)))
        return head + "<answer_sentences>\n" + body + "\n</answer_sentences>"
    return head + "<answer>\n" + inp.ai_answer + "\n</answer>"


# ---------- tool executor ----------
def execute_tool(name: str, arguments: object, catalogue: Catalogue) -> dict:
    if name != "get_brand_facts":
        raise IllegalToolError(f"illegal tool requested: {name[:40]!r}")
    if not isinstance(arguments, dict) or set(arguments) - {"brand_id"} or not isinstance(arguments.get("brand_id"), str):
        raise InvalidOutputError("get_brand_facts requires exactly one string argument: brand_id")
    if arguments["brand_id"] not in catalogue.brands:
        raise UnknownBrandError(f"unknown brand requested: {arguments['brand_id'][:40]!r}")
    return catalogue.get_brand_facts(arguments["brand_id"])


@dataclass
class AgentRun:
    output: AgentOutput
    turns: int
    tool_calls: int
    repairs: int = 0


def run_agent(inp: AgentInput, provider: Provider, version: str = "v1", *, catalogue: Catalogue | None = None,
              timeout: float = DEFAULT_TIMEOUT_S, max_turns: int = MAX_TURNS) -> AgentOutput:
    return run_agent_detailed(inp, provider, version, catalogue=catalogue, timeout=timeout,
                              max_turns=max_turns).output


def run_agent_detailed(inp: AgentInput, provider: Provider, version: str = "v1", *, catalogue=None,
                       timeout: float = DEFAULT_TIMEOUT_S, max_turns: int = MAX_TURNS) -> AgentRun:
    if version not in SYSTEM:
        raise ValueError(f"unknown agent version {version!r}")
    cat = catalogue or default_catalogue()
    max_turns = min(max_turns, MAX_TURNS)
    messages = [{"role": "user", "content": build_user_message(inp, version)}]
    n_tools = repairs = 0
    for turn in range(1, max_turns + 1):
        resp = provider.complete(system=SYSTEM[version], messages=messages, tools=[TOOL_SPEC],
                                 timeout=timeout, force_tool=(turn == 1))
        if resp.tool_calls:
            if turn == max_turns:
                raise TurnLimitError(f"model still requesting tools on turn {turn}")
            results = []
            for tc in resp.tool_calls:
                results.append({"id": tc.id, "content": json.dumps(execute_tool(tc.name, tc.arguments, cat))})
                n_tools += 1
            messages.append({"role": "assistant", "text": resp.text, "raw": resp.raw,
                             "tool_calls": [{"id": t.id, "name": t.name, "arguments": t.arguments} for t in resp.tool_calls]})
            messages.append({"role": "tool", "results": results})
            continue
        if n_tools == 0:
            raise InvalidOutputError("final answer produced without calling get_brand_facts")
        try:
            items = parse_final_json(resp.text)
            claims = (build_claims_v2 if version == "v2" else build_claims_v1)(inp, items)
            validate_claims(inp.ai_answer, claims, cat.fact_ids)
        except InvalidOutputError as e:
            if turn < max_turns:  # spend ONE spare turn (limit is 3) returning the validation error for a corrected reply
                messages.append({"role": "assistant", "text": resp.text, "raw": resp.raw, "tool_calls": []})
                messages.append({"role": "user", "content": f"Your JSON was rejected: {e.message} Return the complete corrected "
                                                            "JSON object only, in the same format, with every claim valid."})
                repairs += 1
                continue
            raise
        return AgentRun(AgentOutput(answer_id=inp.answer_id, claims=claims), turn, n_tools, repairs)
    raise TurnLimitError("turn limit exhausted")


def prompt_version(version: str) -> str:
    return PROMPT_VERSION[version]