"""Research-only model portfolio schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


class PortfolioStyle(StrEnum):
    """Supported local model portfolio styles."""

    CORE_RESEARCH = "core_research"
    DEFENSIVE_RESEARCH = "defensive_research"
    OPPORTUNISTIC_RESEARCH = "opportunistic_research"
    STRATEGY_CHAMPIONS = "strategy_champions"
    BENCHMARK_COMPARISON = "benchmark_comparison"


class PortfolioStatus(StrEnum):
    """Research-only portfolio status."""

    RESEARCH_MODEL = "research_model"
    INCOMPLETE_MODEL = "incomplete_model"
    BLOCKED_BY_RISK = "blocked_by_risk"
    BLOCKED_BY_DATA_QUALITY = "blocked_by_data_quality"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    REFERENCE_ONLY = "reference_only"


class PortfolioMode(StrEnum):
    """Portfolio operation mode."""

    RESEARCH_ONLY = "research_only"
    FUTURE_APPROVAL_PAPER_MODE = "future_approval_paper_mode"
    FUTURE_AUTONOMOUS_PAPER_MODE = "future_autonomous_paper_mode"


class PortfolioHoldingRole(StrEnum):
    """Role of a model holding."""

    CORE_CANDIDATE = "core_candidate"
    SUPPORTING_CANDIDATE = "supporting_candidate"
    BROAD_MARKET_REFERENCE = "broad_market_reference"
    GROWTH_REFERENCE = "growth_reference"
    CASH_RESERVE = "cash_reserve"
    WATCHLIST_ONLY = "watchlist_only"


class PortfolioEvidenceStrength(StrEnum):
    """Portfolio evidence strength."""

    INSUFFICIENT = "insufficient"
    WEAK = "weak"
    MIXED = "mixed"
    MODERATE = "moderate"
    STRONG = "strong"


class PortfolioRiskFlagType(StrEnum):
    """Risk flags attached to holdings or portfolios."""

    SYNTHETIC_DATA_ONLY = "synthetic_data_only"
    TOO_CONCENTRATED = "too_concentrated"
    WEAK_CANDIDATE_EVIDENCE = "weak_candidate_evidence"
    BLOCKED_CANDIDATE = "blocked_candidate"
    INSUFFICIENT_HISTORY = "insufficient_history"
    UNSUPPORTED_STRATEGY_LOGIC = "unsupported_strategy_logic"
    FIXTURE_ONLY_PRICING = "fixture_only_pricing"
    REAL_MONEY_NOT_ALLOWED = "real_money_not_allowed"
    TOO_LITTLE_CASH = "too_little_cash"
    EXCEEDS_POSITION_LIMIT = "exceeds_position_limit"
    EXCEEDS_EQUITY_EXPOSURE_LIMIT = "exceeds_equity_exposure_limit"


class PortfolioConstraintIssueType(StrEnum):
    """Constraint issue types."""

    TARGET_WEIGHTS_DO_NOT_SUM_TO_100 = "target_weights_do_not_sum_to_100"
    POSITION_EXCEEDS_LIMIT = "position_exceeds_limit"
    EQUITY_EXPOSURE_EXCEEDS_LIMIT = "equity_exposure_exceeds_limit"
    CASH_BELOW_MINIMUM = "cash_below_minimum"
    TOO_MANY_POSITIONS = "too_many_positions"
    INSUFFICIENT_CANDIDATES = "insufficient_candidates"
    BLOCKED_CANDIDATE_INCLUDED = "blocked_candidate_included"
    FIXTURE_DATA_ONLY = "fixture_data_only"


class PortfolioRiskFlag(BaseModel):
    """Plain-English portfolio or holding risk flag."""

    flag_type: PortfolioRiskFlagType
    message: str = Field(min_length=1)
    severity: str = "warning"


class PortfolioConstraintIssue(BaseModel):
    """Structured model portfolio constraint issue."""

    issue_type: PortfolioConstraintIssueType
    message: str = Field(min_length=1)
    severity: str = "warning"
    symbol: str | None = None


class PortfolioQualityIssue(BaseModel):
    """Structured model portfolio quality issue."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: str = "warning"


