from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Dict, List

from alphabet.engine import GameEngine
from alphabet.move import Move
from alphabet.rl import FEATURE_KEYS, RLLinearStrategy, LinearPolicyModel, margin_reward
from alphabet.sim_runner import run_episode
from alphabet.simulation import SimulationConfig, load_dictionary, set_seed


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train RL linear strategy via self-play.")
    parser.add_argument("--episodes", type=int, default=200, help="Number of self-play games.")
    parser.add_argument("--alpha", type=float, default=0.01, help="Learning rate.")
    parser.add_argument("--gamma", type=float, default=0.98, help="Discount factor for Monte Carlo returns.")
    parser.add_argument("--epsilon", type=float, default=0.1, help="Exploration rate.")
    parser.add_argument("--seed", type=int, default=1, help="Random seed base.")
    parser.add_argument("--report-every", type=int, default=25, help="Progress print interval.")
    parser.add_argument("--checkpoint-every", type=int, default=50, help="Checkpoint cadence.")
    parser.add_argument("--dictionary", type=str, default="dictionary/classic.txt")
    parser.add_argument("--max-rounds", type=int, default=30)
    parser.add_argument("--model-in", type=str, default=None, help="Resume from model checkpoint path.")
    parser.add_argument("--model-out", type=str, default="models/rl_linear.json")
    parser.add_argument("--metrics-out", type=str, default="runs/train/latest_metrics.json")
    parser.add_argument(
        "--run-dir",
        type=str,
        default="runs/train/latest",
        help="Where episodic metrics/checkpoints are written.",
    )
    return parser.parse_args(argv)


def _safe_value(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return value


def _policy_entropy(scores: List[float]) -> float:
    if len(scores) <= 1:
        return 0.0
    max_s = max(scores)
    exps = [math.exp(s - max_s) for s in scores]
    total = sum(exps)
    if total <= 0:
        return 0.0
    entropy = 0.0
    for val in exps:
        p = val / total
        if p > 0:
            entropy -= p * math.log(p)
    return entropy


def train_episode(
    *,
    engine: GameEngine,
    strategy: RLLinearStrategy,
    config: SimulationConfig,
    dictionary,
    alpha: float,
    gamma: float,
    seed: int,
) -> Dict[str, float]:
    samples_a: List[Dict[str, float]] = []
    samples_b: List[Dict[str, float]] = []
    policy_entropies: List[float] = []
    td_errors: List[float] = []

    def before_action(game, player, move_engine, candidates, action) -> None:
        if candidates:
            scores = [strategy.model.score(strategy.move_features(game, player, c)) for c in candidates]
            policy_entropies.append(_policy_entropy(scores))

        if isinstance(action, Move):
            features = strategy.move_features(game, player, action)
            if player == game.players.a:
                samples_a.append(features)
            else:
                samples_b.append(features)

    episode = run_episode(
        config=config,
        dictionary=dictionary,
        engine_a=engine,
        engine_b=engine,
        seed=seed,
        before_action=before_action,
    )
    game = episode.game

    reward_a = margin_reward(game)
    reward_b = -reward_a

    def update_with_returns(samples: List[Dict[str, float]], terminal_reward: float) -> None:
        running_return = terminal_reward
        for features in reversed(samples):
            predicted = strategy.model.score(features)
            td_errors.append(abs(running_return - predicted))
            strategy.model.update(features=features, target=running_return, alpha=alpha)
            # Monte Carlo return with temporal credit assignment.
            running_return *= gamma

    update_with_returns(samples_a, reward_a)
    update_with_returns(samples_b, reward_b)

    # guardrails for unstable updates
    strategy.model.bias = _safe_value(strategy.model.bias)
    for key in FEATURE_KEYS:
        strategy.model.weights[key] = _safe_value(strategy.model.weights.get(key, 0.0))

    return {
        "reward_a": reward_a,
        "reward_b": reward_b,
        "score_a": float(game.players.a.score),
        "score_b": float(game.players.b.score),
        "moves": float(len(samples_a) + len(samples_b)),
        "avg_entropy": sum(policy_entropies) / max(1, len(policy_entropies)),
        "avg_td_error": sum(td_errors) / max(1, len(td_errors)),
    }


def main(argv: List[str] | None = None) -> None:
    args = parse_args(argv)

    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoints_dir = run_dir / "checkpoints"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    set_seed(args.seed)
    dictionary = load_dictionary(args.dictionary)
    config = SimulationConfig(dictionary_path=args.dictionary, max_rounds=args.max_rounds)

    if args.model_in and Path(args.model_in).exists():
        model = LinearPolicyModel.load(args.model_in)
    else:
        model = LinearPolicyModel.default()

    strategy = RLLinearStrategy(model=model, epsilon=args.epsilon, rng=random.Random(args.seed))
    engine = GameEngine(strategy=strategy)

    history: List[Dict[str, float]] = []
    reward_total = 0.0
    margin_total = 0.0

    for episode in range(1, args.episodes + 1):
        episode_seed = args.seed + episode
        stats = train_episode(
            engine=engine,
            strategy=strategy,
            config=config,
            dictionary=dictionary,
            alpha=args.alpha,
            gamma=args.gamma,
            seed=episode_seed,
        )

        reward_total += stats["reward_a"]
        margin_total += stats["score_a"] - stats["score_b"]

        entry = {
            "episode": float(episode),
            "avg_reward": reward_total / episode,
            "avg_margin": margin_total / episode,
            "episode_reward": stats["reward_a"],
            "episode_margin": stats["score_a"] - stats["score_b"],
            "avg_entropy": stats["avg_entropy"],
            "avg_td_error": stats["avg_td_error"],
        }
        history.append(entry)

        if episode % args.report_every == 0 or episode == args.episodes:
            print(
                f"episode={episode} avg_reward={entry['avg_reward']:.4f} avg_margin={entry['avg_margin']:.2f} "
                f"avg_entropy={entry['avg_entropy']:.4f} avg_td_error={entry['avg_td_error']:.4f}"
            )

        if episode % args.checkpoint_every == 0 or episode == args.episodes:
            checkpoint_path = checkpoints_dir / f"episode_{episode:05d}.json"
            strategy.model.save(checkpoint_path)

    strategy.model.save(args.model_out)

    recommendation = "keep_linear"
    if len(history) >= 50:
        recent = history[-25:]
        prior = history[-50:-25]
        recent_margin = sum(item["episode_margin"] for item in recent) / len(recent)
        prior_margin = sum(item["episode_margin"] for item in prior) / len(prior)
        if recent_margin - prior_margin < 1.0:
            recommendation = "consider_mlp"

    metrics_payload: Dict[str, object] = {
        "episodes": args.episodes,
        "alpha": args.alpha,
        "gamma": args.gamma,
        "epsilon": args.epsilon,
        "seed": args.seed,
        "dictionary": args.dictionary,
        "max_rounds": args.max_rounds,
        "model_out": args.model_out,
        "final_weights": strategy.model.weights,
        "final_bias": strategy.model.bias,
        "history": history,
        "recommendation": recommendation,
    }

    metrics_path = Path(args.metrics_out)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics_payload, indent=2, sort_keys=True))

    print(f"saved_model={args.model_out}")
    print(f"saved_metrics={metrics_path}")
    print(f"recommendation={recommendation}")


if __name__ == "__main__":
    main()
