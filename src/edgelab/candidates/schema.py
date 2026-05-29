"""Research-only candidate equity screener schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


class CandidateSource(StrEnum):
    """Local evidence sources that can support a candidate."""

    STRATEGY_MATCH = "strategy_match"
    DISCOVERY_IDEA_MATCH = "discovery_idea_match"
    RANKING_MATCH = "ranking_match"
    MARKET_DATA_FIXTURE = "market_data_fixture"
    SENTIMENT_FIXTURE = "sentiment_fixture"


class CandidateStatus(StrEnum):
    """Conservative research-only candidate status."""

    RESEARCH_CANDIDATE = "research_candidate"
    WATCHLIST_ONLY = "watchlist_only"
    INTERESTING_BUT_INCOMPLETE = "interesting_but_incomplete"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    BLOCKED_BY_RISK = "blocked_by_risk"
    BLOCKED_BY_DATA_QUALITY = "blocked_by_data_quality"
    REJECTED_FOR_NOW = "rejected_for_now"


class CandidateEvidenceStrength(StrEnum):
    """Plain evidence strength for an equity candidate."""

    INSUFFICIENT = "insufficient"
    WEAK = "weak"
    MIXED = "mixed"
    MODERATE = "moderate"
    STRONG = "strong"


class CandidateRiskFlagType(StrEnum):
    """Research cautions that can block or weaken a candidate."""

    SYNTHETIC_DATA_ONLY = "synthetic_data_only"
    LOW_TRADE_SAMPLE = "low_trade_sample"
    UNSUPPORTED_STRATEGY_LOGIC = "unsupported_strategy_logic"
    WEAK_SENTIMENT_CONTEXT = "weak_sentiment_context"
    CONFLICTING_SENTIMENT_CONTEXT = "conflicting_sentiment_context"
    POOR_MARKET_DATA_QUALITY = "poor_market_data_quality"
    TOO_MUCH_WORST_DROP = "too_much_worst_drop"
    INSUFFICIENT_HISTORY = "insufficient_history"
    NO_BASELINE_PROOF = "no_baseline_proof"
    REAL_MONEY_NOT_ALLOWED = "real_money_not_allowed"


class CandidateReason(BaseModel):
    """One plain-English reason a symbol was surfaced."""

    source: CandidateSource
    summary: str = Field(min_length=1)
    related_id: str | None = None
    weight: float = Field(default=1.0, ge=0.0, le=1.0)


class CandidateRiskFlag(BaseModel):
    """Structured candidate caution."""

    flag_type: CandidateRiskFlagType
    message: str = Field(min_length=1)
    severity: str = "warning"


class CandidateQualityIssue(BaseModel):
    """Candidate-level quality issue."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: str = "warning"


class CandidateMarketSnapshot(BaseModel):
    """Small market fixture summary attached to a candidate."""

    symbol: str = Field(min_length=1)
    row_count: int = Field(ge=0)
    start_timestamp: datetime | None
    end_timestamp: datetime | None
    latest_close: float | None = Field(default=None, gt=0)
    min_close: float | None = Field(default=None, gt=0)
    max_close: float | None = Field(default=None, gt=0)
    total_volume: int = Field(ge=0)
    quality_issue_count: int = Field(ge=0)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("symbol must be non-empty")
        return normalized


class CandidateSentimentSnapshot(BaseModel):
    """Small sentiment fixture summary attached to a candidate."""

    symbol: str = Field(min_length=1)
    event_count: int = Field(ge=0)
    weighted_sentiment_score: float
    decayed_sentiment_score: float
    sentiment_label: str = Field(min_length=1)
    trade_bias_context: str = Field(min_length=1)
    divergence_flags: list[str] = Field(default_factory=list)
    quality_issue_count: int = Field(ge=0)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("symbol must be non-empty")
        return normalized


class EquityCandidate(BaseModel):
    """A local, research-only equity candidate."""

    candidate_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    title: str = Field(min_length=1)
    status: CandidateStatus
    evidence_strength: CandidateEvidenceStrength
    candidate_score: float = Field(ge=0, le=100)
    plain_english_summary: str = Field(min_length=1)
    what_supports_it: list[CandidateReason] = Field(min_length=1)
    what_is_missing: list[str] = Field(min_length=1)
    what_would_change_our_mind: list[str] = Field(min_length=1)
    matched_strategy_ids: list[str] = Field(default_factory=list)
    matched_discovery_ids: list[str] = Field(default_factory=list)
    matched_scorecard_ids: list[str] = Field(default_factory=list)
    market_snapshot: CandidateMarketSnapshot | None = None
    sentiment_snapshot: CandidateSentimentSnapshot | None = None
    risk_flags: list[CandidateRiskFlag] = Field(default_factory=list)
    quality_issues: list[CandidateQualityIssue] = Field(default_factory=list)
    real_money_status: str = "Not allowed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("candidate_id")
    @classmethod
    def validate_candidate_id(cls, value: str) -> str:
        """Require a machine-friendly candidate ID."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("candidate_id must be non-empty")
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-_")
        if normalized.lower() != normalized or any(
            character not in allowed for character in normalized
        ):
            raise ValueError("candidate_id must be machine-friendly")
        return normalized

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("symbol must be non-empty")
        return normalized

    @model_validator(mode="after")
    def validate_research_only_candidate(self) -> Self:
        """Keep candidate output conservative and research-only."""

        if self.real_money_status != "Not allowed":
            raise ValueError("candidate real-money status must be Not allowed")
        if (
            self.evidence_strength == CandidateEvidenceStrength.INSUFFICIENT
            and self.status == CandidateStatus.RESEARCH_CANDIDATE
        ):
            raise ValueError("insufficient evidence cannot be a research candidate")
        if self.status == CandidateStatus.BLOCKED_BY_RISK and not self.risk_flags:
            raise ValueError("risk-blocked candidates must include risk flags")
        if self.status == CandidateStatus.BLOCKED_BY_DATA_QUALITY and not self.quality_issues:
            raise ValueError("data-quality-blocked candidates must include quality issues")
        combined_text = " ".join(
            [
                self.title,
                self.plain_english_summary,
                " ".join(reason.summary for reason in self.what_supports_it),
                " ".join(self.what_is_missing),
                " ".join(self.what_would_change_our_mind),
                " ".join(flag.message for flag in self.risk_flags),
                " ".join(issue.message for issue in self.quality_issues),
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
            "ready for real money",
            "approved for real money",
        ]
        if any(phrase in combined_text for phrase in forbidden_phrases):
            raise ValueError("candidate output must not contain action instructions")
        return self


class CandidateScreeningRequest(BaseModel):
    """Request for the local candidate screener."""

    symbols: list[str] | None = None
    min_score: float = Field(default=0.0, ge=0.0, le=100.0)
    include_watchlist_only: bool = True
    include_rejected: bool = False

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, value: list[str] | None) -> list[str] | None:
        """Normalize requested symbols."""

        if value is None:
            return None
        normalized = [symbol.strip().upper() for symbol in value if symbol.strip()]
        if not normalized:
            raise ValueError("symbols must include at least one non-empty symbol")
        return sorted(set(normalized))


class CandidateScreeningResult(BaseModel):
    """Sorted local candidate screening output."""

    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC))
    universe_size: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    candidates: list[EquityCandidate]
    rejected_count: int = Field(ge=0)
    quality_issues: list[CandidateQualityIssue] = Field(default_factory=list)
    plain_english_summary: str = Field(min_length=1)
