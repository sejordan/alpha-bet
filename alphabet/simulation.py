from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

import numpy as np

from alphabet.engine import GameEngine
from alphabet.game import Game
from alphabet.variant import GameVariant
from alphabet.wordsmith import Dictionary


@dataclass(frozen=True)
class SimulationConfig:
    dictionary_path: str = "dictionary/classic.txt"
    variant: GameVariant.Type = GameVariant.Type.CLASSIC
    max_rounds: int = 30


@dataclass(frozen=True)
class GameSummary:
    seed: int
    turns: int
    rounds: int
    score_a: int
    score_b: int
    winner: str

    @property
    def margin_a(self) -> int:
        return self.score_a - self.score_b


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def load_dictionary(path: str) -> Dictionary:
    words: List[str] = []
    with open(path, "r") as fh:
        for line in fh:
            value = line.strip()
            if value:
                words.append(value)
    return Dictionary(words)


def build_game(config: SimulationConfig, dictionary: Dictionary) -> Game:
    game = Game(dictionary=dictionary, variant=config.variant)
    game.max_rounds = config.max_rounds
    return game


def run_game(
    engine_a: GameEngine,
    engine_b: GameEngine,
    config: SimulationConfig,
    dictionary: Dictionary,
    seed: int,
) -> GameSummary:
    set_seed(seed)
    game = build_game(config=config, dictionary=dictionary)
    game.start()

    turns = 0
    while game.next():
        turns += 1
        engine = engine_a if game.active_player == game.players.a else engine_b
        action = engine.select_action(game, game.active_player, verbose=False)
        game.apply_action(action)

    winner = "tie"
    if game.winner == game.players.a:
        winner = "a"
    elif game.winner == game.players.b:
        winner = "b"

    return GameSummary(
        seed=seed,
        turns=turns,
        rounds=game.round,
        score_a=game.players.a.score,
        score_b=game.players.b.score,
        winner=winner,
    )
