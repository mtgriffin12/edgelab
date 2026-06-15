"""Schemas for controlled intraday variant studies."""

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

VARIANT_STUDY_SCHEMA_VERSION = "phase_7x_2h_v1"
VARIANT_STUDY_CODE_VERSION = "phase_7x_2h"


class VariantStudyClassification(StrEnum):
    """Conservative labels for controlled variant studies."""

    NOT_ENOUGH_EXAMPLES = "not_enough_examples"
    BLOCKED_BY_DATA_QUALITY = "blocked_by_data_quality"
    TOO_NOISY = "too_noisy"
    WEAKER_THAN_BASELINE = "weaker_than_baseline"
    SIMILAR_TO_BASELINE = "similar_to_baseline"
    INTERESTING_BUT_UNPROVEN = "interesting_but_unproven"
    WORTH_MORE_TESTING = "worth_more_testing"


class VariantDefinition(BaseModel):
    """One pre-declared controlled variant definition."""

    variant_id: str = Field(min_length=1)
    plain_english_label: str = Field(min_length=1)
    rule_definition: str = Field(min_length=1)
    why_it_might_matter: str = Field(min_length=1)
    baseline_compared_against: str = "broad_baseline"
    what_would_disprove_it: str = Field(min_length=1)
    is_active_variant: bool = True
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_definition_text(self) -> Self:
        """Keep variant definitions safe and research-only."""

        _validate_safe_output(
            text=" ".join(
                [
                    self.plain_english_label,
                    self.rule_definition,
                    self.why_it_might_matter,
                    self.what_would_disprove_it,
                ]
            ),
            context="variant definition",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class VariantStudyRequest(BaseModel):
    """Request for one local controlled variant study."""

    symbol: str = "SPY"
    paired_symbol: str = "QQQ"
    setup_family: IntradaySetupType = IntradaySetupType.OPENING_RANGE_FAILURE
    start_date: date | None = None
    end_date: date | None = None
    hold_minutes: int = Field(default=5, gt=0)
    slippage_ticks: int = Field(default=1, ge=0)
    commission_per_contract: float = Field(default=0, ge=0)
    minimum_useful_sessions: int = Field(default=30, gt=0)
    minimum_completed_examples: int = Field(default=10, gt=0)
    minimum_worth_more_testing_examples: int = Field(default=20, gt=0)
    fast_failure_minutes: int = Field(default=15, gt=0)
    minimum_clarity_improvement_points: float = Field(default=10, ge=0)

    @field_validator("symbol", "paired_symbol")
    @classmethod
    def normalize_symbols(cls, value: str) -> str:
        """Normalize study symbols."""

        return normalize_symbol(value)

    @model_validator(mode="after")
    def validate_request(self) -> Self:
        """Validate supported first study and date range."""

        if self.setup_family != IntradaySetupType.OPENING_RANGE_FAILURE:
            raise ValueError("Phase 7X-2H only supports Early Move Failed")
        if self.symbol == self.paired_symbol:
            raise ValueError("paired_symbol must differ from symbol")
        if self.start_date is not None and self.end_date is not None:
            if self.start_date > self.end_date:
                raise ValueError("start_date must be on or before end_date")
        return self


class VariantBaselineComparison(BaseModel):
    """How one controlled variant compares with the broad baseline."""

    baseline_variant_id: str = "broad_baseline"
    variant_favorable_share: float | None = None
    baseline_favorable_share: float | None = None
    clarity_delta_points: float | None = None
    plain_english_summary: str = Field(min_length=1)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_comparison_text(self) -> Self:
        """Keep comparison text conservative."""

        _validate_safe_output(
            text=self.plain_english_summary,
            context="variant baseline comparison",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class VariantResultSummary(BaseModel):
    """Plain summary for one controlled variant."""

    variant_id: str = Field(min_length=1)
    plain_english_label: str = Field(min_length=1)
    rule_definition: str = Field(min_length=1)
    why_it_might_matter: str = Field(min_length=1)
    baseline_compared_against: str = "broad_baseline"
    examples_found: int = Field(ge=0)
    examples_completed: int = Field(ge=0)
    moved_as_expected_count: int = Field(ge=0)
    moved_against_test_count: int = Field(ge=0)
    did_not_move_enough_count: int = Field(ge=0)
    average_pretend_result: float | None = None
    worst_pretend_result: float | None = None
    best_pretend_result: float | None = None
    cost_changed_result_count: int = Field(ge=0)
    conservative_classification: VariantStudyClassification
    what_would_disprove_it: str = Field(min_length=1)
    baseline_comparison: VariantBaselineComparison
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_summary_text(self) -> Self:
        """Keep variant output conservative."""

        _validate_safe_output(
            text=" ".join(
                [
                    self.plain_english_label,
                    self.rule_definition,
                    self.why_it_might_matter,
                    self.what_would_disprove_it,
                    self.baseline_comparison.plain_english_summary,
                ]
            ),
            context="variant result summary",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class VariantStudyQualityIssue(BaseModel):
    """Conservative warning for a controlled variant study."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: str = "warning"
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_issue_text(self) -> Self:
        """Keep quality issue text conservative."""

        _validate_safe_output(
            text=self.message,
            context="variant study quality issue",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class VariantStudyResult(BaseModel):
    """Research-only local controlled variant study result."""

    study_id: str = Field(min_length=1)
    request: VariantStudyRequest
    study_available: bool
    classification: VariantStudyClassification
    bottom_line: str = Field(min_length=1)
    what_edgelab_tested: str = Field(min_length=1)
    what_looked_different: str = Field(min_length=1)
    which_version_deserves_more_testing: str = Field(min_length=1)
    why_this_might_be_misleading: str = Field(min_length=1)
    what_edgelab_should_test_next: str = Field(min_length=1)
    baseline_comparison: VariantBaselineComparison
    variant_summaries: list[VariantResultSummary]
    quality_issues: list[VariantStudyQualityIssue] = Field(default_factory=list)
    cache_metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = VARIANT_STUDY_SCHEMA_VERSION
    code_version: str = VARIANT_STUDY_CODE_VERSION
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_result_text(self) -> Self:
        """Keep study output conservative and research-only."""

        _validate_safe_output(
            text=" ".join(
                [
                    self.bottom_line,
                    self.what_edgelab_tested,
                    self.what_looked_different,
                    self.which_version_deserves_more_testing,
                    self.why_this_might_be_misleading,
                    self.what_edgelab_should_test_next,
                    *[issue.message for issue in self.quality_issues],
                ]
            ),
            context="variant study result",
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
    if "paper-mode readiness" in lowered or "signal readiness" in lowered:
        raise ValueError(f"{context} must not imply readiness")


def saved_run_state_payload(
    *,
    run_id: str | None,
    freshness: ResearchRunFreshnessStatus,
    message: str,
) -> dict[str, object]:
    """Return a compact saved-run state for evidence details."""

    return {"run_id": run_id, "freshness": freshness.value, "message": message}
