PYTHON ?= .venv/bin/python

.PHONY: install-dev test lint typecheck ci

install-dev:
	$(PYTHON) -m pip install -r requirements.txt -r requirements-dev.txt

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .

typecheck:
	$(PYTHON) -m mypy alphabet main.py

ci: lint typecheck test
