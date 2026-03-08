from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from typing import Any, Dict, List

from alphabet.engine import GameEngine
from alphabet.move import Move
from alphabet.simulation import SimulationConfig, build_game, load_dictionary, set_seed
from alphabet.strategy_factory import build_strategy


BASELINES = ["greedy", "random", "exchange_pass_safe"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate RL checkpoints versus baselines.")
    parser.add_argument("--checkpoint", type=str, default="models/rl_linear.json")
    parser.add_argument("--checkpoint-glob", type=str, default="")
    parser.add_argument("--games", type=int, default=30)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-rounds", type=int, default=30)
    parser.add_argument("--dictionary", type=str, default="dictionary/classic.txt")
    parser.add_argument("--gate-winrate-vs-greedy", type=float, default=0.45)
    parser.add_argument("--gate-margin-vs-greedy", type=float, default=-25.0)
    parser.add_argument("--metrics-out", type=str, default="runs/eval/latest_metrics.json")
    parser.add_argument("--report-out", type=str, default="reports/rl_eval_latest.md")
    return parser.parse_args()


def resolve_checkpoints(args: argparse.Namespace) -> List[str]:
    if args.checkpoint_glob:
        matches = sorted(glob.glob(args.checkpoint_glob))
        if matches:
            return matches
    return [args.checkpoint]


def run_one_game(
    *,
    config: SimulationConfig,
    dictionary,
    seed: int,
    rl_model_path: str,
    baseline: str,
) -> Dict[str, Any]:
    set_seed(seed)
    rl_result = build_strategy("rl_linear", model_path=rl_model_path, epsilon=0.0, seed=seed)
    base_result = build_strategy(baseline, epsilon=0.0, seed=seed + 11)
    engine_a = GameEngine(strategy=rl_result.strategy)
    engine_b = GameEngine(strategy=base_result.strategy)

    game = build_game(config=config, dictionary=dictionary)
    game.start()
    if not game.next():
        return {"winner": "tie", "margin": 0, "turns": 0, "regret": 0.0}

    turns = 0
    regret_total = 0.0
    rl_moves = 0

    while True:
        turns += 1
        if game.active_player == game.players.a:
            candidates = engine_a.all_valid_moves_codex(game, game.active_player)
            action = engine_a.strategy.select_action(
                engine=engine_a,
                game=game,
                player=game.active_player,
                candidates=candidates,
            )

            if isinstance(action, Move) and candidates:
                chosen = game.score_move(action)
                best = max(game.score_move(candidate) for candidate in candidates)
                regret_total += float(best - chosen)
                rl_moves += 1
        else:
            action = engine_b.select_action(game, game.active_player, verbose=False)

        game.apply_action(action)
        if not game.next():
            break

    winner = "tie"
    if game.winner == game.players.a:
        winner = "a"
    elif game.winner == game.players.b:
        winner = "b"

    return {
        "winner": winner,
        "margin": game.players.a.score - game.players.b.score,
        "turns": turns,
        "regret": regret_total / max(1, rl_moves),
    }


def evaluate_checkpoint(
    *,
    checkpoint: str,
    config: SimulationConfig,
    dictionary,
    games: int,
    seed_start: int,
) -> Dict[str, Any]:
    by_baseline: Dict[str, Any] = {}

    for baseline in BASELINES:
        wins = 0
        losses = 0
        ties = 0
        margin_total = 0.0
        turns_total = 0.0
        regret_total = 0.0

        for idx in range(games):
            seed = seed_start + idx
            result = run_one_game(
                config=config,
                dictionary=dictionary,
                seed=seed,
                rl_model_path=checkpoint,
                baseline=baseline,
            )
            margin_total += float(result["margin"])
            turns_total += float(result["turns"])
            regret_total += float(result["regret"])
            if result["winner"] == "a":
                wins += 1
            elif result["winner"] == "b":
                losses += 1
            else:
                ties += 1

        total = max(1, games)
        by_baseline[baseline] = {
            "games": games,
            "win_rate": wins / total,
            "loss_rate": losses / total,
            "tie_rate": ties / total,
            "avg_margin": margin_total / total,
            "avg_turns": turns_total / total,
            "avg_regret": regret_total / total,
        }

    return {"checkpoint": checkpoint, "baselines": by_baseline}


def write_report(path: str, payload: Dict[str, Any], gates: Dict[str, Any]) -> None:
    lines: List[str] = []
    lines.append("# RL Evaluation Report")
    lines.append("")
    lines.append(f"- Overall status: **{'PASS' if gates['passed'] else 'FAIL'}**")
    lines.append(f"- Gate detail: {gates['detail']}")
    lines.append("")

    for result in payload["results"]:
        lines.append(f"## Checkpoint `{result['checkpoint']}`")
        for name in BASELINES:
            stats = result["baselines"][name]
            lines.append(
                f"- vs {name}: win_rate={stats['win_rate']:.3f}, avg_margin={stats['avg_margin']:.2f}, "
                f"avg_regret={stats['avg_regret']:.2f}, avg_turns={stats['avg_turns']:.2f}"
            )
        lines.append("")

    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines))


def main() -> None:
    args = parse_args()
    checkpoints = resolve_checkpoints(args)

    dictionary = load_dictionary(args.dictionary)
    config = SimulationConfig(dictionary_path=args.dictionary, max_rounds=args.max_rounds)

    results: List[Dict[str, Any]] = []
    for index, checkpoint in enumerate(checkpoints):
        result = evaluate_checkpoint(
            checkpoint=checkpoint,
            config=config,
            dictionary=dictionary,
            games=args.games,
            seed_start=args.seed + (index * 1000),
        )
        results.append(result)

    chosen = results[-1]
    greedy_stats = chosen["baselines"]["greedy"]
    gate_ok = (
        greedy_stats["win_rate"] >= args.gate_winrate_vs_greedy
        and greedy_stats["avg_margin"] >= args.gate_margin_vs_greedy
    )
    gates = {
        "passed": gate_ok,
        "detail": {
            "win_rate_vs_greedy": greedy_stats["win_rate"],
            "avg_margin_vs_greedy": greedy_stats["avg_margin"],
            "required_win_rate": args.gate_winrate_vs_greedy,
            "required_margin": args.gate_margin_vs_greedy,
        },
    }

    payload = {
        "config": {
            "games": args.games,
            "seed": args.seed,
            "max_rounds": args.max_rounds,
            "dictionary": args.dictionary,
            "checkpoints": checkpoints,
        },
        "results": results,
        "gates": gates,
    }

    metrics_path = Path(args.metrics_out)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    write_report(args.report_out, payload, gates)

    print(f"saved_metrics={metrics_path}")
    print(f"saved_report={args.report_out}")
    print(f"gate_passed={gates['passed']}")


if __name__ == "__main__":
    main()
