from datetime import UTC, datetime

from edgelab.backtesting.metrics import (
    calculate_max_drawdown_pct,
    calculate_profit_factor,
    calculate_total_return_pct,
    calculate_win_rate_pct,
)
from edgelab.backtesting.schema import EquityCurvePoint


def test_total_return_calculation() -> None:
    assert calculate_total_return_pct(1000, 1100) == 10.000000000000009


def test_max_drawdown_calculation() -> None:
    curve = [
        EquityCurvePoint(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            cash=1000,
            position_quantity=0,
            position_market_value=0,
            equity=1000,
        ),
        EquityCurvePoint(
            timestamp=datetime(2024, 1, 2, tzinfo=UTC),
            cash=900,
            position_quantity=0,
            position_market_value=0,
            equity=900,
        ),
        EquityCurvePoint(
            timestamp=datetime(2024, 1, 3, tzinfo=UTC),
            cash=950,
            position_quantity=0,
            position_market_value=0,
            equity=950,
        ),
    ]

    assert calculate_max_drawdown_pct(curve) == 10.0


def test_flat_equity_curve_has_no_drawdown() -> None:
    curve = [
        EquityCurvePoint(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            cash=1000,
            position_quantity=0,
            position_market_value=0,
            equity=1000,
        )
    ]

    assert calculate_max_drawdown_pct(curve) == 0.0


def test_win_rate_and_profit_factor_edge_cases() -> None:
    assert calculate_win_rate_pct([]) == 0.0
    assert calculate_profit_factor([]) is None
