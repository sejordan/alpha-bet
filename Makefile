PYTHON ?= .venv/bin/python
RL_EPISODES ?= 100
RL_EVAL_GAMES ?= 20

.PHONY: install-dev hooks test lint typecheck ci benchmark collect-rollouts train-rl eval-rl report-rl rl-smoke

install-dev:
	$(PYTHON) -m pip install -r requirements.txt -r requirements-dev.txt

hooks:
	$(PYTHON) -m pre_commit install

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .

typecheck:
	$(PYTHON) -m mypy alphabet main.py train_rl.py collect_rollouts.py eval_rl.py benchmark_strategies.py webapp/app.py

ci: lint typecheck test

benchmark:
	$(PYTHON) benchmark_strategies.py

collect-rollouts:
	$(PYTHON) collect_rollouts.py

train-rl:
	$(PYTHON) train_rl.py --episodes $(RL_EPISODES) --report-every 20 --checkpoint-every 25 --model-out models/rl_linear.json --metrics-out runs/train/latest_metrics.json --run-dir runs/train/latest

eval-rl:
	$(PYTHON) eval_rl.py --checkpoint models/rl_linear.json --games $(RL_EVAL_GAMES) --metrics-out runs/eval/latest_metrics.json --report-out reports/rl_eval_latest.md

report-rl:
	@echo "Evaluation report: reports/rl_eval_latest.md"
	@cat reports/rl_eval_latest.md

rl-smoke:
	$(PYTHON) train_rl.py --episodes 2 --report-every 1 --checkpoint-every 1 --seed 1 --model-out models/rl_smoke.json --metrics-out runs/train/smoke_metrics.json --run-dir runs/train/smoke
	$(PYTHON) eval_rl.py --checkpoint models/rl_smoke.json --games 2 --seed 1 --metrics-out runs/eval/smoke_metrics.json --report-out reports/rl_eval_smoke.md
