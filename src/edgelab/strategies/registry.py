"""In-memory strategy registry."""

from __future__ import annotations

from edgelab.strategies.schema import AssetClass, StrategySpec, StrategyStatus, TradingHorizon


class StrategyRegistry:
    """In-memory registry for strategy specs."""

    def __init__(self, strategies: list[StrategySpec] | None = None) -> None:
        self._strategies: dict[str, StrategySpec] = {}
        for strategy in strategies or []:
            self.add(strategy)

    def add(self, strategy: StrategySpec) -> None:
        """Register a strategy spec."""

        if strategy.strategy_id in self._strategies:
            raise ValueError(f"Duplicate strategy_id: {strategy.strategy_id}")

        self._strategies[strategy.strategy_id] = strategy

    def list_strategies(self) -> list[StrategySpec]:
        """Return all registered strategies."""

        return list(self._strategies.values())

    def get(self, strategy_id: str) -> StrategySpec | None:
        """Return a strategy spec by id."""

        return self._strategies.get(strategy_id)

    def filter_by_status(self, status: StrategyStatus) -> list[StrategySpec]:
        """Return strategies matching a lifecycle status."""

        return [strategy for strategy in self.list_strategies() if strategy.status == status]

    def filter_by_asset_class(self, asset_class: AssetClass) -> list[StrategySpec]:
        """Return strategies matching an asset class."""

        return [
            strategy for strategy in self.list_strategies() if strategy.asset_class == asset_class
        ]

    def filter_by_horizon(self, horizon: TradingHorizon) -> list[StrategySpec]:
        """Return strategies matching a trading horizon."""

        return [strategy for strategy in self.list_strategies() if strategy.horizon == horizon]

    def filter_by_paper_trading_eligibility(self, eligible: bool) -> list[StrategySpec]:
        """Return strategies by paper-trading eligibility."""

        return [
            strategy
            for strategy in self.list_strategies()
            if strategy.eligible_for_paper_trading == eligible
        ]

    def export_all(self) -> list[dict[str, object]]:
        """Export strategies as JSON-friendly dictionaries."""

        return [strategy.model_dump(mode="json") for strategy in self.list_strategies()]

    @classmethod
    def with_samples(cls) -> StrategyRegistry:
        """Create a registry loaded with the sample strategy set."""

        from edgelab.strategies.samples import SAMPLE_STRATEGIES

        return cls(list(SAMPLE_STRATEGIES))
