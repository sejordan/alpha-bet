from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from alphabet.engine import GameEngine
from alphabet.game import Game, Player
from alphabet.move import ExchangeMove, Move, PassMove
from alphabet.simulation import SimulationConfig, build_game, set_seed
from alphabet.wordsmith import Dictionary


Action = Move | ExchangeMove | PassMove
BeforeActionHook = Callable[[Game, Player, GameEngine, List[Move], Action], None]
AfterActionHook = Callable[[Game, Player, GameEngine, List[Move], Action, bool], None]


@dataclass(frozen=True)
class EpisodeResult:
    game: Game
    turns: int


def run_episode(
    *,
    config: SimulationConfig,
    dictionary: Dictionary,
    engine_a: GameEngine,
    engine_b: GameEngine,
    seed: int,
    before_action: BeforeActionHook | None = None,
    after_action: AfterActionHook | None = None,
) -> EpisodeResult:
    set_seed(seed)
    game = build_game(config=config, dictionary=dictionary)
    game.start()

    turns = 0
    if not game.next():
        return EpisodeResult(game=game, turns=turns)

    while True:
        turns += 1
        player = game.active_player
        engine = engine_a if player == game.players.a else engine_b
        candidates = engine.all_valid_moves_codex(game, player)
        action = engine.strategy.select_action(engine=engine, game=game, player=player, candidates=candidates)

        if before_action is not None:
            before_action(game, player, engine, candidates, action)

        game.apply_action(action)
        done = not game.next()

        if after_action is not None:
            after_action(game, player, engine, candidates, action, done)

        if done:
            return EpisodeResult(game=game, turns=turns)
