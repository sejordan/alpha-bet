# RL Workflow

## Directories and Retention
- `models/`: promoted or checkpointed policy files (`.json`).
- `runs/`: training/evaluation raw metrics and rollout data.
- `reports/`: markdown summaries intended for review.

Retention guidance:
- Keep only promoted models plus periodic checkpoints (e.g., every 1000 episodes).
- Keep at most the last 10 run folders under `runs/train` and `runs/eval`.
- Keep reports for promoted runs and latest failed gate run.

## Train
One command:
```bash
make train-rl
```
Outputs:
- `models/rl_linear.json`
- `runs/train/latest_metrics.json`
- checkpoint files under `runs/train/latest/checkpoints/`

## Collect Rollouts
```bash
make collect-rollouts
```
Outputs:
- `runs/rollouts/latest.jsonl`
- `runs/rollouts/latest.jsonl.meta.json`

## Evaluate
One command:
```bash
make eval-rl
```
Outputs:
- `runs/eval/latest_metrics.json`
- `reports/rl_eval_latest.md`
- pass/fail gates against greedy baseline.

## Promote
Promote a model only when:
- Evaluation gate passes.
- No regressions in `make ci`.
- Quick play-vs-AI smoke game completes without errors using that model.

## Run Model in CLI
```bash
.venv/bin/python main.py --strategy rl --model-path models/rl_linear.json --epsilon 0 --quiet
```

## Run Model in Web App
- Start app: `.venv/bin/python webapp/app.py`
- In `Play vs AI`, choose strategy `RL Model` and select `models/rl_linear.json`.

## Known Limitations
- Current learner is linear and may plateau on strategic depth.
- Reward is still game-outcome oriented; no neural value/policy model yet.
- Training throughput is bounded by full move generation cost.
