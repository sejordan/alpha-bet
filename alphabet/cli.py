from __future__ import annotations

import sys
from typing import Callable, Dict, List


def _dispatch(commands: Dict[str, Callable[[List[str]], None]], argv: List[str]) -> int:
    if len(argv) == 0:
        print("Available commands: " + ", ".join(sorted(commands.keys())))
        return 0

    command = argv[0]
    if command not in commands:
        print(f"Unknown command: {command}")
        print("Available commands: " + ", ".join(sorted(commands.keys())))
        return 2

    commands[command](argv[1:])
    return 0


def main(argv: List[str] | None = None) -> int:
    from benchmark_strategies import main as benchmark_main
    from collect_rollouts import main as rollouts_main
    from eval_rl import main as eval_main
    from main import main as play_main
    from train_rl import main as train_main

    commands: Dict[str, Callable[[List[str]], None]] = {
        "play": play_main,
        "train": train_main,
        "eval": eval_main,
        "rollout": rollouts_main,
        "benchmark": benchmark_main,
    }

    args = argv if argv is not None else sys.argv[1:]
    return _dispatch(commands, args)


if __name__ == "__main__":
    raise SystemExit(main())
