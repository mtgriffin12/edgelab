import pytest
from pydantic import ValidationError

from edgelab.portfolios.schema import (
    CashAllocation,
    ModelPortfolio,
    PortfolioConstraintIssue,
    PortfolioConstraintIssueType,
    PortfolioEvidenceStrength,
    PortfolioHolding,
    PortfolioHoldingRole,
    PortfolioRiskLimits,
    PortfolioStatus,
    PortfolioStyle,
)


def build_holding(**overrides: object) -> PortfolioHolding:
    data: dict[str, object] = {
        "holding_id": "aapl-model-holding",
        "symbol": "aapl",
        "display_name": "AAPL Model Holding",
        "role": PortfolioHoldingRole.CORE_CANDIDATE,
        "target_weight_pct": 8.0,
        "target_value": 4000.0,
        "evidence_strength": PortfolioEvidenceStrength.WEAK,
        "plain_english_reason": "AAPL appears in the local candidate screen.",
        "why_included": ["It has local candidate context."],
        "what_to_monitor": ["Candidate evidence strength."],
        "what_would_make_us_reconsider": ["Candidate evidence weakens."],
    }
    data.update(overrides)
    return PortfolioHolding(**data)


def build_portfolio(**overrides: object) -> ModelPortfolio:
    data: dict[str, object] = {
        "portfolio_id": "sample-model-portfolio",
        "name": "Sample Model Portfolio",
        "style": PortfolioStyle.CORE_RESEARCH,
        "status": PortfolioStatus.RESEARCH_MODEL,
        "evidence_strength": PortfolioEvidenceStrength.WEAK,
        "initial_capital": 50000.0,
        "target_equity_exposure_pct": 8.0,
        "target_cash": CashAllocation(
            target_weight_pct=92.0,
            target_value=46000.0,
            plain_english_reason="Cash is intentional while evidence is thin.",
        ),
        "holdings": [build_holding()],
        "risk_limits": PortfolioRiskLimits(),
        "plain_english_summary": "A local research model.",
        "why_this_portfolio_exists": "It tests construction behavior.",
        "what_supports_it": ["Built from local candidates."],
        "what_is_missing": ["Real historical provider data."],
        "what_would_change_our_mind": ["Candidate evidence weakens."],
    }
    data.update(overrides)
    return ModelPortfolio(**data)


def test_holding_normalizes_symbol_and_defaults_real_money_status() -> None:
    holding = build_holding()

    assert holding.symbol == "AAPL"
    assert holding.real_money_status == "Not allowed"


def test_holding_requires_weight_bounds() -> None:
    with pytest.raises(ValidationError):
        build_holding(target_weight_pct=101)


def test_portfolio_weights_plus_cash_must_sum_to_100() -> None:
    with pytest.raises(ValidationError, match="sum to approximately 100"):
        build_portfolio(
            target_cash=CashAllocation(
                target_weight_pct=80,
                target_value=40000,
                plain_english_reason="Cash is intentional.",
            )
        )


def test_portfolio_real_money_status_defaults_to_not_allowed() -> None:
    portfolio = build_portfolio()

    assert portfolio.real_money_status == "Not allowed"


def test_portfolio_rejects_real_money_permission() -> None:
    with pytest.raises(ValidationError, match="real-money status"):
        build_portfolio(real_money_status="Allowed")


def test_blocked_by_risk_requires_constraint_or_risk_evidence() -> None:
    with pytest.raises(ValidationError, match="risk evidence"):
        build_portfolio(status=PortfolioStatus.BLOCKED_BY_RISK)


def test_cash_below_minimum_requires_constraint_issue() -> None:
    with pytest.raises(ValidationError, match="cash below minimum"):
        build_portfolio(
            target_cash=CashAllocation(
                target_weight_pct=10,
                target_value=5000,
                plain_english_reason="Cash is too low.",
            ),
            holdings=[build_holding(target_weight_pct=90, target_value=45000)],
            target_equity_exposure_pct=90,
        )


def test_position_exceeding_limit_requires_constraint_issue() -> None:
    with pytest.raises(ValidationError, match="position limit"):
        build_portfolio(
            target_cash=CashAllocation(
                target_weight_pct=80,
                target_value=40000,
                plain_english_reason="Cash is intentional.",
            ),
            holdings=[build_holding(target_weight_pct=20, target_value=10000)],
            target_equity_exposure_pct=20,
        )


def test_portfolio_accepts_matching_constraint_issue() -> None:
    portfolio = build_portfolio(
        target_cash=CashAllocation(
            target_weight_pct=80,
            target_value=40000,
            plain_english_reason="Cash is intentional.",
        ),
        holdings=[build_holding(target_weight_pct=20, target_value=10000)],
        target_equity_exposure_pct=20,
        constraint_issues=[
            PortfolioConstraintIssue(
                issue_type=PortfolioConstraintIssueType.POSITION_EXCEEDS_LIMIT,
                message="AAPL exceeds its maximum model weight.",
                severity="error",
                symbol="AAPL",
            )
        ],
        status=PortfolioStatus.BLOCKED_BY_RISK,
    )

    assert portfolio.constraint_issues


def test_portfolio_rejects_action_instruction_phrases() -> None:
    with pytest.raises(ValidationError, match="action instructions"):
        build_portfolio(plain_english_summary="buy now")
