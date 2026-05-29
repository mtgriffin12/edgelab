"""Strategy ranking schemas for local research evidence."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, model_validator


class EvidenceStrength(StrEnum):
    """Plain evidence strength labels."""

    INSUFFICIENT = "insufficient"
    WEAK = "weak"
    MIXED = "mixed"
    MODERATE = "moderate"
    STRONG = "strong"


class RankingConclusion(StrEnum):
    """Research-only ranking conclusions."""

    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    WEAK_EVIDENCE = "weak_evidence"
    INTERESTING_BUT_FRAGILE = "interesting_but_fragile"
    BEATS_BASELINE_IN_SAMPLE = "beats_baseline_in_sample"
    NEEDS_MORE_TESTING = "needs_more_testing"
    PROMISING_RESEARCH_CANDIDATE = "promising_research_candidate"
    REJECTED_FOR_NOW = "rejected_for_now"
    UNSUPPORTED = "unsupported"


class RankingDimension(StrEnum):
    """Dimensions that contribute to a scorecard."""

    RETURN_QUALITY = "return_quality"
    WORST_DROP_CONTROL = "worst_drop_control"
    CONSISTENCY = "consistency"
    BASELINE_ADVANTAGE = "baseline_advantage"
    TRADE_SAMPLE_SIZE = "trade_sample_size"
    COST_SENSITIVITY = "cost_sensitivity"
    SIMPLICITY = "simplicity"
    CURRENT_REGIME_FIT = "current_regime_fit"
    SENTIMENT_CONTEXT = "sentiment_context"
    OVERFITTING_RISK = "overfitting_risk"
    DATA_QUALITY = "data_quality"


class MetricScore(BaseModel):
    """One scored ranking dimension."""

    dimension: RankingDimension
    score: float = Field(ge=0, le=100)
    plain_english_reason: str = Field(min_length=1)


class BaselineComparisonResult(BaseModel):
    """Research-only baseline comparison summary."""

    candidate_id: str = Field(min_length=1)
    baseline_id: str | None = None
    baseline_description: str = Field(min_length=1)
    candidate_result_summary: str = Field(min_length=1)
    baseline_result_summary: str = Field(min_length=1)
    did_candidate_beat_baseline: bool
    improvement_summary: str = Field(min_length=1)
    caution: str = Field(min_length=1)
    evidence_strength: EvidenceStrength


class RankingQualityIssue(BaseModel):
    """Structured ranking caution."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: str = "warning"


class StrategyScorecard(BaseModel):
    """Plain-English scorecard for a strategy or discovery idea."""

    scorecard_id: str = Field(min_length=1)
    strategy_id: str | None = None
    discovery_id: str | None = None
    title: str = Field(min_length=1)
    evidence_strength: EvidenceStrength
    conclusion: RankingConclusion
    overall_score: float = Field(ge=0, le=100)
    dimension_scores: list[MetricScore] = Field(default_factory=list)
    baseline_comparison: BaselineComparisonResult | None = None
    plain_english_summary: str = Field(min_length=1)
    why_it_ranked_this_way: list[str] = Field(min_length=1)
    what_helped: list[str] = Field(default_factory=list)
    what_hurt: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    caution: str = Field(min_length=1)
    not_ready_reasons: list[str] = Field(default_factory=list)
    quality_issues: list[RankingQualityIssue] = Field(default_factory=list)
    real_money_status: str = "Not allowed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_research_only_text(self) -> Self:
        """Keep scorecards conservative and research-only."""

        if (
            self.evidence_strength == EvidenceStrength.INSUFFICIENT
            and self.conclusion == RankingConclusion.PROMISING_RESEARCH_CANDIDATE
        ):
            raise ValueError("insufficient evidence cannot produce a promising conclusion")
        if self.real_money_status != "Not allowed":
            raise ValueError("real-money use is not allowed in ranking scorecards")
        combined_text = " ".join(
            [
                self.title,
                self.plain_english_summary,
                " ".join(self.why_it_ranked_this_way),
                " ".join(self.what_helped),
                " ".join(self.what_hurt),
                " ".join(self.evidence_gaps),
                self.caution,
                " ".join(self.not_ready_reasons),
            ]
        ).lower()
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
            "real-money use is allowed",
            "ready for real money",
        ]
        if any(phrase in combined_text for phrase in forbidden_phrases):
            raise ValueError("scorecards must not contain action instructions")
        return self


class RankingRequest(BaseModel):
    """Request for local sample ranking generation."""

    include_strategies: bool = True
    include_discovery_records: bool = True
    symbol: str = "SPY"

    @model_validator(mode="after")
    def normalize_symbol(self) -> Self:
        """Normalize the fixture symbol."""

        self.symbol = self.symbol.strip().upper()
        if not self.symbol:
            raise ValueError("symbol must be non-empty")
        return self


class RankingResult(BaseModel):
    """Sorted local ranking output."""

    request: RankingRequest
    scorecards: list[StrategyScorecard]
    top_research_candidates: list[StrategyScorecard]
    weak_candidates: list[StrategyScorecard]
    quality_issues: list[RankingQualityIssue] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
