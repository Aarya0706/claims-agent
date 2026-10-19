"""Typed errors. AgentError subclasses become answer-level errors (never silently 'unknown')."""
import re


def sanitize(msg: object, limit: int = 300) -> str:
    s = re.sub(r"\s+", " ", str(msg))
    s = re.sub(r"sk-[A-Za-z0-9_\-]{8,}", "[redacted-key]", s)
    s = re.sub(r"(?i)(api[_-]?key|authorization|bearer)\S*\s*[:=]?\s*\S+", "[redacted]", s)
    return s[:limit]


class AgentError(Exception):
    type = "agent_error"

    def __init__(self, message: str = ""):
        super().__init__(sanitize(message))
        self.message = sanitize(message)


class InvalidOutputError(AgentError):
    type = "invalid_output"


class IllegalToolError(AgentError):
    type = "illegal_tool"


class UnknownBrandError(AgentError):
    type = "unknown_brand"


class TurnLimitError(AgentError):
    type = "turn_limit"


class ProviderError(AgentError):
    type = "provider_error"


class ProviderTimeout(AgentError):
    type = "provider_timeout"


class InfrastructureError(Exception):
    """Auth/config/DB problems: the whole RUN fails (not a per-answer error)."""
