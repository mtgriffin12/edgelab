from edgelab.strategies.samples import SAMPLE_STRATEGIES


def test_sample_strategies_load_successfully() -> None:
    assert len(SAMPLE_STRATEGIES) == 5
    assert {strategy.strategy_id for strategy in SAMPLE_STRATEGIES} == {
        "relative-strength-pullback",
        "earnings-drift-with-confirmation",
        "breakout-with-volume-confirmation",
        "oversold-mean-reversion-with-news-veto",
        "etf-risk-on-risk-off-rotation",
    }


def test_sample_strategies_are_not_paper_or_live_trading_eligible() -> None:
    for strategy in SAMPLE_STRATEGIES:
        assert strategy.eligible_for_paper_trading is False
        assert strategy.eligible_for_live_trading is False
