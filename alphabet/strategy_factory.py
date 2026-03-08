from __future__ import annotations

import random
from dataclasses import dataclass

from alphabet.rl import LinearPolicyModel, RLLinearStrategy
from alphabet.strategy import (
    ActionStrategy,
    ExchangePassSafeStrategy,
    GreedyImmediateScoreStrategy,
    RandomLegalStrategy,
)


@dataclass(frozen=True)
class StrategyBuildResult:
    strategy: ActionStrategy
    warning: str = ""


def build_strategy(
    name: str,
    *,
    model_path: str = "",
    epsilon: float = 0.0,
    seed: int | None = None,
    strict_model_load: bool = False,
) -> StrategyBuildResult:
    normalized = name.strip().lower()

    if normalized in ("greedy", "greedy_immediate"):
        return StrategyBuildResult(strategy=GreedyImmediateScoreStrategy())

    if normalized in ("random", "random_legal"):
        return StrategyBuildResult(strategy=RandomLegalStrategy(rng=random.Random(seed)))

    if normalized in ("exchange_pass_safe", "safe"):
        return StrategyBuildResult(strategy=ExchangePassSafeStrategy())

    if normalized in ("rl", "rl_linear"):
        if model_path:
            try:
                model = LinearPolicyModel.load(model_path)
            except Exception as exc:  # pragma: no cover - exercised via integration paths
                if strict_model_load:
                    raise
                return StrategyBuildResult(
                    strategy=GreedyImmediateScoreStrategy(),
                    warning=f"Failed loading RL model '{model_path}': {exc}. Falling back to greedy.",
                )
        else:
            model = LinearPolicyModel.default()

        return StrategyBuildResult(
            strategy=RLLinearStrategy(model=model, epsilon=epsilon, rng=random.Random(seed))
        )

    if normalized == "rl_nn":
        if strict_model_load:
            raise ValueError("rl_nn is not implemented yet")
        return StrategyBuildResult(
            strategy=GreedyImmediateScoreStrategy(),
            warning="rl_nn not implemented; falling back to greedy.",
        )

    if strict_model_load:
        raise ValueError(f"Unsupported strategy: {name}")
    return StrategyBuildResult(
        strategy=GreedyImmediateScoreStrategy(),
        warning=f"Unsupported strategy '{name}'; falling back to greedy.",
    )
