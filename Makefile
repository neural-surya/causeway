.PHONY: up down install test schema
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
