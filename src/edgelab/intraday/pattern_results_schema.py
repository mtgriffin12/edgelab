"""Schemas for multi-session historical replay pattern summaries."""

from __future__ import annotations

import re
from datetime import date
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from edgelab.intraday.historical_schema import HistoricalIntradayReadiness
from edgelab.intraday.replay_schema import HistoricalReplayStatus
from edgelab.intraday.schema import (
    IntradaySetupDirection,
    IntradaySetupType,
    normalize_symbol,
    reject_action_instructions,
)

OVERCONFIDENT_RESEARCH_PHRASES = [
    "profitable",
    "proven",
    "reliable",
    "timely",
    "ready for real money",
    "real-money ready",
]


class PatternResultClassification(StrEnum):
    """Conservative labels for multi-session replay summaries."""

    NOT_ENOUGH_EXAMPLES = "not_enough_examples"
    BLOCKED_BY_DATA_QUALITY = "blocked_by_data_quality"
    WEAK_OR_INCONSISTENT = "weak_or_inconsistent"
    INTERESTING_BUT_UNPROVEN = "interesting_but_unproven"
    WORTH_MORE_TESTING = "worth_more_testing"
    SIT_OUT_RULES_NEED_REVIEW = "sit_out_rules_need_review"


class NoTradeUsefulnessLabel(StrEnum):
    """Plain labels for sit-out rule review."""

    NEEDS_MORE_EXAMPLES = "needs_more_examples"
    USEFUL = "useful"
    HARMFUL = "harmful"
    INCONCLUSIVE = "inconclusive"


class ReplayResultBucket(StrEnum):
    """Simplified after-the-fact result bucket."""

    FAVORABLE = "favorable"
    FAILED = "failed"
    FLAT = "flat"
    NOT_COMPLETED = "not_completed"
    SAT_OUT = "sat_out"
    SKIPPED_DUE_TO_DATA = "skipped_due_to_data"


class MultiSessionReplayRequest(BaseModel):
    """Request for replaying many local historical sessions."""

    symbol: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    hold_minutes: int = Field(default=5, gt=0)
    slippage_ticks: int = Field(default=1, ge=0)
    commission_per_contract: float = Field(default=0, ge=0)
    max_one_setup_per_day: bool = True
    minimum_useful_sessions: int = Field(default=30, gt=0)
    minimum_setup_examples: int = Field(default=10, gt=0)
    minimum_worth_more_testing_examples: int = Field(default=20, gt=0)
    include_evidence_details: bool = True

    @field_validator("symbol")
    @classmethod
    def normalize_optional_symbol(cls, value: str | None) -> str | None:
        """Normalize optional symbols."""

        if value is None:
            return None
        return normalize_symbol(value)

    @model_validator(mode="after")
    def validate_date_order(self) -> Self:
        """Validate optional date range."""

        if self.start_date is not None and self.end_date is not None:
            if self.start_date > self.end_date:
                raise ValueError("start_date must be on or before end_date")
        return self


