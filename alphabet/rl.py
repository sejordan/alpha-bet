from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from alphabet.board import Tile
from alphabet.game import Game, Player
from alphabet.move import ExchangeMove, Move, PassMove
from alphabet.strategy import ActionStrategy


FEATURE_KEYS = (
    "immediate_score",
    "tiles_used",
    "rack_leave",
    "leave_vowels",
    "leave_consonants",
    "leave_balance",
    "is_bingo",
)

VOWELS = {"a", "e", "i", "o", "u"}


@dataclass
class LinearPolicyModel:
    weights: Dict[str, float]
    bias: float = 0.0

    @classmethod
    def default(cls) -> "LinearPolicyModel":
        return cls(weights={key: 0.0 for key in FEATURE_KEYS}, bias=0.0)

    @classmethod
    def load(cls, path: str | Path) -> "LinearPolicyModel":
        payload = json.loads(Path(path).read_text())
        raw_weights = payload.get("weights", {})
        weights = {key: float(raw_weights.get(key, 0.0)) for key in FEATURE_KEYS}
        bias = float(payload.get("bias", 0.0))
        return cls(weights=weights, bias=bias)

    def save(self, path: str | Path) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "weights": {key: float(self.weights.get(key, 0.0)) for key in FEATURE_KEYS},
            "bias": float(self.bias),
        }
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def score(self, features: Dict[str, float]) -> float:
        total = self.bias
        for key in FEATURE_KEYS:
            total += self.weights.get(key, 0.0) * features.get(key, 0.0)
        return total

    def update(self, features: Dict[str, float], target: float, alpha: float) -> None:
        prediction = self.score(features)
        error = target - prediction
        self.bias += alpha * error
        for key in FEATURE_KEYS:
            self.weights[key] = self.weights.get(key, 0.0) + alpha * error * features.get(key, 0.0)


class RLLinearStrategy(ActionStrategy):
    def __init__(
        self,
        model: LinearPolicyModel | None = None,
        epsilon: float = 0.05,
        rng: random.Random | None = None,
    ) -> None:
        self.model = model if model is not None else LinearPolicyModel.default()
        self.epsilon = epsilon
        self.rng = rng if rng is not None else random.Random()

    def select_action(
        self,
        engine,
        game: Game,
        player: Player,
        candidates: List[Move],
    ) -> Move | ExchangeMove | PassMove:
        if len(candidates) == 0:
            exchange_count = min(len(player.tiles), game.bag.total_tiles)
            if exchange_count > 0:
                return ExchangeMove(player.tiles[:exchange_count])
            return PassMove()

        if self.epsilon > 0 and self.rng.random() < self.epsilon:
            return self.rng.choice(candidates)

        best_move: Move | None = None
        best_score: float | None = None
        best_sig: Tuple | None = None

        for move in candidates:
            features = self.move_features(game, player, move)
            model_score = self.model.score(features)
            move_sig = tuple(engine._move_signature_codex(move))  # pylint: disable=protected-access

            if best_score is None or model_score > best_score:
                best_score = model_score
                best_sig = move_sig
                best_move = move
                continue

            if model_score == best_score and (best_sig is None or move_sig < best_sig):
                best_sig = move_sig
                best_move = move

        assert best_move is not None
        return best_move

    def move_features(self, game: Game, player: Player, move: Move) -> Dict[str, float]:
        immediate_score = float(game.score_move(move))
        tiles_used = float(len(move.placements))

        remaining_tiles = _rack_after_move(player.tiles, move)
        leave_vowels = 0.0
        leave_consonants = 0.0
        for tile in remaining_tiles:
            if tile.wildcard:
                continue
            if tile.letter in VOWELS:
                leave_vowels += 1.0
            else:
                leave_consonants += 1.0

        leave_balance = -abs(leave_vowels - leave_consonants)

        return {
            "immediate_score": immediate_score,
            "tiles_used": tiles_used,
            "rack_leave": float(len(remaining_tiles)),
            "leave_vowels": leave_vowels,
            "leave_consonants": leave_consonants,
            "leave_balance": leave_balance,
            "is_bingo": 1.0 if len(move.placements) == game.variant.starting_tiles else 0.0,
        }


def _rack_after_move(rack: Iterable[Tile], move: Move) -> List[Tile]:
    remaining = list(rack)
    for placement in move.placements:
        target_tile = placement.tile
        for index, tile in enumerate(remaining):
            if tile is target_tile:
                remaining.pop(index)
                break

            # Fallback for copied tile objects in generated moves.
            if tile.wildcard == target_tile.wildcard and tile.letter == target_tile.letter:
                remaining.pop(index)
                break
    return remaining


def margin_reward(game: Game) -> float:
    margin = game.players.a.score - game.players.b.score
    # Clamp reward smoothly to [-1, 1] while keeping large-margin signal.
    return math.tanh(margin / 100.0)
