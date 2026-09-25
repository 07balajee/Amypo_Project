# AMYPO Local AI Platform

A self-hosted AI platform that runs fully offline on a single machine with 8 GB of RAM. It combines two services:

- **AI Request Router**: decides where each AI request should run (a local model, a larger "remote" model, the
  cache or an offline fallback) based on how complex the request is and what resources are available right now.
- **Question-Answering over local data**: answers questions about courses, FAQs, policies and
  academic/placement records. Every answer cites the record it came from, or the service says it doesn't know.

The Q&A service sends its generation step through the router, so every answer takes the cheapest path that
still meets the quality it needs.

## How it works

```
Clients / Dashboard chat
   ├── Router API (:8000)
   │     Complexity scorer → Decision engine → Resource monitor
   │                                          → Cache (exact + semantic)
   │                                          → Local model / Remote model (llama.cpp)
   │                                          → Offline fallback (no LLM)
   └── Q&A API (:8001)
         Intent classifier → Structured path (SQL templates: records, eligibility, matching, skill gap)
                           → Document path (BM25 + vector search → grounded prompt → Router)
                           → Citation check + confidence → answer
```

### Router

- **Complexity scoring**: a lightweight classifier labels each request low, medium or high using features
  such as length, question type, code and math content. It makes no model calls.
- **Resource-aware decisions**: it samples RAM, CPU, bandwidth and remaining quota every second. Each route
  is scored on cost, latency and expected quality, and the best feasible option wins.
- **Explainable**: every decision includes reasoning that quotes the actual numbers, e.g.
  *"bandwidth 48 kbps < 64 kbps floor → cloud_api infeasible"*.
- **Resilient**: timeouts, one re-plan on failure, a circuit breaker on the remote tier and an offline
  fallback that never makes up an answer.
- **Remote tier**: `cloud_api` is a second, larger self-hosted model. It is metered like a paid API
  (per-token price, quota and simulated network latency), so no external provider is ever called.

### Question-Answering

- **Structured questions** (grades, attendance, placement eligibility, student–company matching, skill gaps)
  are answered with fixed, parameterised SQL templates. The LLM never writes SQL.
- **Document questions** use hybrid retrieval (BM25 and vector search, fused with Reciprocal Rank Fusion).
  The model must cite a source for every sentence.
- **Verification**: a sentence is dropped if its citation doesn't back it up or if it has numbers that
  aren't in the source. If nothing is left, the service returns *"I couldn't find this in AMYPO's records."*
- **Access control**: students can see only their own records; staff can see everyone's.

## Tech stack

Python 3.11, FastAPI, pydantic, MySQL 8 (PyMySQL), ChromaDB, rank-bm25, sentence-transformers (all-MiniLM-L6-v2),
scikit-learn, llama.cpp (Qwen2.5-1.5B-Instruct locally, Llama-3.2-3B-Instruct as the remote tier) and a
Streamlit dashboard. Everything runs CPU-only in Docker.

## Quick start

```bash
docker compose up
```

- Router API: http://localhost:8000/api/v1/health
- Q&A API: http://localhost:8001/api/v1/health
- Dashboard: http://localhost:8501

To run one service on its own:

```bash
COMPOSE_PROFILES=router,mysql docker compose up   # router only
COMPOSE_PROFILES=qa,mysql docker compose up       # Q&A (includes the router)
```

### Database

The services use MySQL. `docker compose up` starts a bundled MySQL 8 container, which is reachable from the
host on port 3307. To use a MySQL server installed on your PC instead, edit `.env`: remove `mysql` from
`COMPOSE_PROFILES` and set `DB_HOST=host.docker.internal`, `DB_USER` and `DB_PASSWORD`. When running
without Docker, set `DB__MYSQL__HOST`, `DB__MYSQL__USER` and `DB__MYSQL__PASSWORD`. The services create the
`amypo_ops` and `amypo` databases and their tables on startup if the user has permission. Schemas live in
`app/core/db/mysql/`.

The test suite uses SQLite (`app/core/db/sqlite/`) instead, so `make test` needs no database server.

To test offline with all network access blocked, add the `docker-compose.offline.yml` override.

## Local development

```bash
make venv     # create .venv and install dependencies
make test     # run tests (no model weights needed; uses a mock gateway)
make lint     # ruff
make synth    # generate synthetic data into data/synthetic/
make ingest   # index documents and load structured records
make eval     # run router and Q&A evaluations
```

## Data

Until the real data arrives, the platform runs on **synthetic** data in [data/synthetic/](data/synthetic/):
course syllabi, an FAQ, policies (as markdown, PDF and DOCX), 200 students with grades, attendance and
skills, placement criteria for 10 companies, and the training and evaluation sets (router prompts,
resource scenarios, Q&A benchmark, past queries).

```bash
python scripts/gen_synthetic.py                              # regenerate data/synthetic (seeded)
python -m app.ingest.cli --db-url mysql://user:pass@host:3306/amypo   # load everything into MySQL
```

You can pass the connection string with `--db-url` or set `DB__MYSQL__URL`. Using the environment
variable keeps the password out of your shell history. Loading is a full refresh, so it's safe to re-run.

**Switching to the real data** means implementing
[app/ingest/adapters/amypo.py](app/ingest/adapters/amypo.py) (it has a mapping checklist), setting
`data.adapter: amypo` in `config.yaml`, and re-running the ingest command. Nothing else changes.

## Main endpoints

| Service | Endpoint | Purpose |
|---|---|---|
| Router | `POST /api/v1/route` | Route and run an AI request |
| Router | `GET /api/v1/resource-status` | Current RAM, CPU, bandwidth and quota |
| Q&A | `POST /api/v1/ask` | Ask a question and get a cited answer |
| Both | `GET /api/v1/health` | Service health |

The full spec is in [openapi.yaml](openapi.yaml).

## Project layout

```
app/core/        shared config, inference gateway, cache, resource monitor, DB schemas
app/router/      routing service
app/qa/          question-answering service
app/ingest/      data loaders and parsers (behind swappable adapters)
app/dashboard/   Streamlit dashboard
app/eval/        benchmarks and reports
data/synthetic/  generated sample data
tests/           unit, contract, scenario and adversarial tests
```

## Status

Early stage: the service skeleton, API contracts, config and database schemas are done. Routing and
answering logic is still stubbed.
