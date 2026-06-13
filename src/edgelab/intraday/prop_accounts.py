"""Generic prop-account-style research arithmetic."""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, model_validator


class PropAccountStage(StrEnum):
    """Generic account-stage labels."""

    EVALUATION = "evaluation"
    FUNDED_SIMULATED = "funded_simulated"
    LIVE_FUNDED_FUTURE_PLACEHOLDER = "live_funded_future_placeholder"


class PropAccountQualityIssue(BaseModel):
    """Quality issue for generic prop-account research."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: str = "warning"


class PropAccountRuleSet(BaseModel):
    """Generic prop-account-style rules, not a real firm rulebook."""

    account_size: float = Field(default=50000, gt=0)
    qualification_profit_target: float = Field(default=3000, gt=0)
    max_loss_limit: float = Field(default=2500, gt=0)
    daily_loss_limit: float | None = Field(default=1000, gt=0)
    consistency_rule_pct: float | None = Field(default=None, gt=0, le=100)
    payout_split_to_trader_pct: float = Field(default=90, gt=0, le=100)
    max_payout_count: int | None = Field(default=None, gt=0)
    max_active_accounts: int | None = Field(default=None, gt=0)


class PropAccountSimulationRequest(BaseModel):
    """Request for generic copied-account arithmetic."""

    rule_set: PropAccountRuleSet = Field(default_factory=PropAccountRuleSet)
    copied_account_count: int = Field(default=1, gt=0)
    daily_net_pnl_values: list[float] = Field(default_factory=list)
    starting_balance: float | None = Field(default=None, gt=0)


class CopiedAccountScenario(BaseModel):
    """One copied-account scenario."""

    account_count: int = Field(gt=0)
    copied_account_total_net_pnl: float
    payout_split_estimate: float
    plain_english_summary: str = Field(min_length=1)
    cautions: list[str] = Field(min_length=1)


class PropAccountSimulationResult(BaseModel):
    """Generic prop-account-style simulation output."""

    account_count: int = Field(gt=0)
    single_account_net_pnl: float
    copied_account_total_net_pnl: float
    qualification_target_reached: bool
    max_loss_breached: bool
    daily_loss_breached: bool
    consistency_warning: str | None = None
    payout_split_estimate: float
    scenarios: list[CopiedAccountScenario] = Field(default_factory=list)
    quality_issues: list[PropAccountQualityIssue] = Field(default_factory=list)
    plain_english_summary: str = Field(min_length=1)
    cautions: list[str] = Field(min_length=1)
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_real_money_status(self) -> Self:
        """Keep account modeling research-only."""

        if self.real_money_status != "Not allowed":
            raise ValueError("prop-account real-money status must be Not allowed")
        return self


class PropAccountSimulator:
    """Deterministic generic prop-account-style arithmetic."""

    def run(self, request: PropAccountSimulationRequest) -> PropAccountSimulationResult:
        """Run a generic copied-account simulation."""

        daily_values = request.daily_net_pnl_values or [600, 750, -350, 900, 1250]
        rule_set = request.rule_set
        single_account_net_pnl = sum(daily_values)
        copied_account_total_net_pnl = single_account_net_pnl * request.copied_account_count
        running_total = 0.0
        max_loss_breached = False
        for value in daily_values:
            running_total += value
            if running_total <= -rule_set.max_loss_limit:
                max_loss_breached = True
                break
        daily_loss_breached = (
            any(value <= -rule_set.daily_loss_limit for value in daily_values)
            if rule_set.daily_loss_limit is not None
            else False
        )
        qualification_target_reached = (
            single_account_net_pnl >= rule_set.qualification_profit_target
            and not max_loss_breached
            and not daily_loss_breached
        )
        consistency_warning = _consistency_warning(rule_set, daily_values)
        payout_split_estimate = (
            max(copied_account_total_net_pnl, 0) * rule_set.payout_split_to_trader_pct / 100
        )
        scenarios = [
            _scenario(account_count, single_account_net_pnl, rule_set)
            for account_count in [1, 5, 10, 20]
        ]
        cautions = [
            "Prop-account scaling is an economic multiplier, not a source of edge.",
            "Copying the same decision across accounts multiplies mistakes too.",
            "These generic assumptions may not match any real program.",
            "Real-money status: Not allowed.",
        ]
        summary = (
            "The sample sequence reached the generic target."
            if qualification_target_reached
            else "The sample sequence did not clear every generic account rule."
        )

        return PropAccountSimulationResult(
            account_count=request.copied_account_count,
            single_account_net_pnl=round(single_account_net_pnl, 2),
            copied_account_total_net_pnl=round(copied_account_total_net_pnl, 2),
            qualification_target_reached=qualification_target_reached,
            max_loss_breached=max_loss_breached,
            daily_loss_breached=daily_loss_breached,
            consistency_warning=consistency_warning,
            payout_split_estimate=round(payout_split_estimate, 2),
            scenarios=scenarios,
            plain_english_summary=summary,
            cautions=cautions,
        )


def sample_prop_account_result() -> PropAccountSimulationResult:
    """Return a default generic sample prop-account simulation."""

    return PropAccountSimulator().run(
        PropAccountSimulationRequest(
            copied_account_count=10,
            daily_net_pnl_values=[600, 750, -350, 900, 1250],
        )
    )


def _scenario(
    account_count: int, single_account_net_pnl: float, rule_set: PropAccountRuleSet
) -> CopiedAccountScenario:
    copied_pnl = single_account_net_pnl * account_count
    payout_estimate = max(copied_pnl, 0) * rule_set.payout_split_to_trader_pct / 100
    return CopiedAccountScenario(
        account_count=account_count,
        copied_account_total_net_pnl=round(copied_pnl, 2),
        payout_split_estimate=round(payout_estimate, 2),
        plain_english_summary=(
            f"{account_count} copied account(s) would multiply the same sample result."
        ),
        cautions=[
            "This does not create an edge.",
            "The same weak decision would be repeated across every copied account.",
        ],
    )


def _consistency_warning(rule_set: PropAccountRuleSet, daily_values: list[float]) -> str | None:
    if rule_set.consistency_rule_pct is None or not daily_values:
        return "Consistency rules are placeholders in this generic model."
    largest_day = max(daily_values)
    total = sum(value for value in daily_values if value > 0)
    if total <= 0:
        return "No positive sample total is available for consistency review."
    largest_pct = largest_day / total * 100
    if largest_pct > rule_set.consistency_rule_pct:
        return "One day contributes too much of the positive sample result."
    return None
