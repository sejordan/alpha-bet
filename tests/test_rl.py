import json
from pathlib import Path

import pytest

from alphabet.engine import GameEngine
from alphabet.game import Game
from alphabet.move import ExchangeMove, Move, PassMove
from alphabet.rl import ENCODER_SCHEMA_VERSION, MODEL_SCHEMA_VERSION, LinearPolicyModel, RLLinearStrategy
from alphabet.wordsmith import Dictionary


def _game(words: list[str]) -> Game:
    return Game(Dictionary(words))


def _set_rack(game: Game, letters: list[str]) -> None:
    game.players.a.tiles = []
    game.players.b.tiles = []
    game.active_player.tiles = [game.bag.build_tile(letter) for letter in letters]


def test_rl_strategy_prefers_higher_scoring_move_when_weighted_for_score() -> None:
    game = _game(["at", "cat"])
    game.round = 1
    game.turn = 1
    _set_rack(game, ["c", "a", "t"])

    engine = GameEngine()
    candidates = engine.all_valid_moves_codex(game, game.active_player)

    model = LinearPolicyModel.default()
    model.weights["immediate_score"] = 1.0
    strategy = RLLinearStrategy(model=model, epsilon=0.0)

    action = strategy.select_action(engine=engine, game=game, player=game.active_player, candidates=candidates)
    assert isinstance(action, Move)

    best_score = max(game.score_move(move) for move in candidates)
    assert game.score_move(action) == best_score


def test_rl_strategy_fallbacks_exchange_then_pass() -> None:
    game = _game(["at"])
    game.round = 1
    game.turn = 1
    _set_rack(game, ["z"])

    engine = GameEngine()
    strategy = RLLinearStrategy(model=LinearPolicyModel.default(), epsilon=0.0)

    action = strategy.select_action(engine=engine, game=game, player=game.active_player, candidates=[])
    assert isinstance(action, ExchangeMove)

    game.bag.total_tiles = 0
    action = strategy.select_action(engine=engine, game=game, player=game.active_player, candidates=[])
    assert isinstance(action, PassMove)


def test_linear_policy_model_save_load_roundtrip(tmp_path: Path) -> None:
    model = LinearPolicyModel.default()
    model.weights["immediate_score"] = 0.75
    model.weights["leave_balance"] = -0.2
    model.bias = 0.1

    output = tmp_path / "model.json"
    model.save(output)
    restored = LinearPolicyModel.load(output)

    assert restored.bias == 0.1
    assert restored.weights["immediate_score"] == 0.75
    assert restored.weights["leave_balance"] == -0.2


def test_linear_policy_model_rejects_schema_mismatch(tmp_path: Path) -> None:
    output = tmp_path / "bad_model.json"
    payload = {
        "weights": {},
        "bias": 0.0,
        "feature_schema_version": "wrong_schema",
        "model_schema_version": MODEL_SCHEMA_VERSION,
    }
    output.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="feature schema"):
        LinearPolicyModel.load(output)

    payload = {
        "weights": {},
        "bias": 0.0,
        "feature_schema_version": ENCODER_SCHEMA_VERSION,
        "model_schema_version": "wrong_model_schema",
    }
    output.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="Model schema"):
        LinearPolicyModel.load(output)
