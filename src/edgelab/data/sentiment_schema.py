"""Normalized sentiment data models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


class SentimentSourceType(StrEnum):
    """Supported sentiment source categories."""

    FINANCIAL_NEWS = "financial_news"
    SOCIAL = "social"
    ANALYST_INSTITUTIONAL = "analyst_institutional"
    OPTIONS = "options"
    PRICE_VOLUME_IMPLIED = "price_volume_implied"
    MACRO_MARKET = "macro_market"


class SentimentEventType(StrEnum):
    """Initial sentiment event taxonomy."""

    EARNINGS_BEAT = "earnings_beat"
    EARNINGS_MISS = "earnings_miss"
    GUIDANCE_RAISE = "guidance_raise"
    GUIDANCE_CUT = "guidance_cut"
    ANALYST_UPGRADE = "analyst_upgrade"
    ANALYST_DOWNGRADE = "analyst_downgrade"
    PRICE_TARGET_RAISE = "price_target_raise"
    PRICE_TARGET_CUT = "price_target_cut"
    PRODUCT_LAUNCH = "product_launch"
    REGULATORY_ISSUE = "regulatory_issue"
    LITIGATION = "litigation"
    FRAUD_ACCOUNTING_CONCERN = "fraud_accounting_concern"
    M_AND_A_RUMOR = "m_and_a_rumor"
    M_AND_A_CONFIRMED = "m_and_a_confirmed"
    INSIDER_BUYING = "insider_buying"
    INSIDER_SELLING = "insider_selling"
    SHORT_SELLER_REPORT = "short_seller_report"
    MANAGEMENT_CHANGE = "management_change"
    MACRO_PRESSURE = "macro_pressure"
    SECTOR_ROTATION = "sector_rotation"
    FINANCING_DILUTION = "financing_dilution"
    DEBT_LIQUIDITY_ISSUE = "debt_liquidity_issue"
    DIVIDEND_BUYBACK = "dividend_buyback"
    SOCIAL_MANIA = "social_mania"
    SOCIAL_FEAR = "social_fear"
    PRICE_VOLUME_CONFIRMATION = "price_volume_confirmation"
    PRICE_VOLUME_DIVERGENCE = "price_volume_divergence"


class SentimentLabel(StrEnum):
    """Normalized sentiment labels."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    MIXED = "mixed"
    NEUTRAL = "neutral"


class SentimentDirection(StrEnum):
    """Directional context, not an action instruction."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"
    NEUTRAL = "neutral"


class SentimentEvent(BaseModel):
    """A timestamped sentiment event."""

    event_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    timestamp: datetime
    source_type: SentimentSourceType
    source_name: str = Field(min_length=1)
    event_type: SentimentEventType
    headline_or_summary: str = Field(min_length=1)
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    sentiment_label: SentimentLabel
    relevance_score: float = Field(ge=0.0, le=1.0)
    novelty_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    source_weight: float = Field(ge=0.0, le=1.0)
    mention_count: int | None = Field(default=None, ge=0)
    mention_velocity_zscore: float | None = None
    url_reference: str | None = None
    ingested_at: datetime
    allow_future_timestamp: bool = Field(default=False, exclude=True)

    @field_validator("event_id", "source_name", "headline_or_summary")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        """Strip text fields while preserving non-empty validation."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("required text fields must be non-empty")
        return stripped

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("symbol must be non-empty")
        return normalized

    @model_validator(mode="after")
    def validate_timestamp(self) -> Self:
        """Prevent future timestamps unless tests opt in explicitly."""

        if not self.allow_future_timestamp and _is_future(self.timestamp):
            raise ValueError("timestamp cannot be in the future")
        return self


class SentimentQualityIssue(BaseModel):
    """Structured sentiment quality issue."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    symbol: str | None = None
    event_id: str | None = None
    timestamp: datetime | None = None
    row_number: int | None = None
    severity: str = "error"


class SentimentSnapshot(BaseModel):
    """Ticker-level sentiment snapshot."""

    symbol: str
    as_of: datetime
    event_count: int
    weighted_sentiment_score: float
    decayed_sentiment_score: float
    dominant_event_type: SentimentEventType | None
    average_relevance: float | None
    average_confidence: float | None
    average_novelty: float | None
    mention_count_total: int
    max_mention_velocity_zscore: float | None
    sentiment_label: SentimentLabel
    trade_bias_context: str
    divergence_flags: list[str] = Field(default_factory=list)
    quality_issue_count: int


class SentimentSummary(BaseModel):
    """Summary of local sentiment fixture data."""

    symbol: str
    event_count: int
    start_timestamp: datetime | None
    end_timestamp: datetime | None
    source_types: list[SentimentSourceType]
    event_types: list[SentimentEventType]
    average_sentiment_score: float | None
    average_confidence: float | None
    quality_issue_count: int


def _is_future(value: datetime) -> bool:
    now = datetime.now(UTC)
    comparable = value if value.tzinfo else value.replace(tzinfo=UTC)
    return comparable > now
