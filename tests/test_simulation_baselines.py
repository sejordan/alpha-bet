import random

from alphabet.engine import GameEngine
from alphabet.game import Game
from alphabet.move import ExchangeMove
from alphabet.simulation import SimulationConfig, load_dictionary, run_game
from alphabet.strategy import ExchangePassSafeStrategy, RandomLegalStrategy


def test_run_game_is_reproducible_with_fixed_seed() -> None:
    dictionary = load_dictionary("dictionary/classic.txt")
    config = SimulationConfig(max_rounds=6)

    summary_a = run_game(
        engine_a=GameEngine(strategy=RandomLegalStrategy(rng=random.Random(101))),
        engine_b=GameEngine(strategy=RandomLegalStrategy(rng=random.Random(202))),
        config=config,
        dictionary=dictionary,
        seed=77,
    )
    summary_b = run_game(
        engine_a=GameEngine(strategy=RandomLegalStrategy(rng=random.Random(101))),
        engine_b=GameEngine(strategy=RandomLegalStrategy(rng=random.Random(202))),
        config=config,
        dictionary=dictionary,
        seed=77,
    )

    assert summary_a == summary_b


def test_exchange_pass_safe_ignores_candidates_and_exchanges() -> None:
    dictionary = load_dictionary("dictionary/classic.txt")
    game = _setup_started_game(dictionary)
    engine = GameEngine()

    candidates = engine.all_valid_moves_codex(game, game.active_player)
    assert len(candidates) > 0

    strategy = ExchangePassSafeStrategy()
    action = strategy.select_action(engine=engine, game=game, player=game.active_player, candidates=candidates)
    assert isinstance(action, ExchangeMove)


def _setup_started_game(dictionary) -> Game:
    game = Game(dictionary)
    game.start()
    assert game.next()
    return game
