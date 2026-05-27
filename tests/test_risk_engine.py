from edgelab.risk.engine import evaluate_basic_risk


def test_risk_engine_rejects_live_trading_mode() -> None:
    decision = evaluate_basic_risk("live")

    assert decision.allowed is False
    assert decision.mode == "live"
    assert "Live trading is disabled in Phase 0." in decision.reasons


def test_risk_engine_allows_research_placeholder_mode() -> None:
    decision = evaluate_basic_risk("research")

    assert decision.allowed is True
    assert decision.mode == "research"
