"""Schemas for local comparative intraday pattern studies."""

from __future__ import annotations

import re
from datetime import date
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from edgelab.intraday.pattern_results_schema import OVERCONFIDENT_RESEARCH_PHRASES
from edgelab.intraday.schema import (
    IntradaySetupType,
    normalize_symbol,
    reject_action_instructions,
)
from edgelab.research_runs.schema import ResearchRunFreshnessStatus

COMPARATIVE_STUDY_SCHEMA_VERSION = "phase_7x_2g_v1"
COMPARATIVE_STUDY_CODE_VERSION = "phase_7x_2g"


class ComparativeStudyClassification(StrEnum):
    """Conservative labels for a symbol-to-symbol research comparison."""

    SIMILAR_BEHAVIOR = "similar_behavior"
    SYMBOL_DIFFERENCE_NEEDS_REVIEW = "symbol_difference_needs_review"
    SPY_MORE_INTERESTING = "spy_more_interesting"
    QQQ_MORE_INTERESTING = "qqq_more_interesting"
    TOO_NOISY_TO_COMPARE = "too_noisy_to_compare"
    NOT_ENOUGH_EVIDENCE = "not_enough_evidence"
    BLOCKED_BY_DATA_QUALITY = "blocked_by_data_quality"


class ComparativeStudyQualityIssue(BaseModel):
    """Conservative warning for a comparative study."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: str = "warning"
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_safe_issue(self) -> Self:
        """Keep warning text conservative."""

        _validate_safe_output(
            text=self.message,
            context="comparative study quality issue",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class ComparativeStudyRequest(BaseModel):
    """Request for a local SPY/QQQ comparative study."""

    symbols: tuple[str, str] = ("SPY", "QQQ")
    setup_family: IntradaySetupType = IntradaySetupType.OPENING_RANGE_FAILURE
    start_date: date | None = None
    end_date: date | None = None
    hold_minutes: int = Field(default=5, gt=0)
    slippage_ticks: int = Field(default=1, ge=0)
    commission_per_contract: float = Field(default=0, ge=0)
    minimum_useful_sessions: int = Field(default=30, gt=0)
    minimum_setup_examples: int = Field(default=10, gt=0)
    minimum_worth_more_testing_examples: int = Field(default=20, gt=0)

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, value: tuple[str, str]) -> tuple[str, str]:
        """Normalize and require exactly two distinct symbols."""

        normalized = tuple(normalize_symbol(symbol) for symbol in value)
        if len(normalized) != 2 or normalized[0] == normalized[1]:
            raise ValueError("comparative study requires two different symbols")
        return normalized

    @model_validator(mode="after")
    def validate_request(self) -> Self:
        """Validate supported setup and date range."""

        if self.setup_family != IntradaySetupType.OPENING_RANGE_FAILURE:
            raise ValueError("Phase 7X-2G only supports Opening Range Failure")
        if self.start_date is not None and self.end_date is not None:
            if self.start_date > self.end_date:
                raise ValueError("start_date must be on or before end_date")
        return self


class SymbolComparisonSummary(BaseModel):
    """Plain summary for one symbol in a comparative study."""

    symbol: str = Field(min_length=1)
    saved_run_id: str | None = None
    saved_run_freshness: ResearchRunFreshnessStatus
    saved_run_message: str = Field(min_length=1)
    comparison_available: bool
    sessions_tested: int = Field(ge=0)
    usable_sessions: int = Field(ge=0)
    possible_setup_count: int = Field(ge=0)
    sit_out_count: int = Field(ge=0)
    completed_pretend_result_count: int = Field(ge=0)
    helpful_afterward_count: int = Field(ge=0)
    wrong_way_afterward_count: int = Field(ge=0)
    flat_afterward_count: int = Field(ge=0)
    incomplete_pretend_result_count: int = Field(ge=0)
    setup_classification: str = Field(min_length=1)
    direction_context_counts: dict[str, int] = Field(default_factory=dict)
    opening_gap_bucket_counts: dict[str, int] = Field(default_factory=dict)
    first_hour_range_width_bucket_counts: dict[str, int] = Field(default_factory=dict)
    first_hour_completeness_counts: dict[str, int] = Field(default_factory=dict)
    plain_english_summary: str = Field(min_length=1)
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @field_validator("symbol")
    @classmethod
    def normalize_summary_symbol(cls, value: str) -> str:
        """Normalize symbol names."""

        return normalize_symbol(value)

    @model_validator(mode="after")
    def validate_safe_summary(self) -> Self:
        """Keep symbol comparison text conservative."""

        _validate_safe_output(
            text=" ".join([self.saved_run_message, self.plain_english_summary]),
            context="symbol comparison summary",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class SetupFamilyComparison(BaseModel):
    """Comparison for one setup family across symbols."""

    setup_family: IntradaySetupType
    classification: ComparativeStudyClassification
    symbol_summaries: list[SymbolComparisonSummary]
    bottom_line: str = Field(min_length=1)
    what_edgelab_compared: str = Field(min_length=1)
    what_looked_different: str = Field(min_length=1)
    why_that_might_matter: str = Field(min_length=1)
    why_this_might_be_misleading: str = Field(min_length=1)
    what_edgelab_should_test_next: str = Field(min_length=1)
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_safe_comparison(self) -> Self:
        """Keep comparison text conservative."""

        _validate_safe_output(
            text=" ".join(
                [
                    self.bottom_line,
                    self.what_edgelab_compared,
                    self.what_looked_different,
                    self.why_that_might_matter,
                    self.why_this_might_be_misleading,
                    self.what_edgelab_should_test_next,
                ]
            ),
            context="setup family comparison",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class ComparativeStudyResult(BaseModel):
    """Research-only local comparative study result."""

    study_id: str = Field(min_length=1)
    request: ComparativeStudyRequest
    comparison_available: bool
    classification: ComparativeStudyClassification
    setup_family_comparison: SetupFamilyComparison
    quality_issues: list[ComparativeStudyQualityIssue] = Field(default_factory=list)
    cache_metadata: dict[str, Any] = Field(default_factory=dict)
    bottom_line: str = Field(min_length=1)
    what_edgelab_compared: str = Field(min_length=1)
    what_looked_different: str = Field(min_length=1)
    why_that_might_matter: str = Field(min_length=1)
    why_this_might_be_misleading: str = Field(min_length=1)
    what_edgelab_should_test_next: str = Field(min_length=1)
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = COMPARATIVE_STUDY_SCHEMA_VERSION
    code_version: str = COMPARATIVE_STUDY_CODE_VERSION
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_safe_result(self) -> Self:
        """Keep comparative study output conservative."""

        _validate_safe_output(
            text=" ".join(
                [
                    self.bottom_line,
                    self.what_edgelab_compared,
                    self.what_looked_different,
                    self.why_that_might_matter,
                    self.why_this_might_be_misleading,
                    self.what_edgelab_should_test_next,
                    *[issue.message for issue in self.quality_issues],
                ]
            ),
            context="comparative study result",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


def _validate_safe_output(
    *,
    text: str,
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
