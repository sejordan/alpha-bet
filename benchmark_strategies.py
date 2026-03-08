from __future__ import annotations

import argparse
import random
from dataclasses import asdict

from alphabet.engine import GameEngine
from alphabet.rl import LinearPolicyModel, RLLinearStrategy
from alphabet.simulation import SimulationConfig, load_dictionary, run_game
from alphabet.strategy import (
    ExchangePassSafeStrategy,
    GreedyImmediateScoreStrategy,
    RandomLegalStrategy,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark strategy matchups with reproducible seeds.")
    parser.add_argument("--games", type=int, default=50, help="Number of games.")
    parser.add_argument("--seed", type=int, default=1, help="Base seed for reproducible game seeds.")
    parser.add_argument("--dictionary", type=str, default="dictionary/classic.txt")
    parser.add_argument("--max-rounds", type=int, default=30)
    parser.add_argument(
        "--a-strategy",
        choices=["greedy", "random", "exchange_pass_safe", "rl"],
        default="greedy",
    )
    parser.add_argument(
        "--b-strategy",
        choices=["greedy", "random", "exchange_pass_safe", "rl"],
        default="random",
    )
    parser.add_argument("--a-model", type=str, default="", help="Model path for A when strategy is rl.")
    parser.add_argument("--b-model", type=str, default="", help="Model path for B when strategy is rl.")
    parser.add_argument("--a-epsilon", type=float, default=0.0)
    parser.add_argument("--b-epsilon", type=float, default=0.0)
    parser.add_argument("--print-games", action="store_true", help="Print per-game summaries.")
    return parser.parse_args()


def build_engine(name: str, model_path: str, epsilon: float, seed: int) -> GameEngine:
    if name == "greedy":
        return GameEngine(strategy=GreedyImmediateScoreStrategy())

    if name == "random":
        return GameEngine(strategy=RandomLegalStrategy(rng=random.Random(seed)))

    if name == "exchange_pass_safe":
        return GameEngine(strategy=ExchangePassSafeStrategy())

    if name == "rl":
        model = LinearPolicyModel.default()
        if model_path:
            model = LinearPolicyModel.load(model_path)
        return GameEngine(strategy=RLLinearStrategy(model=model, epsilon=epsilon, rng=random.Random(seed)))

    raise ValueError(f"Unsupported strategy: {name}")


def main() -> None:
    args = parse_args()

    config = SimulationConfig(
        dictionary_path=args.dictionary,
        max_rounds=args.max_rounds,
    )
    dictionary = load_dictionary(config.dictionary_path)

    wins_a = 0
    wins_b = 0
    ties = 0
    margin_total = 0
    turns_total = 0
    rounds_total = 0

    for game_idx in range(args.games):
        seed = args.seed + game_idx
        engine_a = build_engine(args.a_strategy, args.a_model, args.a_epsilon, seed=(seed * 2) + 1)
        engine_b = build_engine(args.b_strategy, args.b_model, args.b_epsilon, seed=(seed * 2) + 2)

        summary = run_game(
            engine_a=engine_a,
            engine_b=engine_b,
            config=config,
            dictionary=dictionary,
            seed=seed,
        )

        margin_total += summary.margin_a
        turns_total += summary.turns
        rounds_total += summary.rounds

        if summary.winner == "a":
            wins_a += 1
        elif summary.winner == "b":
            wins_b += 1
        else:
            ties += 1

        if args.print_games:
            print(asdict(summary))

    total = max(1, args.games)
    print(f"matchup={args.a_strategy}_vs_{args.b_strategy}")
    print(f"games={args.games} seed_start={args.seed} max_rounds={args.max_rounds}")
    print(f"win_rate_a={wins_a / total:.4f} win_rate_b={wins_b / total:.4f} tie_rate={ties / total:.4f}")
    print(f"avg_margin_a={margin_total / total:.2f}")
    print(f"avg_turns={turns_total / total:.2f} avg_rounds={rounds_total / total:.2f}")


if __name__ == "__main__":
    main()
