import pytest

from edgelab.strategies.registry import StrategyRegistry
from edgelab.strategies.samples import SAMPLE_STRATEGIES
from edgelab.strategies.schema import AssetClass, StrategyStatus, TradingHorizon


def test_registry_rejects_duplicate_strategy_ids() -> None:
    strategy = SAMPLE_STRATEGIES[0]
    registry = StrategyRegistry([strategy])

    with pytest.raises(ValueError, match="Duplicate strategy_id"):
        registry.add(strategy)


def test_registry_filters_by_status() -> None:
    registry = StrategyRegistry.with_samples()

    strategies = registry.filter_by_status(StrategyStatus.RESEARCH_CANDIDATE)

    assert len(strategies) == len(SAMPLE_STRATEGIES)


def test_registry_filters_by_asset_class() -> None:
    registry = StrategyRegistry.with_samples()

    strategies = registry.filter_by_asset_class(AssetClass.ETFS)

    assert [strategy.strategy_id for strategy in strategies] == ["etf-risk-on-risk-off-rotation"]


def test_registry_filters_by_horizon() -> None:
    registry = StrategyRegistry.with_samples()

    strategies = registry.filter_by_horizon(TradingHorizon.DAILY)

    assert [strategy.strategy_id for strategy in strategies] == [
        "oversold-mean-reversion-with-news-veto"
    ]


def test_registry_filters_by_paper_trading_eligibility() -> None:
    registry = StrategyRegistry.with_samples()

    strategies = registry.filter_by_paper_trading_eligibility(False)

    assert len(strategies) == len(SAMPLE_STRATEGIES)


def test_registry_exports_all_strategies_as_dicts() -> None:
    registry = StrategyRegistry.with_samples()

    exported = registry.export_all()

    assert len(exported) == len(SAMPLE_STRATEGIES)
    assert exported[0]["strategy_id"] == SAMPLE_STRATEGIES[0].strategy_id
