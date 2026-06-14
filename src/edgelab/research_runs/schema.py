"""Schemas for saved local research runs."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from edgelab.intraday.pattern_results_schema import OVERCONFIDENT_RESEARCH_PHRASES
from edgelab.intraday.schema import normalize_symbol, reject_action_instructions

SAVED_RESEARCH_RUN_SCHEMA_VERSION = "phase_7x_2f_v1"
SAVED_RESEARCH_RUN_CODE_VERSION = "phase_7x_2f"


class ResearchRunType(StrEnum):
    """Supported saved local research-run families."""

    FIRSTRATE_MANY_MORNING_REPLAY = "firstrate_many_morning_replay"


class ResearchRunStatus(StrEnum):
    """Explicit status for a saved research run."""

    COMPLETED = "completed"
    FAILED = "failed"


class ResearchRunFreshnessStatus(StrEnum):
    """Whether a saved result still matches the local source file and code schema."""

    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"
    NOT_FOUND = "not_found"


class ResearchRunQualityIssue(BaseModel):
    """Saved warning about a local research run."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: str = "warning"
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_safe_issue(self) -> Self:
        """Keep warning text conservative."""

        _validate_safe_text(
            self.message,
            context="research run quality issue",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class ResearchRunCreateRequest(BaseModel):
    """Request to run and save one local analysis."""

    run_type: ResearchRunType = ResearchRunType.FIRSTRATE_MANY_MORNING_REPLAY
    symbol: str = Field(min_length=1)
    start_date: date | None = None
    end_date: date | None = None
    hold_minutes: int = Field(default=5, gt=0)
    slippage_ticks: int = Field(default=1, ge=0)
    commission_per_contract: float = Field(default=0, ge=0)

    @field_validator("symbol")
    @classmethod
    def normalize_request_symbol(cls, value: str) -> str:
        """Normalize symbols for matching."""

        return normalize_symbol(value)

    @model_validator(mode="after")
    def validate_date_order(self) -> Self:
        """Validate optional date ranges."""

        if self.start_date is not None and self.end_date is not None:
            if self.start_date > self.end_date:
                raise ValueError("start_date must be on or before end_date")
        return self


class SavedResearchRun(BaseModel):
    """Compact saved result from one local research run."""

    run_id: str = Field(min_length=1)
    run_type: ResearchRunType
    symbol: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    source_file_path: str = Field(min_length=1)
    source_file_size: int = Field(ge=0)
    source_file_modified_time: int = Field(ge=0)
    source_data_fingerprint: str = Field(min_length=1)
    start_date: date | None = None
    end_date: date | None = None
    hold_minutes: int = Field(gt=0)
    slippage_ticks: int = Field(ge=0)
    commission_per_contract: float = Field(ge=0)
    run_status: ResearchRunStatus
    started_at: datetime
    completed_at: datetime
    elapsed_ms: int = Field(ge=0)
    summary_result: dict[str, Any] = Field(default_factory=dict)
    first_hour_completeness_summary: dict[str, Any] = Field(default_factory=dict)
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    quality_issues: list[ResearchRunQualityIssue] = Field(default_factory=list)
    plain_english_bottom_line: str = Field(min_length=1)
    what_edgelab_tested: str = Field(min_length=1)
    what_edgelab_found: str = Field(min_length=1)
    is_this_enough_to_trust: str = Field(min_length=1)
    what_to_test_next: str = Field(min_length=1)
    schema_version: str = SAVED_RESEARCH_RUN_SCHEMA_VERSION
    code_version: str = SAVED_RESEARCH_RUN_CODE_VERSION
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @field_validator("symbol")
    @classmethod
    def normalize_saved_symbol(cls, value: str) -> str:
        """Normalize saved symbols."""

        return normalize_symbol(value)

    @field_validator("started_at", "completed_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        """Store timestamps in UTC."""

        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_saved_run(self) -> Self:
        """Keep saved user-facing output conservative."""

        _validate_safe_text(
            " ".join(
                [
                    self.plain_english_bottom_line,
                    self.what_edgelab_tested,
                    self.what_edgelab_found,
                    self.is_this_enough_to_trust,
                    self.what_to_test_next,
                    *[issue.message for issue in self.quality_issues],
                ]
            ),
            context="saved research run text",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class ResearchRunSummary(BaseModel):
    """Small list item for saved research runs."""

    run_id: str
    run_type: ResearchRunType
    symbol: str
    completed_at: datetime
    plain_english_bottom_line: str
    run_status: ResearchRunStatus
    real_money_status: str = "Not allowed"


class ResearchRunFreshness(BaseModel):
    """Freshness result for a saved research run."""

    status: ResearchRunFreshnessStatus
    message: str
    checked_at: datetime
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_freshness_text(self) -> Self:
        """Keep freshness copy conservative."""

        _validate_safe_text(
            self.message,
            context="research run freshness text",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


def _validate_safe_text(
    text: str,
    *,
    context: str,
    research_only_status: str,
    real_money_status: str,
) -> None:
    if research_only_status != "Research only":
        raise ValueError(f"{context} must remain research-only")
    if real_money_status != "Not allowed":
        raise ValueError(f"{context} real-money status must be Not allowed")
    reject_action_instructions(text, context)
    lowered = text.lower()
    if any(
        re.search(rf"\b{re.escape(phrase)}\b", lowered) for phrase in OVERCONFIDENT_RESEARCH_PHRASES
    ):
        raise ValueError(f"{context} must not contain overconfident research language")