class PortfolioHolding(BaseModel):
    """A hypothetical model holding."""

    holding_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    role: PortfolioHoldingRole
    candidate_id: str | None = None
    target_weight_pct: float = Field(ge=0, le=100)
    target_value: float = Field(ge=0)
    evidence_strength: PortfolioEvidenceStrength
    candidate_score: float | None = Field(default=None, ge=0, le=100)
    linked_strategy_ids: list[str] = Field(default_factory=list)
    linked_discovery_ids: list[str] = Field(default_factory=list)
    linked_scorecard_ids: list[str] = Field(default_factory=list)
    plain_english_reason: str = Field(min_length=1)
    why_included: list[str] = Field(min_length=1)
    what_to_monitor: list[str] = Field(min_length=1)
    what_would_make_us_reconsider: list[str] = Field(min_length=1)
    risk_flags: list[PortfolioRiskFlag] = Field(default_factory=list)
    real_money_status: str = "Not allowed"

    @field_validator("holding_id")
    @classmethod
    def validate_holding_id(cls, value: str) -> str:
        """Require machine-friendly holding IDs."""

        return _machine_friendly(value, "holding_id")

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """Normalize symbols."""

        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("symbol must be non-empty")
        return normalized

    @model_validator(mode="after")
    def validate_research_only_holding(self) -> Self:
        """Keep holdings research-only."""

        if self.real_money_status != "Not allowed":
            raise ValueError("holding real-money status must be Not allowed")
        if _contains_forbidden_instruction(_holding_text(self)):
            raise ValueError("holding text must not contain action instructions")
        return self


class CashAllocation(BaseModel):
    """Explicit cash allocation."""

    target_weight_pct: float = Field(ge=0, le=100)
    target_value: float = Field(ge=0)
    plain_english_reason: str = Field(min_length=1)


class PortfolioRiskLimits(BaseModel):
    """Deterministic model portfolio limits."""

    initial_capital: float = Field(default=50000, gt=0)
    max_single_equity_weight_pct: float = Field(default=8, gt=0, le=100)
    max_etf_weight_pct: float = Field(default=35, gt=0, le=100)
    max_total_equity_exposure_pct: float = Field(default=75, gt=0, le=100)
    min_cash_weight_pct: float = Field(default=20, ge=0, le=100)
    max_positions: int = Field(default=10, gt=0)
    max_portfolio_worst_drop_pct: float = Field(default=15, gt=0, le=100)


class PortfolioMonitoringNote(BaseModel):
    """Future review note, not an action instruction."""

    note_id: str = Field(min_length=1)
    portfolio_id: str = Field(min_length=1)
    symbol: str | None = None
    severity: str = Field(pattern="^(info|caution|warning)$")
    plain_english_note: str = Field(min_length=1)
    what_to_watch: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    future_review_trigger: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_note_text(self) -> Self:
        """Reject instruction-like monitoring text."""

        text = " ".join(
            [
                self.plain_english_note,
                self.what_to_watch,
                self.why_it_matters,
                self.future_review_trigger,
            ]
        )
        if _contains_forbidden_instruction(text):
            raise ValueError("monitoring notes must not contain action instructions")
        return self


