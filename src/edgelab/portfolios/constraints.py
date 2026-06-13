"""Deterministic model portfolio constraint checks."""

from __future__ import annotations

from edgelab.candidates.schema import CandidateStatus, EquityCandidate
from edgelab.portfolios.schema import (
    ModelPortfolio,
    PortfolioConstraintIssue,
    PortfolioConstraintIssueType,
    PortfolioHolding,
    PortfolioRiskLimits,
)

ETF_SYMBOLS = {"SPY", "QQQ"}


def check_portfolio_constraints(
    holdings: list[PortfolioHolding],
    cash_weight_pct: float,
    limits: PortfolioRiskLimits,
    *,
    included_candidates: list[EquityCandidate] | None = None,
) -> list[PortfolioConstraintIssue]:
    """Return structured constraint issues for a draft model portfolio."""

    issues: list[PortfolioConstraintIssue] = [
        PortfolioConstraintIssue(
            issue_type=PortfolioConstraintIssueType.FIXTURE_DATA_ONLY,
            message="This model uses fixture-only sample data.",
            severity="warning",
        )
    ]
    total_weight = cash_weight_pct + sum(holding.target_weight_pct for holding in holdings)
    if abs(total_weight - 100.0) > 0.05:
        issues.append(
            PortfolioConstraintIssue(
                issue_type=PortfolioConstraintIssueType.TARGET_WEIGHTS_DO_NOT_SUM_TO_100,
                message="Holding weights plus cash do not sum to 100%.",
                severity="error",
            )
        )
    if cash_weight_pct < limits.min_cash_weight_pct:
        issues.append(
            PortfolioConstraintIssue(
                issue_type=PortfolioConstraintIssueType.CASH_BELOW_MINIMUM,
                message="Cash is below the model portfolio minimum.",
                severity="error",
            )
        )
    if len(holdings) > limits.max_positions:
        issues.append(
            PortfolioConstraintIssue(
                issue_type=PortfolioConstraintIssueType.TOO_MANY_POSITIONS,
                message="The model includes more holdings than the limit allows.",
                severity="error",
            )
        )
    equity_exposure = sum(holding.target_weight_pct for holding in holdings)
    if equity_exposure > limits.max_total_equity_exposure_pct:
        issues.append(
            PortfolioConstraintIssue(
                issue_type=PortfolioConstraintIssueType.EQUITY_EXPOSURE_EXCEEDS_LIMIT,
                message="Total model equity exposure exceeds the configured limit.",
                severity="error",
            )
        )
    for holding in holdings:
        max_weight = (
            limits.max_etf_weight_pct
            if holding.symbol in ETF_SYMBOLS
            else limits.max_single_equity_weight_pct
        )
        if holding.target_weight_pct > max_weight:
            issues.append(
                PortfolioConstraintIssue(
                    issue_type=PortfolioConstraintIssueType.POSITION_EXCEEDS_LIMIT,
                    message=f"{holding.symbol} exceeds its maximum model weight.",
                    severity="error",
                    symbol=holding.symbol,
                )
            )
    candidates = included_candidates or []
    blocked_statuses = {
        CandidateStatus.BLOCKED_BY_RISK,
        CandidateStatus.BLOCKED_BY_DATA_QUALITY,
        CandidateStatus.REJECTED_FOR_NOW,
    }
    for candidate in candidates:
        if candidate.status in blocked_statuses:
            issues.append(
                PortfolioConstraintIssue(
                    issue_type=PortfolioConstraintIssueType.BLOCKED_CANDIDATE_INCLUDED,
                    message=f"{candidate.symbol} is blocked or rejected in candidate screening.",
                    severity="error",
                    symbol=candidate.symbol,
                )
            )
    if not holdings:
        issues.append(
            PortfolioConstraintIssue(
                issue_type=PortfolioConstraintIssueType.INSUFFICIENT_CANDIDATES,
                message="No holdings were available for this model portfolio.",
                severity="error",
            )
        )
    return issues


def portfolio_has_error_constraints(portfolio: ModelPortfolio) -> bool:
    """Return whether any constraint issue is blocking."""

    return any(issue.severity == "error" for issue in portfolio.constraint_issues)
