"""Pydantic models for the router API. Field names/types here are the exact contract from
CLAUDE.md §6 — never rename a required field; new fields must be additive only."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RoutedTo = Literal["local_model", "cloud_api", "cache", "offline_fallback"]
ComplexityHint = Literal["low", "medium", "high"]


class RouteRequest(BaseModel):
    request_id: str
    query: str
    complexity_hint: ComplexityHint | None = None
    max_tokens: int = 256
    user_scope: str = "global"
    dry_run: bool = False
    messages: list[dict[str, str]] | None = None


class RouteMeta(BaseModel):
    complexity: str
    complexity_prob: float
    candidates: list[str] = Field(default_factory=list)
    replanned: bool = False
    cache_level: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0


class RouteResponse(BaseModel):
    request_id: str
    routed_to: RoutedTo
    reasoning: str
    latency_ms: int
    estimated_cost: float
    response: str
    meta: RouteMeta


class ResourceStatus(BaseModel):
    ram_available_mb: float
    cpu_load_pct: float
    bandwidth_kbps: float
    api_quota_remaining: float
    source: Literal["live", "scenario", "manual"]
    sampled_at: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    components: dict[str, Any] = Field(default_factory=dict)
    version: str


class SimulateRequest(BaseModel):
    mode: Literal["manual", "scenario", "live"]
    ram_available_mb: float | None = None
    bandwidth_kbps: float | None = None
    api_quota_remaining: float | None = None
    cpu_load_pct: float | None = None
    scenario_file: str | None = None


class DecisionLogEntry(BaseModel):
    request_id: str
    ts: str
    query: str
    routed_to: RoutedTo
    reasoning: str
    latency_ms: int
    estimated_cost: float
