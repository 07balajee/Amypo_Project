"""Router service — POST /api/v1/route, GET /api/v1/resource-status, GET /api/v1/health,
/api/v1/admin/*. See CLAUDE.md §6 for the exact contract and §14 M0 for this milestone's scope:
a working skeleton with stub decision logic (always local_model) — the real decision engine
(cache/remote/offline candidates, feasibility, hysteresis, breaker) lands in M3/M5.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.db.conn import get_ops_conn
from app.core.inference.client import build_gateway_client
from app.core.monitor.snapshot import get_monitor
from app.router import complexity
from app.router.schemas import (
    DecisionLogEntry,
    HealthResponse,
    ResourceStatus,
    RouteMeta,
    RouteRequest,
    RouteResponse,
    SimulateRequest,
)

SERVICE_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.gateway = build_gateway_client(
        use_mock=settings.gateway.use_mock,
        local_url=settings.gateway.local_url,
        remote_url=settings.gateway.remote_url,
    )
    app.state.monitor = get_monitor()
    get_ops_conn()  # applies schema on startup
    yield
    await app.state.gateway.aclose()


app = FastAPI(title="AI Request Router", version=SERVICE_VERSION, lifespan=lifespan)


@app.get("/api/v1/health")
async def health() -> JSONResponse:
    components = {"ops_db": "ok", "gateway": "ok"}
    status = "ok"
    body = HealthResponse(status=status, components=components, version=SERVICE_VERSION)
    return JSONResponse(content=body.model_dump(), status_code=200)


@app.get("/api/v1/resource-status", response_model=ResourceStatus)
async def resource_status() -> ResourceStatus:
    snap = app.state.monitor.get_snapshot()
    return ResourceStatus(**snap.to_dict())


@app.post("/api/v1/route")
async def route(req: RouteRequest) -> JSONResponse:
    settings = app.state.settings
    start = time.perf_counter()

    comp = complexity.score(req.query, req.complexity_hint)
    routed_to = "local_model"
    reasoning = (
        f"M0 stub decision engine: always routes to local_model "
        f"(complexity={comp.label}, prob={comp.prob}); full candidate scoring lands in M5."
    )

    tokens_in = tokens_out = 0
    response_text = ""
    if not req.dry_run:
        messages = req.messages or [{"role": "user", "content": req.query}]
        result = await app.state.gateway.generate("local", messages, req.max_tokens)
        response_text = result.text
        tokens_in, tokens_out = result.tokens_in, result.tokens_out

    latency_ms = int((time.perf_counter() - start) * 1000)
    estimated_cost = 0.0

    body = RouteResponse(
        request_id=req.request_id,
        routed_to=routed_to,
        reasoning=reasoning,
        latency_ms=latency_ms,
        estimated_cost=estimated_cost,
        response=response_text,
        meta=RouteMeta(
            complexity=comp.label,
            complexity_prob=comp.prob,
            candidates=[routed_to],
            replanned=False,
            cache_level=None,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        ),
    )

    _log_decision(req, body)

    payload = body.model_dump()
    if settings.strict_contract:
        payload.pop("response", None)
        payload.pop("meta", None)
    return JSONResponse(content=payload, status_code=200)


def _log_decision(req: RouteRequest, resp: RouteResponse) -> None:
    conn = get_ops_conn()
    conn.execute(
        """INSERT OR REPLACE INTO route_log
           (request_id, ts, query, complexity_hint, complexity, complexity_prob, user_scope,
            dry_run, routed_to, reasoning, latency_ms, estimated_cost, tokens_in, tokens_out,
            cache_level, replanned, candidates_json, snapshot_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            req.request_id,
            datetime.now(UTC).isoformat(),
            req.query,
            req.complexity_hint,
            resp.meta.complexity,
            resp.meta.complexity_prob,
            req.user_scope,
            int(req.dry_run),
            resp.routed_to,
            resp.reasoning,
            resp.latency_ms,
            resp.estimated_cost,
            resp.meta.tokens_in,
            resp.meta.tokens_out,
            resp.meta.cache_level,
            int(resp.meta.replanned),
            ",".join(resp.meta.candidates),
            None,
        ),
    )
    conn.commit()


@app.post("/api/v1/admin/simulate")
async def admin_simulate(req: SimulateRequest) -> dict:
    monitor = app.state.monitor
    if req.mode == "live":
        monitor.clear_overrides()
    else:
        monitor.set_manual(
            ram_available_mb=req.ram_available_mb,
            bandwidth_kbps=req.bandwidth_kbps,
            api_quota_remaining=req.api_quota_remaining,
            cpu_load_pct=req.cpu_load_pct,
        )
    note = None
    if req.mode == "scenario":
        note = "scenario CSV replay lands in M3; overrides applied manually for now"
    return {"ok": True, "mode": req.mode, "note": note}


@app.get("/api/v1/admin/decisions", response_model=list[DecisionLogEntry])
async def admin_decisions(since: str | None = Query(default=None), limit: int = Query(default=50)) -> list[DecisionLogEntry]:
    conn = get_ops_conn()
    if since:
        rows = conn.execute(
            "SELECT * FROM route_log WHERE ts >= ? ORDER BY ts DESC LIMIT ?", (since, limit)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM route_log ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    return [
        DecisionLogEntry(
            request_id=r["request_id"],
            ts=r["ts"],
            query=r["query"],
            routed_to=r["routed_to"],
            reasoning=r["reasoning"],
            latency_ms=r["latency_ms"],
            estimated_cost=r["estimated_cost"],
        )
        for r in rows
    ]
