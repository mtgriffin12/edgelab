from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from edgelab.backtesting.schema import BacktestRequest, ExecutionAssumptions


def test_execution_assumptions_validation() -> None:
    with pytest.raises(ValidationError):
        ExecutionAssumptions(initial_capital=0)

    with pytest.raises(ValidationError):
        ExecutionAssumptions(max_position_pct=1.5)

    with pytest.raises(ValidationError):
        ExecutionAssumptions(execution_timing="same_close")


def test_backtest_request_validation_and_symbol_normalization() -> None:
    request = BacktestRequest(strategy_id="relative-strength-pullback", symbol=" spy ")

    assert request.symbol == "SPY"


def test_backtest_request_rejects_invalid_window() -> None:
    with pytest.raises(ValidationError):
        BacktestRequest(
            strategy_id="relative-strength-pullback",
            symbol="SPY",
            start_timestamp=datetime(2024, 1, 5, tzinfo=UTC),
            end_timestamp=datetime(2024, 1, 2, tzinfo=UTC),
        )
