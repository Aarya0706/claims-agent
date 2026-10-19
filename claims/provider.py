"""Provider abstraction. The agent only sees neutral messages; AnthropicProvider adapts them
to real tool calling. FakeProvider (tests) records every payload it receives."""
from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol

from .errors import InfrastructureError, ProviderError, ProviderTimeout


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: object


@dataclass
class ProviderResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: object = None  # opaque provider message (e.g. Gemini thought signatures) replayed verbatim next turn


class Provider(Protocol):
    name: str
    model: str
    settings: dict

    def complete(self, *, system: str, messages: list[dict], tools: list[dict],
                 timeout: float, force_tool: bool) -> ProviderResponse: ...


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str | None = None, model: str | None = None,
                 temperature: float | None = 0.0, max_tokens: int = 4096):
        import anthropic
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise InfrastructureError("ANTHROPIC_API_KEY is not set")
        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=key, max_retries=1)
        self.model = model or os.getenv("CLAIMS_MODEL", "claude-sonnet-5-5")
        self.temperature, self.max_tokens = temperature, max_tokens
        self.settings = {"temperature": temperature, "max_tokens": max_tokens, "sdk_max_retries": 1}

    @staticmethod
    def _convert(messages: list[dict]) -> list[dict]:
        out = []
        for m in messages:
            if m["role"] == "user":
                out.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                blocks = []
                if m.get("text"):
                    blocks.append({"type": "text", "text": m["text"]})
                for tc in m.get("tool_calls", []):
                    blocks.append({"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["arguments"]})
                out.append({"role": "assistant", "content": blocks})
            elif m["role"] == "tool":
                out.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": r["id"], "content": r["content"],
                     **({"is_error": True} if r.get("is_error") else {})} for r in m["results"]]})
        return out

    def complete(self, *, system, messages, tools, timeout, force_tool):
        a = self._anthropic
        kwargs = dict(model=self.model, max_tokens=self.max_tokens, system=system,
                      messages=self._convert(messages), timeout=timeout,
                      tools=[{"name": t["name"], "description": t["description"],
                              "input_schema": t["input_schema"]} for t in tools])
        if force_tool:
            kwargs["tool_choice"] = {"type": "any"}
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        try:
            r = self.client.messages.create(**kwargs)
        except a.APITimeoutError as e:
            raise ProviderTimeout(f"provider request exceeded {timeout}s") from e
        except (a.AuthenticationError, a.PermissionDeniedError) as e:
            raise InfrastructureError(f"provider auth failed: {type(e).__name__}") from e
        except a.APIError as e:
            raise ProviderError(f"{type(e).__name__}: {getattr(e, 'message', e)}") from e
        text = "".join(b.text for b in r.content if b.type == "text")
        calls = [ToolCall(b.id, b.name, b.input) for b in r.content if b.type == "tool_use"]
        return ProviderResponse(text=text, tool_calls=calls)


class FakeProvider:
    """Scripted provider. Each script item is a ProviderResponse, an Exception to raise,
    or a callable(messages) -> ProviderResponse. `calls` records every payload seen."""
    name = "fake"
    model = "fake-model"
    settings: dict = {"fake": True}

    def __init__(self, script: list | Callable):
        self.script, self.calls, self._i = script, [], 0

    def complete(self, *, system, messages, tools, timeout, force_tool):
        self.calls.append({"system": system, "messages": [dict(m) for m in messages],
                           "tools": tools, "timeout": timeout, "force_tool": force_tool})
        if callable(self.script):
            return self.script(messages)
        item = self.script[min(self._i, len(self.script) - 1)]
        self._i += 1
        if isinstance(item, Exception):
            raise item
        return item(messages) if callable(item) else item


