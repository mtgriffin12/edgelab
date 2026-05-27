"""Strategy registry placeholders."""

from edgelab.strategies.schema import StrategySpec


class StrategyRegistry:
    """In-memory placeholder registry for strategy specs."""

    def __init__(self) -> None:
        self._strategies: dict[str, StrategySpec] = {}

    def add(self, strategy: StrategySpec) -> None:
        """Register a strategy spec."""

        self._strategies[strategy.strategy_id] = strategy

    def get(self, strategy_id: str) -> StrategySpec | None:
        """Return a strategy spec by id."""

        return self._strategies.get(strategy_id)
