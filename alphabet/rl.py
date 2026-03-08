from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from alphabet.encoding import ActionEncoder, ENCODER_SCHEMA_VERSION, StateEncoder
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

MODEL_SCHEMA_VERSION = "rl_linear_v1"


@dataclass
class LinearPolicyModel:
    weights: Dict[str, float]
    bias: float = 0.0
    feature_schema_version: str = ENCODER_SCHEMA_VERSION
    model_schema_version: str = MODEL_SCHEMA_VERSION

    @classmethod
    def default(cls) -> "LinearPolicyModel":
        return cls(
            weights={key: 0.0 for key in FEATURE_KEYS},
            bias=0.0,
            feature_schema_version=ENCODER_SCHEMA_VERSION,
            model_schema_version=MODEL_SCHEMA_VERSION,
        )

    @classmethod
    def load(cls, path: str | Path) -> "LinearPolicyModel":
        payload = json.loads(Path(path).read_text())
        feature_schema_version = payload.get("feature_schema_version", "")
        model_schema_version = payload.get("model_schema_version", "")
        if feature_schema_version != ENCODER_SCHEMA_VERSION:
            raise ValueError(
                f"Model feature schema '{feature_schema_version}' != expected '{ENCODER_SCHEMA_VERSION}'"
            )
        if model_schema_version != MODEL_SCHEMA_VERSION:
            raise ValueError(
                f"Model schema '{model_schema_version}' != expected '{MODEL_SCHEMA_VERSION}'"
            )
        raw_weights = payload.get("weights", {})
        weights = {key: float(raw_weights.get(key, 0.0)) for key in FEATURE_KEYS}
        bias = float(payload.get("bias", 0.0))
        return cls(
            weights=weights,
            bias=bias,
            feature_schema_version=feature_schema_version,
            model_schema_version=model_schema_version,
        )

    def save(self, path: str | Path) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "weights": {key: float(self.weights.get(key, 0.0)) for key in FEATURE_KEYS},
            "bias": float(self.bias),
            "feature_schema_version": self.feature_schema_version,
            "model_schema_version": self.model_schema_version,
        }
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def score(self, features: Dict[str, float]) -> float:
        total = self.bias
        for key in FEATURE_KEYS:
            total += self.weights.get(key, 0.0) * features.get(key, 0.0)
        return total

    def update(self, features: Dict[str, float], target: float, alpha: float) -> None:
        if not math.isfinite(target) or not math.isfinite(alpha):
            return
        prediction = self.score(features)
        error = target - prediction
        if not math.isfinite(error):
            return
        self.bias += alpha * error
        for key in FEATURE_KEYS:
            self.weights[key] = self.weights.get(key, 0.0) + alpha * error * features.get(key, 0.0)
            if not math.isfinite(self.weights[key]):
                self.weights[key] = 0.0
        if not math.isfinite(self.bias):
            self.bias = 0.0


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
        self.state_encoder = StateEncoder()
        self.action_encoder = ActionEncoder()

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
        self.state_encoder.encode(game, player)
        encoded = self.action_encoder.encode(game, player, move)

        return {
            "immediate_score": float(encoded.immediate_score),
            "tiles_used": float(encoded.tiles_used),
            "rack_leave": float(encoded.leave_size),
            "leave_vowels": float(encoded.leave_vowels),
            "leave_consonants": float(encoded.leave_consonants),
            "leave_balance": float(-encoded.leave_balance),
            "is_bingo": float(encoded.is_bingo),
        }


def margin_reward(game: Game) -> float:
    margin = game.players.a.score - game.players.b.score
    # Clamp reward smoothly to [-1, 1] while keeping large-margin signal.
    return math.tanh(margin / 100.0)