class GeminiProvider:
    """Google Gemini via the free AI Studio key (https://aistudio.google.com/apikey). No billing needed.
    - Free-tier requests/min and requests/day are tight: calls are throttled (min_interval) and 429s are retried.
    - Daily-quota exhaustion, bad key or unknown model raise InfrastructureError (the RUN fails, not one answer)."""
    name = "gemini"
    _lock = threading.Lock()
    _last_call = 0.0

    def __init__(self, api_key: str | None = None, model: str | None = None, temperature: float | None = None,
                 max_tokens: int = 8192, min_interval: float = 6.5, max_retries: int = 3, client=None):
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if client is None:
            if not key:
                raise InfrastructureError("GEMINI_API_KEY is not set (free key: https://aistudio.google.com/apikey)")
            from google import genai
            client = genai.Client(api_key=key)
        from google.genai import types
        self._types = types
        self.client = client
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        self.temperature, self.max_tokens = temperature, max_tokens
        self.min_interval, self.max_retries = min_interval, max_retries
        self.settings = {"temperature": temperature if temperature is not None else "model default",
                         "max_output_tokens": max_tokens, "min_interval_s": min_interval,
                         "retries_on_429": max_retries}

    # ---- neutral messages -> Gemini contents ----
    def _contents(self, messages: list[dict]) -> list:
        t, out, names = self._types, [], {}
        for m in messages:
            if m["role"] == "user":
                out.append(t.Content(role="user", parts=[t.Part(text=m["content"])]))
            elif m["role"] == "assistant":
                if m.get("raw") is not None:           # keeps thought_signature intact (required by Gemini 3)
                    out.append(m["raw"])
                else:
                    parts = ([t.Part(text=m["text"])] if m.get("text") else []) + [
                        t.Part(function_call=t.FunctionCall(name=c["name"], args=c["arguments"]))
                        for c in m.get("tool_calls", [])]
                    out.append(t.Content(role="model", parts=parts))
                names.update({c["id"]: c["name"] for c in m.get("tool_calls", [])})
            elif m["role"] == "tool":
                parts = []
                for r in m["results"]:
                    try:
                        payload = json.loads(r["content"])
                    except Exception:
                        payload = r["content"]
                    parts.append(t.Part(function_response=t.FunctionResponse(
                        name=names.get(r["id"], "get_brand_facts"), response={"result": payload})))
                out.append(t.Content(role="user", parts=parts))
        return out

    def _config(self, system, tools, timeout, force_tool):
        t = self._types
        decl = [t.FunctionDeclaration(
            name=x["name"], description=x["description"],
            parameters=t.Schema(type="OBJECT", required=x["input_schema"]["required"], properties={
                k: t.Schema(type="STRING", description=v.get("description", ""))
                for k, v in x["input_schema"]["properties"].items()})) for x in tools]
        kw = dict(system_instruction=system, tools=[t.Tool(function_declarations=decl)],
                  tool_config=t.ToolConfig(function_calling_config=t.FunctionCallingConfig(
                      mode="ANY" if force_tool else "AUTO")),
                  automatic_function_calling=t.AutomaticFunctionCallingConfig(disable=True),
                  max_output_tokens=self.max_tokens, http_options=t.HttpOptions(timeout=int(timeout * 1000)))
        if self.temperature is not None:
            kw["temperature"] = self.temperature
        return t.GenerateContentConfig(**kw)

    def _throttle(self):
        with GeminiProvider._lock:
            wait = GeminiProvider._last_call + self.min_interval - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            GeminiProvider._last_call = time.monotonic()

    @staticmethod
    def _retry_delay(msg: str, attempt: int) -> float:
        m = re.search(r"retry(?: in|Delay\W+)\s*([\d.]+)\s*s", msg, re.I)
        return min(float(m.group(1)) + 1 if m else 15.0 * (attempt + 1), 90.0)

    def complete(self, *, system, messages, tools, timeout, force_tool):
        import httpx
        from google.genai import errors
        contents, cfg = self._contents(messages), self._config(system, tools, timeout, force_tool)
        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                r = self.client.models.generate_content(model=self.model, contents=contents, config=cfg)
                break
            except httpx.TimeoutException as e:
                raise ProviderTimeout(f"provider request exceeded {timeout}s") from e
            except errors.APIError as e:
                msg = str(getattr(e, "message", "") or e)
                code = getattr(e, "code", None)
                if code == 429:
                    if re.search(r"per ?day|daily|RequestsPerDay", msg, re.I) or attempt == self.max_retries:
                        if re.search(r"per ?day|daily|RequestsPerDay", msg, re.I):
                            raise InfrastructureError("Gemini free-tier DAILY quota exhausted; resume tomorrow, "
                                                      "use a Flash-Lite model, or see AI Studio rate-limit page") from e
                        raise ProviderError("rate limited (429) after retries") from e
                    time.sleep(self._retry_delay(msg, attempt))
                    continue
                if code in (401, 403) or (code == 400 and re.search(r"API key", msg, re.I)):
                    raise InfrastructureError(f"Gemini auth failed ({code}); check GEMINI_API_KEY") from e
                if code == 404:
                    raise InfrastructureError(f"model {self.model!r} not available to this key; "
                                              "run scripts/list_models.py and set GEMINI_MODEL") from e
                if code == 504 or "DEADLINE" in msg.upper():
                    raise ProviderTimeout(f"provider request exceeded {timeout}s") from e
                if code and code >= 500 and attempt < self.max_retries:
                    time.sleep(5.0 * (attempt + 1))
                    continue
                raise ProviderError(f"Gemini error {code}: {msg}") from e
        cands = getattr(r, "candidates", None) or []
        if not cands or cands[0].content is None or not cands[0].content.parts:
            raise ProviderError("Gemini returned no content (blocked or empty response)")
        content, text, calls = cands[0].content, "", []
        for i, part in enumerate(content.parts):
            if getattr(part, "function_call", None):
                fc = part.function_call
                calls.append(ToolCall(fc.id or f"call_{i}", fc.name, dict(fc.args or {})))
            elif part.text and not getattr(part, "thought", False):
                text += part.text
        return ProviderResponse(text=text, tool_calls=calls, raw=content)


def make_provider(name: str | None = None, model: str | None = None, **kw):
    name = (name or os.getenv("CLAIMS_PROVIDER", "gemini")).lower()
    if name == "gemini":
        return GeminiProvider(model=model, **kw)
    if name == "anthropic":
        return AnthropicProvider(model=model)
    raise InfrastructureError(f"unknown provider {name!r} (use gemini or anthropic)")
