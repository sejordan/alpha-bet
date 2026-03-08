from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Sequence

from alphabet.encoding import ActionEncoder, StateEncoder
from alphabet.engine import GameEngine
from alphabet.move import Move
from alphabet.sim_runner import run_episode
from alphabet.simulation import SimulationConfig
from alphabet.wordsmith import Dictionary


@dataclass
class Transition:
    episode: int
    step: int
    player: str
    state: Dict[str, Any]
    action: Dict[str, Any]
    reward: float
    next_state: Dict[str, Any]
    done: bool


@dataclass
class RolloutSummary:
    episodes: int
    transitions: int
    path: str


def _write_metadata(path: Path, metadata: Dict[str, Any]) -> None:
    meta_path = path.with_suffix(path.suffix + ".meta.json")
    meta_path.write_text(json.dumps(metadata, indent=2, sort_keys=True))


def _episode_seed(seed_start: int, episode: int, seed_stride: int) -> int:
    return seed_start + (episode * seed_stride)


def run_rollouts(
    *,
    dictionary: Dictionary,
    config: SimulationConfig,
    engine_a: GameEngine,
    engine_b: GameEngine,
    episodes: int,
    seed_start: int,
    seed_stride: int,
    output_jsonl: str,
    opponent_mix: Sequence[str] | None = None,
) -> RolloutSummary:
    state_encoder = StateEncoder()
    action_encoder = ActionEncoder()

    output_path = Path(output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    transitions = 0
    with output_path.open("w") as fh:
        for episode in range(episodes):
            seed = _episode_seed(seed_start, episode, seed_stride)
            step = 0
            pending: Dict[str, Any] = {}

            def before_action(game, player, current_engine, candidates, action) -> None:
                nonlocal pending
                state = state_encoder.encode(game, player).to_dict()
                reward = 0.0
                action_payload: Dict[str, Any]
                if isinstance(action, Move):
                    action_payload = action_encoder.encode(game, player, action).to_dict()
                    reward = float(game.score_move(action))
                else:
                    action_payload = {
                        "schema_version": state["schema_version"],
                        "type": action.__class__.__name__,
                    }

                pending = {
                    "player": "a" if player == game.players.a else "b",
                    "state": state,
                    "action_payload": action_payload,
                    "reward": reward,
                }

            def after_action(game, player, current_engine, candidates, action, done) -> None:
                nonlocal step, transitions, pending
                if not done:
                    next_player = game.active_player
                    next_state = state_encoder.encode(game, next_player).to_dict()
                else:
                    next_state = {
                        "terminal": True,
                        "score_a": game.players.a.score,
                        "score_b": game.players.b.score,
                    }

                step += 1
                record = Transition(
                    episode=episode,
                    step=step,
                    player=pending["player"],
                    state=pending["state"],
                    action=pending["action_payload"],
                    reward=pending["reward"],
                    next_state=next_state,
                    done=done,
                )
                fh.write(json.dumps(record.__dict__) + "\n")
                transitions += 1

            run_episode(
                config=config,
                dictionary=dictionary,
                engine_a=engine_a,
                engine_b=engine_b,
                seed=seed,
                before_action=before_action,
                after_action=after_action,
            )

    metadata = {
        "episodes": episodes,
        "transitions": transitions,
        "seed_start": seed_start,
        "seed_stride": seed_stride,
        "dictionary_path": config.dictionary_path,
        "variant": config.variant.name,
        "max_rounds": config.max_rounds,
        "opponent_mix": list(opponent_mix) if opponent_mix is not None else [],
    }
    _write_metadata(output_path, metadata)
    return RolloutSummary(episodes=episodes, transitions=transitions, path=str(output_path))


def load_jsonl(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, "r") as fh:
        for line in fh:
            value = line.strip()
            if value:
                yield json.loads(value)
