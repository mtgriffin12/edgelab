from edgelab.backtesting.schema import BacktestQualityIssue, BacktestResult, BacktestStatus
from edgelab.ranking.scoring import (
    score_backtest_result,
    score_data_quality,
    score_trade_sample_size,
    score_worst_drop_control,
)


def build_result(**overrides: object) -> BacktestResult:
    data: dict[str, object] = {
        "strategy_id": "sample",
        "symbol": "SPY",
        "status": BacktestStatus.COMPLETED,
        "initial_capital": 50_000,
        "final_equity": 51_000,
        "total_return_pct": 2.0,
        "max_drawdown_pct": 2.0,
        "trade_count": 10,
        "winning_trade_count": 6,
        "losing_trade_count": 4,
        "win_rate_pct": 60.0,
        "average_win_pct": 1.0,
        "average_loss_pct": -0.5,
        "profit_factor": 1.5,
        "exposure_pct": 40.0,
        "quality_issues": [],
        "assumptions_summary": {
            "commission_per_trade": 0.0,
            "slippage_bps": 0.0,
        },
    }
    data.update(overrides)
    return BacktestResult(**data)


def test_scoring_penalizes_large_worst_drop() -> None:
    low_drop = score_worst_drop_control(2.0)
    high_drop = score_worst_drop_control(25.0)

    assert high_drop.score < low_drop.score


def test_scoring_penalizes_too_few_sample_events() -> None:
    no_events = score_trade_sample_size(0)
    enough_events = score_trade_sample_size(30)

    assert no_events.score < enough_events.score


def test_scoring_penalizes_quality_issues() -> None:
    clean = score_data_quality(0)
    noisy = score_data_quality(3)

    assert noisy.score < clean.score


def test_total_return_alone_does_not_dominate_ranking() -> None:
    high_return_fragile = build_result(
        total_return_pct=100,
        max_drawdown_pct=50,
        trade_count=20,
        profit_factor=2,
    )
    moderate_return_controlled = build_result(
        total_return_pct=5,
        max_drawdown_pct=2,
        trade_count=20,
        profit_factor=2,
    )

    assert score_backtest_result(moderate_return_controlled) > score_backtest_result(
        high_return_fragile
    )


def test_unsupported_strategy_gets_heavy_penalty() -> None:
    result = build_result(
        status=BacktestStatus.UNSUPPORTED_STRATEGY,
        trade_count=0,
        quality_issues=[BacktestQualityIssue(code="unsupported_strategy", message="Unsupported.")],
    )

    assert score_backtest_result(result) <= 20
