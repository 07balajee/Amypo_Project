"""Pydantic models for the Q&A API. Field names/types here are the exact contract from
CLAUDE.md §6 — never rename a required field; new fields must be additive only."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Path = Literal["sql", "rag", "abstain"]

ABSTAIN_MESSAGE = "I couldn't find this in AMYPO's records."


class AskRequest(BaseModel):
    question: str
    user_id: str | None = None
    conversation_id: str | None = None


class Source(BaseModel):
    record_id: str
    snippet: str


class AskMeta(BaseModel):
    path: Path
    intent: str
    routed_to: str | None = None
    abstained: bool
    route_request_id: str | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
    confidence: float
    meta: AskMeta


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    components: dict[str, Any] = Field(default_factory=dict)
    version: str


def abstain_response(intent: str = "out_of_scope") -> AskResponse:
    return AskResponse(
        answer=ABSTAIN_MESSAGE,
        sources=[],
        confidence=0.0,
        meta=AskMeta(path="abstain", intent=intent, routed_to=None, abstained=True, route_request_id=None),
    )
