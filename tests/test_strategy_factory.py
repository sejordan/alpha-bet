from pathlib import Path

from alphabet.rl import LinearPolicyModel, RLLinearStrategy
from alphabet.strategy import GreedyImmediateScoreStrategy
from alphabet.strategy_factory import build_strategy


def test_factory_builds_rl_strategy_with_valid_model(tmp_path: Path) -> None:
    model = LinearPolicyModel.default()
    path = tmp_path / "model.json"
    model.save(path)

    result = build_strategy("rl", model_path=str(path), epsilon=0.0, seed=1)
    assert result.warning == ""
    assert isinstance(result.strategy, RLLinearStrategy)


def test_factory_falls_back_to_greedy_on_bad_model_path() -> None:
    result = build_strategy("rl", model_path="/no/such/model.json", strict_model_load=False)
    assert "Falling back to greedy" in result.warning
    assert isinstance(result.strategy, GreedyImmediateScoreStrategy)
