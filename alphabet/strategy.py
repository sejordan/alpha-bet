from __future__ import annotations

from abc import ABC, abstractmethod
import random
from typing import TYPE_CHECKING, List

from alphabet.move import ExchangeMove, Move, PassMove

if TYPE_CHECKING:
    from alphabet.engine import GameEngine
    from alphabet.game import Game, Player


class ActionStrategy(ABC):
    @abstractmethod
    def select_action(
        self,
        engine: "GameEngine",
        game: "Game",
        player: "Player",
        candidates: List[Move],
    ) -> Move | ExchangeMove | PassMove:
        raise NotImplementedError


class GreedyImmediateScoreStrategy(ActionStrategy):
    """
    Default strategy:
    1. pick move with highest immediate score
    2. tie-break by greater tiles used
    3. tie-break deterministically by placement signature
    4. if no moves, exchange when possible, else pass
    """

    def select_action(
        self,
        engine: "GameEngine",
        game: "Game",
        player: "Player",
        candidates: List[Move],
    ) -> Move | ExchangeMove | PassMove:
        if candidates:
            best_move: Move | None = None
            best_key: tuple[int, int, tuple] | None = None
            for candidate in candidates:
                key = (
                    game.score_move(candidate),
                    len(candidate.placements),
                    tuple(engine._move_signature_codex(candidate)),  # pylint: disable=protected-access
                )
                if best_key is None or key > best_key:
                    best_key = key
                    best_move = candidate
            assert best_move is not None
            return best_move

        exchange_count = min(len(player.tiles), game.bag.total_tiles)
        if exchange_count > 0:
            return ExchangeMove(player.tiles[:exchange_count])

        return PassMove()


class RandomLegalStrategy(ActionStrategy):
    """
    Baseline strategy:
    1. choose a random legal word move
    2. if no words, exchange a random subset of rack tiles
    3. if exchange impossible, pass
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng if rng is not None else random.Random()

    def select_action(
        self,
        engine: "GameEngine",
        game: "Game",
        player: "Player",
        candidates: List[Move],
    ) -> Move | ExchangeMove | PassMove:
        if candidates:
            return self.rng.choice(candidates)

        exchange_count = min(len(player.tiles), game.bag.total_tiles)
        if exchange_count > 0:
            take = self.rng.randint(1, exchange_count)
            return ExchangeMove(self.rng.sample(player.tiles, take))

        return PassMove()


class ExchangePassSafeStrategy(ActionStrategy):
    """
    Floor baseline that never attempts board plays.
    It only exchanges when possible, otherwise passes.
    """

    def select_action(
        self,
        engine: "GameEngine",
        game: "Game",
        player: "Player",
        candidates: List[Move],
    ) -> Move | ExchangeMove | PassMove:
        exchange_count = min(len(player.tiles), game.bag.total_tiles)
        if exchange_count > 0:
            return ExchangeMove(player.tiles[:exchange_count])
        return PassMove()
