# Project Gaps and Missing Pieces

## 1. Pass/Endgame Rules (Completed)

- Completed:
  - Explicit `pass_turn()` support.
  - Consecutive-pass termination (`2` passes ends the game).
  - No-move selection returns `None` and the main loop treats it as a pass.
  - Endgame rack penalties/bonuses are applied when game ends.

## 2. Scoring Rules Completeness (Completed)

- Completed:
  - 50-point bingo bonus when a move uses all rack tiles.
  - Endgame score adjustments implemented:
    - Tile-out with empty bag: finisher gains opponent rack remainder, opponent loses it.
    - Pass/round-limit ending: each player loses own rack remainder.

## 3. Move Generation Validation and Performance (Completed)

- Completed:
  - Added move deduplication in `all_valid_moves_codex` output.
  - Added regression tests to ensure:
    - generated move sets do not contain duplicate placements,
    - engine-selected moves remain legal across multiple real-game turns.

## 4. Missing Move Types (Completed)

- Completed:
  - Added explicit `ExchangeMove` and `PassMove` action types.
  - Added `Game.apply_action(...)` to handle `Move`, `ExchangeMove`, and `PassMove`.
  - Added `Game.exchange(...)` and `Game.can_exchange(...)`.
  - Updated engine selection to return explicit actions (`select_action`), with:
    - random legal word move if available,
    - otherwise exchange when possible,
    - otherwise pass.

## 5. Core Logic Structure (Completed)

- Completed:
  - Centralized generated-word extraction into `_words_formed_positions(...)`.
  - Reused shared word extraction in both legality validation and scoring paths.
  - Reduced duplicate per-axis/per-word traversal logic between `is_legal` and `score_move`.

## 6. Test Coverage Depth (Completed)

- Completed:
  - Added deterministic multi-turn engine action-flow regression test.
  - Added explicit tests for:
    - no-move exchange fallback,
    - no-move pass fallback,
    - exchange action mechanics/invariants.
  - Existing wildcard/modifier/crossword scoring tests retained and expanded.

## 7. CLI/Runtime UX (Completed)

- Completed:
  - Added `--quiet` mode to suppress board rendering and turn-by-turn verbosity.
  - Added `--seed` for deterministic runs (`numpy` RNG seed).
  - Added `--benchmark` mode with end-of-run timing summary.

## 8. Tooling and Dev Workflow (Completed)

- Completed:
  - Added `requirements-dev.txt` (`pytest`, `ruff`, `mypy`).
  - Added `pyproject.toml` config for pytest/ruff/mypy.
  - Expanded `Makefile` with `install-dev`, `lint`, `typecheck`, and `ci` targets.
  - Added GitHub Actions workflow at `.github/workflows/ci.yml`.

## 9. Move Selection Strategy (Completed)

- Completed:
  - Replaced random move choice with deterministic best-immediate-score selection.
  - Tie-breakers now prefer:
    - higher tile usage,
    - stable placement ordering for deterministic behavior.
  - Added tests asserting higher-scoring move preference.

## 10. Documentation Depth (Completed)

- Completed:
  - Added a formal rules and invariants spec in `RULES_SPEC.md`.
  - Documented:
    - action model (`Move`, `ExchangeMove`, `PassMove`),
    - legality invariants,
    - scoring behavior (multipliers, cross-words, wildcard handling, bingo),
    - endgame adjustments,
    - exchange constraints,
    - deterministic/testing expectations.
