from edgelab.strategies.schema import (
    StrategySignal,
    StrategySpec,
    StrategyUniverse,
)


def test_strategy_spec_defaults_live_trading_to_false() -> None:
    spec = StrategySpec(
        strategy_id="mean-reversion-placeholder",
        name="Mean Reversion Placeholder",
        description="A testable placeholder strategy.",
        universe=StrategyUniverse(symbols=["SPY"]),
        signals=[
            StrategySignal(
                name="Oversold",
                description="Placeholder oversold condition.",
                inputs=["close"],
                rule="close below placeholder threshold",
            )
        ],
        entry_rule="Enter only after a validated signal.",
        exit_rule="Exit on a validated reversal or timeout.",
        position_sizing_rule="Use placeholder fixed fractional sizing.",
        holding_period="daily to multi-day swing",
        expected_edge="Unknown until backtested.",
        failure_conditions=["No evidence yet."],
    )

    assert spec.eligible_for_paper_trading is False
    assert spec.eligible_for_live_trading is False
