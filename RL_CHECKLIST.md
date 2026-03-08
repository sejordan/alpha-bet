# RL Path Checklist

## 1. Environment and Baselines
- [x] Freeze a deterministic simulation setup (dictionary, seed handling, variant, max rounds).
- [x] Define baseline opponents (`greedy`, `random`, `exchange/pass-safe`) for comparison.
- [x] Add reproducible benchmark script for win rate, score margin, and game length.

## 2. State and Action Representation
- [x] Define canonical state encoder (board premiums, occupied letters, rack, bag estimate, turn context).
- [x] Define action encoder for candidate moves (placements, score, leave, cross-word impact).
- [x] Add feature versioning so saved models are tied to encoder schema.

## 3. Data Collection Pipeline
- [x] Build self-play rollout runner that logs `(state, action, reward, next_state, done)` transitions.
- [x] Store trajectories in an on-disk dataset format (JSONL/Parquet) with metadata.
- [x] Add sampling controls (episodes, seed sweeps, opponent mix).

## 4. Learning Algorithm (Incremental)
- [x] Start with improved linear TD/Monte Carlo update with temporal credit assignment.
- [x] Add checkpointing cadence and resumable training.
- [x] Track training metrics per checkpoint (loss proxy, reward trend, policy entropy).
- [x] Evaluate moving to function approximation model (small MLP) if linear plateaus.

## 5. Evaluation Harness
- [x] Add head-to-head tournament runner across checkpoints and baselines.
- [x] Compute and persist metrics: win rate, average margin, regret vs best immediate move.
- [x] Add acceptance gates (e.g., RL must beat greedy by target win rate over N games).
- [x] Produce evaluation report markdown artifact per run.

## 6. Strategy Integration
- [x] Add `StrategyFactory` for clean runtime selection (`greedy`, `rl_linear`, future `rl_nn`).
- [x] Add robust model load errors and fallback behavior in CLI/webapp.
- [x] Add config surface for inference knobs (epsilon=0 by default for competitive play).

## 7. Human Play Integration
- [x] Let play-vs-AI choose a trained checkpoint from UI (dropdown/file input with validation).
- [x] Show AI reasoning summary per move (top candidates and model scores).
- [x] Add optional post-game analysis comparing human move vs model top-K.

## 8. Training Safety and Correctness
- [x] Add invariants test suite for rollout legality and game-state consistency.
- [x] Add guardrails for NaN/inf weights and unstable updates.
- [x] Add deterministic regression test for checkpoint load -> identical action selection.

## 9. Ops and Workflow
- [x] Add `make train-rl`, `make eval-rl`, `make report-rl` targets.
- [x] Add experiment folder layout (`models/`, `runs/`, `reports/`) and retention rules.
- [x] Add docs for end-to-end workflow: train -> evaluate -> promote model.

## 10. Promotion Criteria to "Fully Functional"
- [x] One-command training run produces checkpoint and metrics artifact.
- [x] One-command evaluation run compares against baselines with pass/fail gates.
- [x] Play-vs-AI can load promoted model and complete full games without errors.
- [x] CI includes RL smoke tests (short train + short eval) behind a fast profile.
- [x] Documentation covers operational usage and known limitations.