class ModelPortfolio(BaseModel):
    """A local hypothetical research model portfolio."""

    portfolio_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    style: PortfolioStyle
    mode: PortfolioMode = PortfolioMode.RESEARCH_ONLY
    status: PortfolioStatus
    evidence_strength: PortfolioEvidenceStrength
    initial_capital: float = Field(gt=0)
    target_equity_exposure_pct: float = Field(ge=0, le=100)
    target_cash: CashAllocation
    holdings: list[PortfolioHolding]
    risk_limits: PortfolioRiskLimits
    constraint_issues: list[PortfolioConstraintIssue] = Field(default_factory=list)
    monitoring_notes: list[PortfolioMonitoringNote] = Field(default_factory=list)
    quality_issues: list[PortfolioQualityIssue] = Field(default_factory=list)
    plain_english_summary: str = Field(min_length=1)
    why_this_portfolio_exists: str = Field(min_length=1)
    what_supports_it: list[str] = Field(min_length=1)
    what_is_missing: list[str] = Field(min_length=1)
    what_would_change_our_mind: list[str] = Field(min_length=1)
    real_money_status: str = "Not allowed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("portfolio_id")
    @classmethod
    def validate_portfolio_id(cls, value: str) -> str:
        """Require machine-friendly portfolio IDs."""

        return _machine_friendly(value, "portfolio_id")

    @model_validator(mode="after")
    def validate_model_portfolio(self) -> Self:
        """Validate conservative portfolio construction rules."""

        if self.mode != PortfolioMode.RESEARCH_ONLY:
            raise ValueError("only research_only mode is active in this phase")
        if self.real_money_status != "Not allowed":
            raise ValueError("portfolio real-money status must be Not allowed")
        total_weight = self.target_cash.target_weight_pct + sum(
            holding.target_weight_pct for holding in self.holdings
        )
        if abs(total_weight - 100.0) > 0.05:
            raise ValueError("holdings plus cash must sum to approximately 100%")
        if (
            self.status == PortfolioStatus.BLOCKED_BY_RISK
            and not self.constraint_issues
            and not any(holding.risk_flags for holding in self.holdings)
        ):
            raise ValueError("risk-blocked portfolios must include risk evidence")
        if self.status == PortfolioStatus.BLOCKED_BY_DATA_QUALITY and not self.quality_issues:
            raise ValueError("data-quality-blocked portfolios must include quality issues")
        if (
            self.evidence_strength == PortfolioEvidenceStrength.INSUFFICIENT
            and self.status == PortfolioStatus.RESEARCH_MODEL
        ):
            raise ValueError("insufficient evidence cannot be a research model")
        if self.target_cash.target_weight_pct < self.risk_limits.min_cash_weight_pct and not any(
            issue.issue_type == PortfolioConstraintIssueType.CASH_BELOW_MINIMUM
            for issue in self.constraint_issues
        ):
            raise ValueError("cash below minimum requires a constraint issue")
        if any(_holding_exceeds_limit(holding, self.risk_limits) for holding in self.holdings):
            if not any(
                issue.issue_type == PortfolioConstraintIssueType.POSITION_EXCEEDS_LIMIT
                for issue in self.constraint_issues
            ):
                raise ValueError("position limit breaches require a constraint issue")
        if _contains_forbidden_instruction(_portfolio_text(self)):
            raise ValueError("portfolio text must not contain action instructions")
        return self


class PortfolioConstructionRequest(BaseModel):
    """Request for local model portfolio construction."""

    style: PortfolioStyle | None = None
    initial_capital: float = Field(default=50000, gt=0)
    max_positions: int | None = Field(default=None, gt=0)
    min_candidate_score: float | None = Field(default=None, ge=0, le=100)
    include_watchlist_only: bool = False
    include_benchmark_portfolio: bool = True


class PortfolioConstructionResult(BaseModel):
    """Model portfolio construction result."""

    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC))
    initial_capital: float = Field(gt=0)
    portfolio_count: int = Field(ge=0)
    portfolios: list[ModelPortfolio]
    rejected_candidate_count: int = Field(ge=0)
    quality_issues: list[PortfolioQualityIssue] = Field(default_factory=list)
    plain_english_summary: str = Field(min_length=1)


def _machine_friendly(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-_")
    if normalized.lower() != normalized or any(
        character not in allowed for character in normalized
    ):
        raise ValueError(f"{field_name} must be machine-friendly")
    return normalized


def _holding_exceeds_limit(holding: PortfolioHolding, limits: PortfolioRiskLimits) -> bool:
    if holding.symbol in {"SPY", "QQQ"}:
        return holding.target_weight_pct > limits.max_etf_weight_pct
    return holding.target_weight_pct > limits.max_single_equity_weight_pct


def _contains_forbidden_instruction(text: str) -> bool:
    lowered = text.lower()
    forbidden_phrases = [
        "buy now",
        "sell now",
        "short now",
        "place an order",
        "submit an order",
        "execute a trade",
        "open a trade",
        "enter a trade",
        "trade now",
        "ready for real money",
        "approved for real money",
    ]
    return any(phrase in lowered for phrase in forbidden_phrases)


def _holding_text(holding: PortfolioHolding) -> str:
    return " ".join(
        [
            holding.display_name,
            holding.plain_english_reason,
            " ".join(holding.why_included),
            " ".join(holding.what_to_monitor),
            " ".join(holding.what_would_make_us_reconsider),
            " ".join(flag.message for flag in holding.risk_flags),
        ]
    )


def _portfolio_text(portfolio: ModelPortfolio) -> str:
    return " ".join(
        [
            portfolio.name,
            portfolio.plain_english_summary,
            portfolio.why_this_portfolio_exists,
            " ".join(portfolio.what_supports_it),
            " ".join(portfolio.what_is_missing),
            " ".join(portfolio.what_would_change_our_mind),
            portfolio.target_cash.plain_english_reason,
            " ".join(_holding_text(holding) for holding in portfolio.holdings),
            " ".join(issue.message for issue in portfolio.constraint_issues),
            " ".join(issue.message for issue in portfolio.quality_issues),
        ]
    )
