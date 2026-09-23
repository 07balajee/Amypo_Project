# AMYPO Unified Platform — HackWithAMYPO 2026

One platform, two problem statements:

- **PS1 — Low-Cost AI Request Router**: routes each request to `local_model | cloud_api | cache | offline_fallback`.
- **PS7 — Local Database Question-Answering**: answers questions over course content, FAQs, policies and
  structured academic/placement records, with a cited source on every answer.

PS7's generation step calls PS1's `/route`, so the two problem statements share one running system. Full
design rationale, API contracts, and build order live in [CLAUDE.md](CLAUDE.md) — this file is the quick-start.

## Quick start

```bash
docker compose up            # full stack (router + qa + dashboard + inference tiers)
```

`.env` sets `COMPOSE_PROFILES=router,qa` so the bare command above brings up everything. For an isolated
single-PS submission, override the env var itself (a bare `--profile` flag unions with it rather than
replacing it):

```bash
COMPOSE_PROFILES=router docker compose up   # PS1 only
COMPOSE_PROFILES=qa docker compose up       # PS7 only
```

Then:
- Router API: http://localhost:8000/api/v1/health
- Q&A API: http://localhost:8001/api/v1/health
- Dashboard: http://localhost:8501

## Local development (without Docker)

```bash
make venv        # creates .venv, installs everything (pip install -e ".[all]")
make test         # pytest, no model weights needed (MockGateway)
make lint         # ruff
make synth        # generate data/synthetic/* (M1)
make ingest       # index documents + load structured records (M4/M6)
make eval         # router + qa evaluation reports (M8)
```

All tests run against `MockGateway` (`app/core/inference/mock.py`) — no llama.cpp weights required,
so `make test` stays fast and fully offline.

## Current status: M0 (skeleton)

Repo layout, config, DB schemas, both FastAPI apps with contract-matching stub endpoints, MockGateway,
compose file and Makefile are in place. Decision logic is currently a stub (`/route` always chooses
`local_model`; `/ask` always abstains) — see [CLAUDE.md §14](CLAUDE.md#14-build-order-milestones--finish-and-verify-each-before-the-next)
for the milestone plan that fills these in (M1 synthetic data → M2 real model containers → M3 router →
M4/M6 Q&A → M7 dashboard → M8 eval).

`inference` and `remote-tier` currently run `scripts/inference_stub_server.py`, a placeholder that speaks
the same `/health` + `/v1/chat/completions` shape as the real llama.cpp server. M2 replaces it with
`ghcr.io/ggml-org/llama.cpp:server` + baked GGUF weights (Qwen2.5-1.5B-Instruct local,
Llama-3.2-3B-Instruct remote).

## API contracts

Exact request/response shapes: [CLAUDE.md §6](CLAUDE.md#6-api-contracts-exact). Machine-readable spec:
[openapi.yaml](openapi.yaml) (regenerate with `python scripts/export_openapi.py` after any route/schema
change — a contract test fails CI if it drifts).

## Hard constraints

No third-party/paid APIs at runtime, fully offline (`network_mode`/no-egress capable — see
`docker-compose.offline.yml`), 8 GB RAM budget, one-command startup, frozen API contracts, every PS7
answer cites a real `record_id` or abstains, the LLM never writes SQL. Full list: [CLAUDE.md §1](CLAUDE.md#1-hard-constraints-never-violate).
