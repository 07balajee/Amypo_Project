"""Q&A service — POST /api/v1/ask, GET /api/v1/health, POST /api/v1/admin/reindex.
M0 scope: skeleton + a contract-correct stub that always abstains (hard constraint #6: never
return an uncited factual answer). Classification, retrieval, SQL templates, grounding and
verification land in M4/M6; each will replace the abstain-only branch in `ask()` below.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.db.conn import get_amypo_conn, get_ops_conn
from app.qa.schemas import AskRequest, AskResponse, abstain_response

SERVICE_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = get_settings()
    get_ops_conn().close()  # applies schemas on startup
    get_amypo_conn().close()
    yield


app = FastAPI(title="Local DB Q&A", version=SERVICE_VERSION, lifespan=lifespan)


@app.get("/api/v1/health")
async def health() -> JSONResponse:
    components = {"amypo_db": "ok", "ops_db": "ok"}
    body = {"status": "ok", "components": components, "version": SERVICE_VERSION}
    return JSONResponse(content=body, status_code=200)


@app.post("/api/v1/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    resp = abstain_response(intent="out_of_scope")
    _log_ask(req, resp)
    return resp


def _log_ask(req: AskRequest, resp: AskResponse) -> None:
    with get_ops_conn() as conn:
        conn.execute(
            """INSERT INTO qa_log
               (ts, user_id, conversation_id, question, intent, path, answer, confidence, abstained,
                route_request_id, sources_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(UTC).isoformat(),
                req.user_id,
                req.conversation_id,
                req.question,
                resp.meta.intent,
                resp.meta.path,
                resp.answer,
                resp.confidence,
                int(resp.meta.abstained),
                resp.meta.route_request_id,
                "[]",
            ),
        )


@app.post("/api/v1/admin/reindex")
async def admin_reindex() -> dict:
    return {"ok": True, "note": "ingestion + indexing pipeline lands in M4/M6"}
