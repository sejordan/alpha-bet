from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphabet.engine import GameEngine
from alphabet.rollout import run_rollouts
from alphabet.simulation import SimulationConfig, load_dictionary
from alphabet.strategy_factory import build_strategy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect RL rollouts into JSONL transitions.")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--seed-stride", type=int, default=1)
    parser.add_argument("--dictionary", type=str, default="dictionary/classic.txt")
    parser.add_argument("--max-rounds", type=int, default=30)
    parser.add_argument("--output", type=str, default="runs/rollouts/latest.jsonl")
    parser.add_argument(
        "--opponent-mix",
        type=str,
        default="greedy,random,exchange_pass_safe",
        help="Comma-separated strategy pool for Player B rotation.",
    )
    parser.add_argument("--a-strategy", type=str, default="greedy")
    parser.add_argument("--a-model", type=str, default="")
    parser.add_argument("--a-epsilon", type=float, default=0.0)
    parser.add_argument("--b-model", type=str, default="")
    parser.add_argument("--b-epsilon", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dictionary = load_dictionary(args.dictionary)
    config = SimulationConfig(dictionary_path=args.dictionary, max_rounds=args.max_rounds)

    pool = [name.strip() for name in args.opponent_mix.split(",") if name.strip()]
    if not pool:
        pool = ["greedy"]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Rotate opponent strategy mix across short rollout shards and append.
    shard_size = max(1, args.episodes // len(pool))
    remaining = args.episodes
    current_seed = args.seed_start

    total_transitions = 0
    if output_path.exists():
        output_path.unlink()

    for index, opponent_name in enumerate(pool):
        episodes = shard_size if index < len(pool) - 1 else remaining
        if episodes <= 0:
            continue

        strategy_a_result = build_strategy(
            args.a_strategy,
            model_path=args.a_model,
            epsilon=args.a_epsilon,
            seed=current_seed,
        )
        strategy_b_result = build_strategy(
            opponent_name,
            model_path=args.b_model,
            epsilon=args.b_epsilon,
            seed=current_seed + 17,
        )
        engine_a = GameEngine(strategy=strategy_a_result.strategy)
        engine_b = GameEngine(strategy=strategy_b_result.strategy)

        shard_output = output_path.with_suffix(f".part{index}.jsonl")
        summary = run_rollouts(
            dictionary=dictionary,
            config=config,
            engine_a=engine_a,
            engine_b=engine_b,
            episodes=episodes,
            seed_start=current_seed,
            seed_stride=args.seed_stride,
            output_jsonl=str(shard_output),
            opponent_mix=pool,
        )

        with shard_output.open("r") as source, output_path.open("a") as target:
            target.write(source.read())
        total_transitions += summary.transitions
        shard_output.unlink(missing_ok=True)
        shard_output.with_suffix(shard_output.suffix + ".meta.json").unlink(missing_ok=True)

        remaining -= episodes
        current_seed += episodes * args.seed_stride
        print(f"collected episodes={episodes} vs={opponent_name} transitions={summary.transitions}")

    output_path.with_suffix(output_path.suffix + ".meta.json").write_text(
        json.dumps(
            {
                "episodes": args.episodes,
                "transitions": total_transitions,
                "seed_start": args.seed_start,
                "seed_stride": args.seed_stride,
                "dictionary_path": args.dictionary,
                "max_rounds": args.max_rounds,
                "opponent_mix": pool,
                "a_strategy": args.a_strategy,
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"rollouts_path={output_path}")


if __name__ == "__main__":
    main()
