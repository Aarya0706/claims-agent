from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Label = Literal["supported", "contradicted", "unknown"]


class AgentInput(BaseModel):
    """Exactly the four permitted input fields; anything else (gold, claims...) -> 422."""
    model_config = ConfigDict(extra="forbid")
    answer_id: str = Field(min_length=1)
    brand_id: str = Field(min_length=1)
    question: str
    ai_answer: str = Field(min_length=1)


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    start_char: int
    end_char: int
    quote: str
    label: Label
    fact_ids: list[str]
    reason: str


class AgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer_id: str
    claims: list[Claim]


class ModelClaim(BaseModel):
    """v1: model returns an exact quote; Python locates the offsets."""
    quote: str
    label: Label
    fact_ids: list[str]
    reason: str


class ModelClaimIdx(BaseModel):
    """v2: model returns an index into the Python-segmented sentences."""
    sentence_index: int
    label: Label
    fact_ids: list[str]
    reason: str
