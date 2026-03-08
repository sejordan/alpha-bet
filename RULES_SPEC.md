# Rules and Invariants Specification

This document defines the current rule behavior implemented in `alpha-bet`.
It is intended as a refactor safety spec for legality, scoring, and turn flow.

## 1. Turn and Action Model

Each turn applies exactly one action:

- `Move`: place one or more tiles on the board.
- `ExchangeMove`: return selected rack tiles to the bag and draw the same count.
- `PassMove`: make no board change and no score change.

Engine selection order:

1. Choose best legal `Move` if at least one exists.
2. Otherwise choose `ExchangeMove` if exchange is possible.
3. Otherwise choose `PassMove`.

## 2. Game End Conditions

The game ends when any of these are true:

- `round > max_rounds`
- `consecutive_passes >= 2`
- bag is empty and either player has no tiles left (tile-out)

Endgame score adjustments are applied once at game end.

## 3. Move Legality Rules (`Game.is_legal`)

A `Move` is legal iff all of the following hold:

1. Has at least one placement.
2. Every placement position is in bounds.
3. Every placement position is currently empty.
4. No duplicate placement positions.
5. Any wildcard tile is assigned a concrete letter before placement.
6. Active player owns every tile used by placements.
7. Placements are on a single axis (single row or single column).
8. Move is contiguous along that axis when including existing board tiles.
9. Opening move (`round == 1 and turn == 1`) crosses center square.
10. Non-opening move touches the existing board graph.
11. All formed words are valid dictionary words:
   - main word length must be > 1
   - each cross-word of length > 1 must be valid

## 4. Scoring Rules (`Game.score_move`)

Scoring is per action `Move` and sums all words formed:

- Main word formed by placements.
- All cross-words formed by each newly placed tile.

Per-word scoring:

- Existing board tiles contribute face value only.
- Newly placed tiles:
  - apply letter multiplier (`2L`, `3L`) to that tile only.
  - contribute to word multiplier (`2W`, `3W`) multiplicatively.
- Multipliers are applied only on newly placed tiles.

Wildcard scoring:

- Wildcards always score `0` face value, even after letter assignment.

Bingo:

- If a move places exactly `variant.starting_tiles` tiles, add `+50`.

## 5. Endgame Score Adjustments

When game ends, apply exactly once:

Tile-out with empty bag:

- If Player A emptied rack:
  - Player A gains sum of Player B rack tile values.
  - Player B loses that same amount.
- If Player B emptied rack:
  - symmetric behavior.

Pass/round-limit ending (no tile-out):

- Each player loses sum of their own remaining rack tile values.

## 6. Exchange Rules

`ExchangeMove` is legal iff:

1. At least one tile is requested.
2. Bag has at least as many tiles as requested.
3. Active player owns all exchanged tiles.

Exchange effects:

- `consecutive_passes += 1`
- exchanged tiles removed from player rack and returned to bag
- same number of tiles drawn from bag
- no board change
- no direct score change

## 7. Determinism and Testing Expectations

- `main.py --seed N` must make runs reproducible for the same code + dictionary.
- `make ci` must pass:
  - `ruff`
  - `mypy`
  - `pytest`

This spec is the source of truth for future legality/scoring refactors.
