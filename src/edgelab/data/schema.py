"""Normalized market-data models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class AssetType(StrEnum):
    """Supported local research asset types."""

    EQUITY = "equity"
    ETF = "etf"


class BarInterval(StrEnum):
    """Supported bar intervals for fixture data."""

    DAILY = "1d"


class AssetIdentifier(BaseModel):
    """Normalized asset identity."""

    symbol: str = Field(min_length=1)
    asset_type: AssetType
    name: str | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("symbol must be non-empty")
        return normalized


class OHLCVBar(BaseModel):
    """Normalized point-in-time OHLCV bar."""

    symbol: str = Field(min_length=1)
    timestamp: datetime
    interval: BarInterval
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)
    adjusted_close: float | None = Field(default=None, gt=0)
    source: str = Field(min_length=1)
    ingested_at: datetime
    allow_future_timestamp: bool = Field(default=False, exclude=True)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("symbol must be non-empty")
        return normalized

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        """Require non-empty source labels."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("source must be non-empty")
        return normalized

    @model_validator(mode="after")
    def validate_bar_relationships(self) -> OHLCVBar:
        """Validate OHLC relationships and future timestamp guard."""

        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be greater than or equal to open, close, and low")

        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be less than or equal to open, close, and high")

        if not self.allow_future_timestamp and _is_future(self.timestamp):
            raise ValueError("timestamp cannot be in the future")

        return self


class CorporateAction(BaseModel):
    """Placeholder model for future point-in-time corporate actions."""

    symbol: str = Field(min_length=1)
    timestamp: datetime
    action_type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    source: str = Field(min_length=1)


class MarketDataQualityIssue(BaseModel):
    """Structured market-data quality issue."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    symbol: str | None = None
    timestamp: datetime | None = None
    interval: BarInterval | None = None
    row_number: int | None = None
    severity: str = "error"


class MarketDataSet(BaseModel):
    """Loaded bars plus quality issues."""

    symbol: str
    bars: list[OHLCVBar] = Field(default_factory=list)
    quality_issues: list[MarketDataQualityIssue] = Field(default_factory=list)


class MarketDataSummary(BaseModel):
    """Summary of a loaded market-data set."""

    symbol: str
    row_count: int
    start_timestamp: datetime | None
    end_timestamp: datetime | None
    interval: BarInterval | None
    min_close: float | None
    max_close: float | None
    total_volume: int
    quality_issue_count: int


def _is_future(value: datetime) -> bool:
    now = datetime.now(UTC)
    comparable = value if value.tzinfo else value.replace(tzinfo=UTC)
    return comparable > now
