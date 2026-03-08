import json
import random
from pathlib import Path

from alphabet.engine import GameEngine
from alphabet.rollout import load_jsonl, run_rollouts
from alphabet.simulation import SimulationConfig, load_dictionary
from alphabet.strategy import RandomLegalStrategy


def test_rollout_records_have_consistent_state_action_shape(tmp_path: Path) -> None:
    dictionary = load_dictionary("dictionary/classic.txt")
    config = SimulationConfig(max_rounds=4)

    output = tmp_path / "rollout.jsonl"
    summary = run_rollouts(
        dictionary=dictionary,
        config=config,
        engine_a=GameEngine(strategy=RandomLegalStrategy(rng=random.Random(1))),
        engine_b=GameEngine(strategy=RandomLegalStrategy(rng=random.Random(2))),
        episodes=2,
        seed_start=10,
        seed_stride=1,
        output_jsonl=str(output),
    )

    assert summary.episodes == 2
    assert summary.transitions > 0

    rows = list(load_jsonl(str(output)))
    assert len(rows) == summary.transitions

    for row in rows:
        assert row["player"] in ("a", "b")
        assert isinstance(row["state"], dict)
        assert "schema_version" in row["state"]
        assert "action" in row
        assert "reward" in row
        assert "done" in row

    meta = json.loads(output.with_suffix(output.suffix + ".meta.json").read_text())
    assert meta["episodes"] == 2
    assert meta["transitions"] == summary.transitions
