#!/usr/bin/env python
"""Capture ONE real, sanitized model/tool exchange from a live call.

    python scripts/capture_exchange.py --version v1 --answer-id A01

Runs the real agent loop for a single answer (about 2 provider requests) through a logging wrapper and
writes docs/sample_exchange.md. Nothing is invented: every block is what the provider returned or what
the executor sent back. Long fields are truncated, and the API key is redacted if it ever appears.
"""
import argparse
import json
import os
import sys
from pathlib import Path


def shorten(obj, max_str=300, max_items=2):
    """Truncate long strings and lists so the exchange stays readable (shows how much was cut)."""
    if isinstance(obj, str):
        return obj if len(obj) <= max_str else obj[:max_str] + f"... [truncated, {len(obj)} chars total]"
    if isinstance(obj, list):
        out = [shorten(x, max_str, max_items) for x in obj[:max_items]]
        if len(obj) > max_items:
            out.append(f"... [{len(obj) - max_items} more items, {len(obj)} total]")
        return out
    if isinstance(obj, dict):
        return {k: shorten(v, max_str, max_items) for k, v in obj.items()}
    return obj


def as_json(obj) -> str:
    return json.dumps(shorten(obj), indent=2, ensure_ascii=False, default=str)


class LoggingProvider:
    """Forwards every call to the real provider and records the payload and the response."""

    def __init__(self, inner):
        self.inner = inner
        self.name = getattr(inner, "name", "")
        self.model = getattr(inner, "model", "")
        self.settings = getattr(inner, "settings", {})
        self.calls = []

    def complete(self, **kw):
        resp = self.inner.complete(**kw)
        msgs = [{k: v for k, v in m.items() if k != "raw"} for m in kw.get("messages", [])]
        self.calls.append({
            "force_tool": kw.get("force_tool"),
            "timeout": kw.get("timeout"),
            "system": kw.get("system", ""),
            "messages": json.loads(json.dumps(msgs, default=str)),
            "text": getattr(resp, "text", ""),
            "tool_calls": [{"id": t.id, "name": t.name, "arguments": t.arguments}
                           for t in (getattr(resp, "tool_calls", None) or [])],
        })
        return resp


def render(calls, answer_id, version, provider_name, model, output, error):
    lines = [
        "# Sample model/tool exchange (real, sanitized)",
        "",
        f"One real live call to `{provider_name}` / `{model}` for answer `{answer_id}` with agent version `{version}`,",
        "captured with `scripts/capture_exchange.py` through the unchanged agent loop. It was captured separately",
        "from the four saved runs (their `trace_ref` fields are null), so the model output can differ from the saved run",
        "for the same answer (default temperature). Long fields are truncated; nothing else is edited.",
        "",
    ]
    for i, c in enumerate(calls, 1):
        lines += [f"## Turn {i}", ""]
        if i == 1:
            lines += ["**System prompt (start):**", "```text", shorten(c["system"], 500), "```", ""]
            first = c["messages"][0] if c["messages"] else {}
            lines += ["**User message to the model (start):**", "```text",
                      shorten(first.get("content", ""), 700), "```", ""]
            lines += [f"Provider call: `force_tool={c['force_tool']}`, timeout {c['timeout']} s", ""]
        else:
            tool_msgs = [m for m in c["messages"] if m.get("role") == "tool"]
            lines += ["**Executor result sent back to the model (tool results):**", "```json"]
            results = []
            for r in (tool_msgs[-1].get("results", []) if tool_msgs else []):
                try:
                    results.append({**r, "content": json.loads(r["content"])})  # show the real structure
                except Exception:
                    results.append(r)
            lines += [as_json(results) if results else "(none)", "```", ""]
        if c["tool_calls"]:
            lines += ["**Model response: tool request**", "```json", as_json(c["tool_calls"]), "```", ""]
        if c["text"]:
            lines += ["**Model response: text**", "```text", shorten(c["text"], 900), "```", ""]
    lines += ["## Result", ""]
    if error:
        lines += [f"The agent raised an error (preserved as an answer-level error): `{error}`", ""]
    else:
        claims = [c.model_dump() for c in output.claims]
        lines += [f"Validated output: {len(claims)} claims (first 2 shown).", "```json", as_json(claims), "```", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1", choices=["v1", "v2"])
    ap.add_argument("--answer-id", default="A01")
    ap.add_argument("--out", default="docs/sample_exchange.md")
    a = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from dotenv import load_dotenv
    load_dotenv()
    from claims import data
    from claims.agent import DEFAULT_TIMEOUT_S, run_agent
    from claims.errors import AgentError
    from claims.models import AgentInput
    from claims.provider import make_provider

    rows = {r["answer_id"]: r for r in data.load_answers()}
    row = rows[a.answer_id]
    inp = AgentInput(**{k: row[k] for k in ("answer_id", "brand_id", "question", "ai_answer")})
    prov = LoggingProvider(make_provider(None, None, min_interval=6.5))
    output, error = None, None
    try:
        output = run_agent(inp, prov, a.version, timeout=DEFAULT_TIMEOUT_S)
    except AgentError as e:
        error = f"{e.type}: {e.message}"

    text = render(prov.calls, a.answer_id, a.version, prov.name, prov.model, output, error)
    key = os.getenv("GEMINI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if key:
        text = text.replace(key, "[REDACTED]")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out} ({len(prov.calls)} provider calls)")


if __name__ == "__main__":
    main()