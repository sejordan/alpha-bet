from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Dict, List

from alphabet.engine import GameEngine
from alphabet.game import Game
from alphabet.move import Move
from alphabet.rl import FEATURE_KEYS, RLLinearStrategy, LinearPolicyModel, margin_reward
from alphabet.wordsmith import Dictionary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a lightweight RL strategy via self-play.")
    parser.add_argument("--episodes", type=int, default=200, help="Number of self-play games.")
    parser.add_argument("--alpha", type=float, default=0.01, help="Learning rate.")
    parser.add_argument("--epsilon", type=float, default=0.1, help="Exploration rate.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed.")
    parser.add_argument("--report-every", type=int, default=25, help="Progress print interval.")
    parser.add_argument(
        "--dictionary",
        type=str,
        default="dictionary/classic.txt",
        help="Path to dictionary word list.",
    )
    parser.add_argument("--model-in", type=str, default=None, help="Optional checkpoint path to resume from.")
    parser.add_argument(
        "--model-out",
        type=str,
        default="models/rl_linear.json",
        help="Output path for trained model.",
    )
    return parser.parse_args()


def load_dictionary(path: str) -> Dictionary:
    words: List[str] = []
    with open(path, "r") as fh:
        for line in fh:
            value = line.strip()
            if value:
                words.append(value)
    return Dictionary(words)


def train_episode(dictionary: Dictionary, strategy: RLLinearStrategy, alpha: float) -> Dict[str, float]:
    game = Game(dictionary)
    game.start()
    engine = GameEngine(strategy=strategy)

    samples_a: List[Dict[str, float]] = []
    samples_b: List[Dict[str, float]] = []

    while game.next():
        player = game.active_player
        candidates = engine.all_valid_moves_codex(game, player)
        action = strategy.select_action(engine=engine, game=game, player=player, candidates=candidates)

        if isinstance(action, Move):
            features = strategy.move_features(game, player, action)
            if player == game.players.a:
                samples_a.append(features)
            else:
                samples_b.append(features)

        game.apply_action(action)

    reward_a = margin_reward(game)
    reward_b = -reward_a

    for features in samples_a:
        strategy.model.update(features=features, target=reward_a, alpha=alpha)

    for features in samples_b:
        strategy.model.update(features=features, target=reward_b, alpha=alpha)

    return {
        "reward_a": reward_a,
        "reward_b": reward_b,
        "score_a": float(game.players.a.score),
        "score_b": float(game.players.b.score),
        "moves_a": float(len(samples_a)),
        "moves_b": float(len(samples_b)),
    }


def main() -> None:
    args = parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    dictionary = load_dictionary(args.dictionary)

    if args.model_in is not None and Path(args.model_in).exists():
        model = LinearPolicyModel.load(args.model_in)
    else:
        model = LinearPolicyModel.default()

    strategy = RLLinearStrategy(model=model, epsilon=args.epsilon, rng=random.Random(args.seed))

    reward_total = 0.0
    margin_total = 0.0

    for episode in range(1, args.episodes + 1):
        stats = train_episode(dictionary, strategy, alpha=args.alpha)
        reward_total += stats["reward_a"]
        margin_total += stats["score_a"] - stats["score_b"]

        if episode % args.report_every == 0 or episode == args.episodes:
            avg_reward = reward_total / episode
            avg_margin = margin_total / episode
            print(
                f"episode={episode} avg_reward={avg_reward:.4f} avg_margin={avg_margin:.2f} "
                f"weights={{"
                + ", ".join([f"{k}:{strategy.model.weights.get(k, 0.0):.4f}" for k in FEATURE_KEYS])
                + "}}"
            )

    strategy.model.save(args.model_out)
    print(f"saved_model={args.model_out}")


if __name__ == "__main__":
    main()
