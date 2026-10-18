.PHONY: up down install test schema seed eval demo
PY := .venv/bin/python

install:
	test -d .venv || python3 -m venv .venv
	$(PY) -m pip install --quiet -e ".[dev]"

up:
	docker compose up -d falkordb

down:
	docker compose down

test: install up
	$(PY) -m pytest -q

schema: install up
	$(PY) -m causeway.graph.schema

seed: schema
	$(PY) -m causeway.data.loader 42

eval: install up
	$(PY) -m eval.run_eval

demo: seed
	@echo "Open http://127.0.0.1:8000"
	$(PY) -m causeway.api
