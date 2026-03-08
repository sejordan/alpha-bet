PYTHON ?= .venv/bin/python

.PHONY: install-dev hooks test lint typecheck ci

install-dev:
	$(PYTHON) -m pip install -r requirements.txt -r requirements-dev.txt

hooks:
	$(PYTHON) -m pre_commit install

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .

typecheck:
	$(PYTHON) -m mypy alphabet main.py train_rl.py webapp/app.py

ci: lint typecheck test
