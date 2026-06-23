"""Schemas for the SPY/CSGP morning divergence data audit."""

from __future__ import annotations

from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from edgelab.intraday.schema import normalize_symbol


class SpyCsgpFileAudit(BaseModel):
    """One local FirstRate file observed by the SPY/CSGP audit."""

    symbol: str = Field(min_length=1)
    file_path: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    row_count: int = Field(ge=0)
    first_timestamp_utc: datetime | None = None
    last_timestamp_utc: datetime | None = None
    start_date: date | None = None
    end_date: date | None = None
    calendar_days_covered: int | None = Field(default=None, ge=0)
    apparent_trading_sessions: int = Field(ge=0)
    usable_first_hour_sessions: int = Field(ge=0)
    first_hour_data_appears_usable: bool
    readiness_counts: dict[str, int] = Field(default_factory=dict)
    quality_issue_count: int = Field(ge=0)
    data_quality_warning: str = Field(min_length=1)
    timezone_assumption: str = "America/New_York source timestamps normalized to UTC"
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @field_validator("symbol")
    @classmethod
    def normalize_file_symbol(cls, value: str) -> str:
        """Normalize symbols."""

        return normalize_symbol(value)

    @model_validator(mode="after")
    def validate_research_only(self) -> Self:
        """Keep file audit output inside the research-only boundary."""

        if self.research_only_status != "Research only":
            raise ValueError("file audit must remain research-only")
        if self.real_money_status != "Not allowed":
            raise ValueError("file audit real-money status must be Not allowed")
        return self


class DataImportFileSpec(BaseModel):
    """Required local CSV file shape for the future SPY/CSGP study."""

    symbol: str = Field(min_length=1)
    recommended_path: str = Field(min_length=1)
    accepted_existing_pattern: str = Field(min_length=1)
    required_columns: list[str] = Field(min_length=1)
    acceptable_alternative_columns: list[str] = Field(default_factory=list)
    plain_english_summary: str = Field(min_length=1)

    @field_validator("symbol")
    @classmethod
    def normalize_spec_symbol(cls, value: str) -> str:
        """Normalize symbols."""

        return normalize_symbol(value)


class MorningDivergenceWindow(BaseModel):
    """One candidate time window for the future SPY/CSGP study."""

    label: str = Field(min_length=1)
    local_time_window: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)


class SpyCsgpDataAudit(BaseModel):
    """Read-only data audit and first test plan for SPY/CSGP morning divergence."""

    audit_id: str = Field(min_length=1)
    as_of: date
    data_dir: str = Field(min_length=1)
    available_symbols: list[str] = Field(default_factory=list)
    expected_symbols: list[str] = Field(default_factory=list)
    files: list[SpyCsgpFileAudit] = Field(default_factory=list)
    spy_data_found: bool
    csgp_data_found: bool
    spy_summary: SpyCsgpFileAudit | None = None
    csgp_summary: SpyCsgpFileAudit | None = None
    legacy_spy_summary: SpyCsgpFileAudit | None = None
    recent_spy_summary: SpyCsgpFileAudit | None = None
    recent_csgp_summary: SpyCsgpFileAudit | None = None
    recent_pair_has_enough_overlap: bool = False
    recent_pair_plain_english: str = Field(min_length=1)
    current_spy_data_plain_english: str = Field(min_length=1)
    csgp_data_plain_english: str = Field(min_length=1)
    spy_data_recent_enough_for_last_year_observation: bool
    recommended_data_window: str = Field(min_length=1)
    why_old_and_current_data_should_not_be_mixed: str = Field(min_length=1)
    exact_data_needed: list[str] = Field(min_length=1)
    required_files: list[DataImportFileSpec] = Field(min_length=1)
    target_normalized_columns: list[str] = Field(
        default_factory=lambda: ["timestamp", "open", "high", "low", "close", "volume"]
    )
    morning_windows: list[MorningDivergenceWindow] = Field(min_length=1)
    spy_weakness_thresholds: list[str] = Field(min_length=1)
    csgp_strength_thresholds: list[str] = Field(min_length=1)
    first_study_question: str = Field(min_length=1)
    future_metrics: list[str] = Field(min_length=1)
    next_steps: list[str] = Field(min_length=1)
    provider_supports_external_calls: bool
    provider_requires_credentials: bool
    provider_plain_english_summary: str = Field(min_length=1)
    no_live_data_requested: bool = True
    no_ai_or_model_calls: bool = True
    no_batch_results_saved: bool = True
    local_save_deferred: bool = True
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @field_validator("available_symbols", "expected_symbols")
    @classmethod
    def normalize_symbol_lists(cls, values: list[str]) -> list[str]:
        """Normalize and sort symbols."""

        return sorted({normalize_symbol(value) for value in values})

    @model_validator(mode="after")
    def validate_research_only(self) -> Self:
        """Keep the audit read-only and non-actionable."""

        if self.provider_supports_external_calls:
            raise ValueError("SPY/CSGP audit must not use external calls")
        if self.provider_requires_credentials:
            raise ValueError("SPY/CSGP audit must not require credentials")
        if self.research_only_status != "Research only":
            raise ValueError("SPY/CSGP audit must remain research-only")
        if self.real_money_status != "Not allowed":
            raise ValueError("SPY/CSGP audit real-money status must be Not allowed")
        return self