class ReplaySessionOutcome(BaseModel):
    """One normalized outcome from a single-session replay."""

    symbol: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    session_date: date | None = None
    replay_status: HistoricalReplayStatus
    session_readiness: HistoricalIntradayReadiness
    setup_type: IntradaySetupType | None = None
    setup_direction: IntradaySetupDirection | None = None
    setup_found: bool
    sat_out: bool
    data_skipped: bool
    completed_pretend_result: bool
    result_bucket: ReplayResultBucket
    result_label: str | None = None
    pretend_net_result: float | None = None
    pretend_gross_result: float | None = None
    cost_changed_conclusion: bool = False
    no_trade_reasons: list[str] = Field(default_factory=list)
    missed_looking_afterward: bool = False
    opening_gap_bucket: str | None = None
    opening_range_width_bucket: str | None = None
    quality_issue_count: int = Field(ge=0)
    plain_english_summary: str = Field(min_length=1)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @field_validator("symbol")
    @classmethod
    def normalize_outcome_symbol(cls, value: str) -> str:
        """Normalize symbols."""

        return normalize_symbol(value)

    @model_validator(mode="after")
    def validate_research_only(self) -> Self:
        """Keep session outcome output conservative."""

        _validate_safe_output(
            text=" ".join([self.plain_english_summary, *self.no_trade_reasons]),
            context="session outcome text",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class SetupTypeSummary(BaseModel):
    """Aggregated summary for one setup type."""

    setup_type: IntradaySetupType
    examples_found: int = Field(ge=0)
    completed_pretend_results: int = Field(ge=0)
    favorable_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    flat_count: int = Field(ge=0)
    not_completed_count: int = Field(ge=0)
    average_pretend_result: float | None = None
    worst_pretend_result: float | None = None
    best_pretend_result: float | None = None
    cost_changed_conclusion_count: int = Field(ge=0)
    classification: PatternResultClassification
    plain_english_summary: str = Field(min_length=1)
    what_usually_happened: str = Field(min_length=1)
    why_this_might_be_misleading: str = Field(min_length=1)
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_summary_text(self) -> Self:
        """Keep setup summaries conservative."""

        _validate_safe_output(
            text=" ".join(
                [
                    self.plain_english_summary,
                    self.what_usually_happened,
                    self.why_this_might_be_misleading,
                ]
            ),
            context="setup type summary text",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class NoTradeReasonSummary(BaseModel):
    """Aggregated review for one sit-out reason."""

    reason_type: str = Field(min_length=1)
    display_reason: str = Field(min_length=1)
    appeared_count: int = Field(ge=0)
    what_edgelab_avoided: str = Field(min_length=1)
    what_edgelab_might_have_missed: str = Field(min_length=1)
    usefulness_label: NoTradeUsefulnessLabel
    what_needs_more_data: str = Field(min_length=1)
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_summary_text(self) -> Self:
        """Keep sit-out summaries conservative."""

        _validate_safe_output(
            text=" ".join(
                [
                    self.display_reason,
                    self.what_edgelab_avoided,
                    self.what_edgelab_might_have_missed,
                    self.what_needs_more_data,
                ]
            ),
            context="no-trade reason summary text",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class MultiSessionReplaySummary(BaseModel):
    """Research-only summary of many historical intraday replays."""

    summary_id: str = Field(min_length=1)
    symbol: str | None = None
    request: MultiSessionReplayRequest
    sessions_found: int = Field(ge=0)
    sessions_tested: int = Field(ge=0)
    usable_sessions: int = Field(ge=0)
    skipped_due_to_data: int = Field(ge=0)
    setup_count: int = Field(ge=0)
    sit_out_count: int = Field(ge=0)
    completed_pretend_result_count: int = Field(ge=0)
    favorable_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    flat_count: int = Field(ge=0)
    cost_changed_conclusion_count: int = Field(ge=0)
    average_pretend_result: float | None = None
    worst_pretend_result: float | None = None
    best_pretend_result: float | None = None
    classification: PatternResultClassification
    session_outcomes: list[ReplaySessionOutcome] = Field(default_factory=list)
    setup_type_summaries: list[SetupTypeSummary] = Field(default_factory=list)
    no_trade_reason_summaries: list[NoTradeReasonSummary] = Field(default_factory=list)
    quality_issues: list[str] = Field(default_factory=list)
    bottom_line: str = Field(min_length=1)
    what_edgelab_tested: str = Field(min_length=1)
    what_usually_happened: str = Field(min_length=1)
    anything_worth_more_testing: str = Field(min_length=1)
    when_edgelab_sat_out: str = Field(min_length=1)
    whether_sitting_out_helped: str = Field(min_length=1)
    why_this_might_be_misleading: str = Field(min_length=1)
    what_edgelab_should_test_next: str = Field(min_length=1)
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @field_validator("symbol")
    @classmethod
    def normalize_optional_summary_symbol(cls, value: str | None) -> str | None:
        """Normalize optional symbols."""

        if value is None:
            return None
        return normalize_symbol(value)

    @model_validator(mode="after")
    def validate_summary_text(self) -> Self:
        """Keep multi-session summaries conservative."""

        _validate_safe_output(
            text=" ".join(
                [
                    self.bottom_line,
                    self.what_edgelab_tested,
                    self.what_usually_happened,
                    self.anything_worth_more_testing,
                    self.when_edgelab_sat_out,
                    self.whether_sitting_out_helped,
                    self.why_this_might_be_misleading,
                    self.what_edgelab_should_test_next,
                    *self.quality_issues,
                ]
            ),
            context="multi-session summary text",
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
