"""Historical intraday import schemas for local research data."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from edgelab.intraday.schema import (
    IntradayBarInterval,
    IntradayInstrumentType,
    IntradaySessionType,
    normalize_symbol,
)


class HistoricalIntradayAdjustmentMode(StrEnum):
    """Supported historical bar adjustment modes."""

    UNADJUSTED = "unadjusted"
    ADJUSTED = "adjusted"
    SPLIT_ADJUSTED = "split_adjusted"
    UNKNOWN = "unknown"


class HistoricalIntradayProviderType(StrEnum):
    """Supported historical intraday provider categories."""

    LOCAL_CSV = "local_csv"
    FUTURE_PAID_PROVIDER_PLACEHOLDER = "future_paid_provider_placeholder"


class HistoricalIntradayReadiness(StrEnum):
    """Readiness for future replay inspection."""

    READY_FOR_REPLAY = "ready_for_replay"
    INCOMPLETE = "incomplete"
    UNUSABLE = "unusable"
    NEEDS_REVIEW = "needs_review"


class HistoricalIntradayQualityIssue(BaseModel):
    """Structured quality issue for historical intraday imports."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: str = "warning"
    symbol: str | None = None
    session_id: str | None = None
    row_number: int | None = None
    timestamp_utc: datetime | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_optional_symbol(cls, value: str | None) -> str | None:
        """Normalize optional symbols."""

        if value is None:
            return None
        return normalize_symbol(value)

    @field_validator("timestamp_utc")
    @classmethod
    def normalize_optional_timestamp(cls, value: datetime | None) -> datetime | None:
        """Normalize optional timestamps to UTC."""

        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class HistoricalIntradayDataSource(BaseModel):
    """Metadata for one local historical intraday data source."""

    source_id: str = Field(min_length=1)
    provider_name: str = Field(min_length=1)
    provider_type: HistoricalIntradayProviderType
    source_path: str | None = None
    dataset_id: str = Field(min_length=1)
    imported_at: datetime
    row_count: int = Field(ge=0)
    source_timezone: str = Field(min_length=1)
    adjustment_mode: HistoricalIntradayAdjustmentMode
    license_note: str = Field(min_length=1)
    approved_for_research: bool = True
    real_money_status: str = "Not allowed"

    @field_validator("imported_at")
    @classmethod
    def normalize_imported_at(cls, value: datetime) -> datetime:
        """Normalize import timestamps to UTC."""

        return normalize_to_utc(value)

    @model_validator(mode="after")
    def validate_research_only(self) -> Self:
        """Keep data-source metadata research-only."""

        if self.real_money_status != "Not allowed":
            raise ValueError("historical data source real-money status must be Not allowed")
        return self


class HistoricalIntradayInstrument(BaseModel):
    """Instrument metadata for historical intraday bars."""

    symbol: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    instrument_type: IntradayInstrumentType
    point_value: float = Field(gt=0)
    tick_size: float = Field(gt=0)
    tick_value: float = Field(gt=0)
    exchange_or_venue: str | None = None
    timezone: str = Field(min_length=1)
    regular_session_open: str = Field(min_length=1)
    regular_session_close: str = Field(min_length=1)
    plain_english_description: str = Field(min_length=1)

    @field_validator("symbol")
    @classmethod
    def normalize_instrument_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        return normalize_symbol(value)


class HistoricalIntradayBar(BaseModel):
    """Normalized historical intraday OHLCV bar."""

    symbol: str = Field(min_length=1)
    timestamp_utc: datetime
    raw_timestamp: str = Field(min_length=1)
    source_timezone: str = Field(min_length=1)
    interval: IntradayBarInterval
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)
    session_type: IntradaySessionType
    session_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    adjustment_mode: HistoricalIntradayAdjustmentMode
    ingested_at: datetime

    @field_validator("symbol")
    @classmethod
    def normalize_bar_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        return normalize_symbol(value)

    @field_validator("timestamp_utc", "ingested_at")
    @classmethod
    def normalize_bar_timestamp(cls, value: datetime) -> datetime:
        """Normalize bar timestamps to UTC."""

        return normalize_to_utc(value)

    @field_validator("session_id", "provider", "dataset_id", "source_timezone", "raw_timestamp")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        """Require non-empty text after stripping."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("value must be non-empty")
        return normalized

    @model_validator(mode="after")
    def validate_ohlc_relationships(self) -> Self:
        """Validate OHLC relationships."""

        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be greater than or equal to open, close, and low")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be less than or equal to open, close, and high")
        return self


class HistoricalIntradaySession(BaseModel):
    """Historical intraday session summary."""

    session_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    session_date: date
    bar_count: int = Field(ge=0)
    first_bar_timestamp_utc: datetime | None = None
    last_bar_timestamp_utc: datetime | None = None
    has_premarket: bool = False
    has_regular_first_hour: bool = False
    has_regular_session: bool = False
    has_after_hours: bool = False
    has_overnight: bool = False
    readiness: HistoricalIntradayReadiness
    quality_issue_count: int = Field(ge=0)
    plain_english_summary: str = Field(min_length=1)
    real_money_status: str = "Not allowed"

    @field_validator("symbol")
    @classmethod
    def normalize_session_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        return normalize_symbol(value)

    @field_validator("first_bar_timestamp_utc", "last_bar_timestamp_utc")
    @classmethod
    def normalize_optional_session_timestamp(cls, value: datetime | None) -> datetime | None:
        """Normalize optional session timestamps to UTC."""

        if value is None:
            return None
        return normalize_to_utc(value)

    @model_validator(mode="after")
    def validate_research_only(self) -> Self:
        """Keep session output research-only."""

        if self.real_money_status != "Not allowed":
            raise ValueError("historical session real-money status must be Not allowed")
        return self


class HistoricalIntradayProviderCapabilities(BaseModel):
    """Capabilities reported by a historical intraday provider."""

    provider_name: str = Field(min_length=1)
    provider_type: HistoricalIntradayProviderType
    supports_local_files: bool
    supports_external_calls: bool
    requires_credentials: bool
    supported_intervals: list[IntradayBarInterval] = Field(min_length=1)
    supported_adjustment_modes: list[HistoricalIntradayAdjustmentMode] = Field(min_length=1)
    supports_dynamic_symbols: bool
    plain_english_summary: str = Field(min_length=1)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_research_only(self) -> Self:
        """Keep provider capability output research-only."""

        if self.real_money_status != "Not allowed":
            raise ValueError("provider capability real-money status must be Not allowed")
        return self


class HistoricalIntradayImportResult(BaseModel):
    """Historical intraday import result."""

    source: HistoricalIntradayDataSource
    instruments: list[HistoricalIntradayInstrument] = Field(default_factory=list)
    sessions: list[HistoricalIntradaySession] = Field(default_factory=list)
    bars: list[HistoricalIntradayBar] = Field(default_factory=list)
    bars_loaded: int = Field(ge=0)
    quality_issues: list[HistoricalIntradayQualityIssue] = Field(default_factory=list)
    plain_english_summary: str = Field(min_length=1)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_research_only(self) -> Self:
        """Keep import output research-only."""

        if self.real_money_status != "Not allowed":
            raise ValueError("historical import real-money status must be Not allowed")
        if self.bars_loaded != len(self.bars):
            raise ValueError("bars_loaded must match bars length")
        return self


def normalize_to_utc(value: datetime) -> datetime:
    """Normalize a datetime to timezone-aware UTC."""

    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(UTC)
