from edgelab.portfolios.constraints import check_portfolio_constraints
from edgelab.portfolios.schema import (
    PortfolioConstraintIssueType,
    PortfolioEvidenceStrength,
    PortfolioHolding,
    PortfolioHoldingRole,
    PortfolioRiskLimits,
)


def build_holding(symbol: str = "AAPL", weight: float = 8.0) -> PortfolioHolding:
    return PortfolioHolding(
        holding_id=f"{symbol.lower()}-model-holding",
        symbol=symbol,
        display_name=f"{symbol} Model Holding",
        role=PortfolioHoldingRole.CORE_CANDIDATE,
        target_weight_pct=weight,
        target_value=50000 * weight / 100,
        evidence_strength=PortfolioEvidenceStrength.WEAK,
        plain_english_reason="Local research model holding.",
        why_included=["It has candidate context."],
        what_to_monitor=["Evidence strength."],
        what_would_make_us_reconsider=["Evidence weakens."],
    )


def test_cash_below_minimum_creates_constraint_issue() -> None:
    issues = check_portfolio_constraints([build_holding(weight=8)], 10, PortfolioRiskLimits())

    assert any(
        issue.issue_type == PortfolioConstraintIssueType.CASH_BELOW_MINIMUM for issue in issues
    )


def test_position_exceeding_limit_creates_constraint_issue() -> None:
    issues = check_portfolio_constraints([build_holding(weight=20)], 80, PortfolioRiskLimits())

    assert any(
        issue.issue_type == PortfolioConstraintIssueType.POSITION_EXCEEDS_LIMIT for issue in issues
    )


def test_equity_exposure_exceeding_limit_creates_constraint_issue() -> None:
    holdings = [build_holding("SPY", 35), build_holding("QQQ", 35), build_holding("AAPL", 8)]
    issues = check_portfolio_constraints(holdings, 22, PortfolioRiskLimits())

    assert any(
        issue.issue_type == PortfolioConstraintIssueType.EQUITY_EXPOSURE_EXCEEDS_LIMIT
        for issue in issues
    )


def test_weights_not_summing_to_100_creates_constraint_issue() -> None:
    issues = check_portfolio_constraints([build_holding(weight=8)], 50, PortfolioRiskLimits())

    assert any(
        issue.issue_type == PortfolioConstraintIssueType.TARGET_WEIGHTS_DO_NOT_SUM_TO_100
        for issue in issues
    )


def test_fixture_data_only_issue_is_always_present() -> None:
    issues = check_portfolio_constraints([build_holding(weight=8)], 92, PortfolioRiskLimits())

    assert any(
        issue.issue_type == PortfolioConstraintIssueType.FIXTURE_DATA_ONLY for issue in issues
    )
