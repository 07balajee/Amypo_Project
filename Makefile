.PHONY: venv up up-router up-qa down build test lint synth ingest eval eval-router eval-qa offline-test clean

PYTHON ?= python3
VENV   := .venv
PY     := $(VENV)/bin/python

venv:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -e ".[all]"

up:
	docker compose up --build

up-router:
	COMPOSE_PROFILES=router,mysql docker compose up --build

up-qa:
	COMPOSE_PROFILES=qa,mysql docker compose up --build

down:
	docker compose down

build:
	docker compose build

test:
	$(PY) -m pytest -q

lint:
	$(VENV)/bin/ruff check app tests scripts

synth:
	$(PY) scripts/gen_synthetic.py

ingest:
	$(PY) -m app.ingest.cli

eval: eval-router eval-qa

eval-router:
	$(PY) -m app.eval.run_router_eval

eval-qa:
	$(PY) -m app.eval.run_qa_eval

offline-test:
	docker compose -f docker-compose.yml -f docker-compose.offline.yml up --build --abort-on-container-exit

clean:
	docker compose down -v
	rm -rf $${DB__SQLITE__DIR:-$$HOME/.amypo/db}/ops.db* $${DB__SQLITE__DIR:-$$HOME/.amypo/db}/amypo.db*
