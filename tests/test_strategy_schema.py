import pytest
from pydantic import ValidationError

from edgelab.strategies.schema import (
    AssetClass,
    EntryRule,
    ExitRule,
    PositionSizingRule,
    RiskRule,
    SignalType,
    StrategyDirection,
    StrategyEvidenceRequirement,
    StrategySignal,
    StrategySpec,
    StrategyUniverse,
    TradingHorizon,
)


def build_valid_strategy(**overrides: object) -> StrategySpec:
    data: dict[str, object] = {
        "strategy_id": "mean-reversion-placeholder",
        "name": "Mean Reversion Placeholder",
        "description": "A testable placeholder strategy.",
        "thesis": "Short-term stretches can revert when risk gates allow exposure.",
        "asset_class": AssetClass.US_EQUITIES_AND_ETFS,
        "direction": StrategyDirection.LONG_ONLY,
        "horizon": TradingHorizon.MULTI_DAY_SWING,
        "universe": StrategyUniverse(description="Liquid US equities and ETFs.", symbols=["SPY"]),
        "signals": [
            StrategySignal(
                name="Oversold",
                description="Placeholder oversold condition.",
                signal_type=SignalType.PRICE,
                inputs=["close"],
                rule="close below placeholder threshold",
            )
        ],
        "entry_rules": [
            EntryRule(
                name="Validated entry",
                description="Enter only after confirmation.",
                rule="entry requires confirmation",
            )
        ],
        "exit_rules": [
            ExitRule(
                name="Validated exit",
                description="Exit on reversal or timeout.",
                rule="exit on reversal or timeout",
            )
        ],
        "position_sizing": PositionSizingRule(
            method="fixed_fractional_research",
            description="Placeholder fixed fractional sizing.",
        ),
        "risk_rules": [
            RiskRule(
                name="Risk veto",
                description="Reject stale or excessive-risk signals.",
                veto_condition="data is stale or risk limit is breached",
            )
        ],
        "holding_period": "daily to multi-day swing",
        "expected_edge": "Unknown until backtested.",
        "failure_conditions": ["No evidence yet."],
        "evidence_required": [
            StrategyEvidenceRequirement(
                name="Backtest evidence",
                description="Requires point-in-time backtest evidence.",
                minimum_threshold="positive risk-adjusted result after costs",
            )
        ],
    }
    data.update(overrides)
    return StrategySpec(**data)


def test_strategy_spec_defaults_live_and_paper_trading_to_false() -> None:
    spec = build_valid_strategy()

    assert spec.eligible_for_research is True
    assert spec.eligible_for_backtesting is False
    assert spec.eligible_for_paper_trading is False
    assert spec.eligible_for_live_trading is False


@pytest.mark.parametrize("bad_id", ["", "Mean Reversion", "mean_reversion", "-starts-bad"])
def test_strategy_id_must_be_machine_friendly(bad_id: str) -> None:
    with pytest.raises(ValidationError):
        build_valid_strategy(strategy_id=bad_id)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("name", ""),
        ("thesis", ""),
        ("expected_edge", ""),
        ("signals", []),
        ("entry_rules", []),
        ("exit_rules", []),
        ("risk_rules", []),
        ("failure_conditions", []),
        ("evidence_required", []),
    ],
)
def test_missing_required_strategy_components_are_rejected(field_name: str, value: object) -> None:
    with pytest.raises(ValidationError):
        build_valid_strategy(**{field_name: value})


def test_live_trading_requires_paper_trading_eligibility() -> None:
    with pytest.raises(ValidationError, match="live trading eligibility requires"):
        build_valid_strategy(
            eligible_for_backtesting=True,
            eligible_for_paper_trading=False,
            eligible_for_live_trading=True,
        )


def test_paper_trading_requires_backtesting_eligibility() -> None:
    with pytest.raises(ValidationError, match="paper trading eligibility requires"):
        build_valid_strategy(eligible_for_paper_trading=True)


@pytest.mark.parametrize(
    "overrides",
    [
        {"asset_class": AssetClass.OPTIONS},
        {"asset_class": AssetClass.CRYPTO},
        {"horizon": TradingHorizon.INTRADAY},
        {"direction": StrategyDirection.SHORT_ONLY},
        {"uses_margin": True},
    ],
)
def test_future_only_scopes_cannot_be_promoted_to_paper_or_live(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="future-only"):
        build_valid_strategy(
            **overrides,
            eligible_for_backtesting=True,
            eligible_for_paper_trading=True,
        )
