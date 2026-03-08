import argparse
import random
import time
from typing import List

from alphabet.game import Game
from alphabet.display import GameDisplay
from alphabet.engine import GameEngine
from alphabet.rl import LinearPolicyModel, RLLinearStrategy
from alphabet.strategy import GreedyImmediateScoreStrategy
from alphabet.wordsmith import Dictionary
from alphabet.move import Move, ExchangeMove, PassMove
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an alpha-bet game simulation.")
    parser.add_argument("--quiet", action="store_true", help="Suppress board rendering and per-turn detail output.")
    parser.add_argument("--seed", type=int, default=None, help="Set RNG seed for deterministic runs.")
    parser.add_argument("--benchmark", action="store_true", help="Print timing and throughput summary.")
    parser.add_argument(
        "--strategy",
        choices=["greedy", "rl"],
        default="greedy",
        help="Move-selection strategy for both players.",
    )
    parser.add_argument(
        "--model-path",
        default="",
        help="Path to RL model checkpoint JSON (used when --strategy=rl).",
    )
    parser.add_argument(
        "--epsilon",
        type=float,
        default=0.0,
        help="Exploration rate for RL strategy.",
    )
    return parser.parse_args()


def _build_engine(args: argparse.Namespace) -> GameEngine:
    if args.strategy == "rl":
        if args.model_path:
            model = LinearPolicyModel.load(args.model_path)
        else:
            model = LinearPolicyModel.default()
        strategy = RLLinearStrategy(model=model, epsilon=args.epsilon, rng=random.Random(args.seed))
        return GameEngine(strategy=strategy)

    return GameEngine(strategy=GreedyImmediateScoreStrategy())


def main():
    args = parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)

    words: List[str] = []
    with open('./dictionary/classic.txt', 'r') as fh:
        for line in fh:
            words.append(line.strip())

    dictionary = Dictionary(words)

    game = Game(dictionary)
    game.start()

    game_engine = _build_engine(args)

    game_start = time.perf_counter()
    turns = 0
    while game.next():
        turns += 1
        if not args.quiet:
            print(f"Round={game.round}; Current Turn={game.active_player}")
            GameDisplay.present(game)

        action = game_engine.select_action(game, game.active_player, verbose=not args.quiet)
        if not args.quiet:
            if isinstance(action, PassMove):
                print(f"{game.active_player} has no valid moves and passes.")
            elif isinstance(action, ExchangeMove):
                print(f"{game.active_player} exchanges {len(action.tiles)} tiles.")
            elif isinstance(action, Move):
                print(f"{game.active_player} plays {len(action.placements)} tiles.")

        game.apply_action(action)

    if not args.quiet:
        GameDisplay.present(game)

    print("Winner: ", "Tie Game!" if game.is_tie else (game.winner.name if game.winner else "None!"))

    if args.benchmark:
        elapsed = time.perf_counter() - game_start
        per_turn_ms = 1000 * elapsed / max(1, turns)
        print(f"Benchmark: turns={turns} elapsed={elapsed:.3f}s avg_turn={per_turn_ms:.2f}ms")


if __name__ == "__main__":
    main()
