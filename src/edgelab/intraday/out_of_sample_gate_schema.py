"""Schemas for local out-of-sample research gates."""

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

OUT_OF_SAMPLE_GATE_SCHEMA_VERSION = "phase_7x_2i_v1"
OUT_OF_SAMPLE_GATE_CODE_VERSION = "phase_7x_2i"


class OutOfSampleSplitStrategy(StrEnum):
    """Supported fixed time-based split strategies."""

    CALENDAR_QUARTER_HOLDOUT = "calendar_quarter_holdout"


class OutOfSampleGateConclusion(StrEnum):
    """Conservative plain-English gate outcomes."""

    HELD_UP_IN_FIRST_CHECK = "held_up_in_first_check"
    BECAME_UNCLEAR = "became_unclear"
    NOT_ENOUGH_HOLDOUT_EXAMPLES = "not_enough_holdout_examples"
    WEAKER_ON_HOLDOUT = "weaker_on_holdout"
    BLOCKED_BY_DATA_QUALITY = "blocked_by_data_quality"
    NEEDS_MORE_DATA = "needs_more_data"


class OutOfSampleGatePeriod(BaseModel):
    """One side of a time-based out-of-sample split."""

    label: str = Field(min_length=1)
    start_date: date
    end_date: date
    session_count: int = Field(ge=0)
    plain_english_summary: str = Field(min_length=1)


class OutOfSampleVariantResult(BaseModel):
    """Compact result for one variant in one split period."""

    variant_id: str = Field(min_length=1)
    plain_english_label: str = Field(min_length=1)
    examples_found: int = Field(ge=0)
    examples_completed: int = Field(ge=0)
    moved_as_expected_count: int = Field(ge=0)
    moved_against_test_count: int = Field(ge=0)
    did_not_move_enough_count: int = Field(ge=0)
    average_pretend_result: float | None = None
    cost_changed_result_count: int = Field(ge=0)
    plain_english_result: str = Field(min_length=1)
    evidence_details: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_result_text(self) -> Self:
        """Keep result copy conservative."""

        _validate_safe_output(self.plain_english_result, context="out-of-sample variant result")
        return self


class OutOfSampleVariantComparison(BaseModel):
    """Discovery-vs-holdout comparison for one variant."""

    variant_id: str = Field(min_length=1)
    plain_english_label: str = Field(min_length=1)
    discovery_result: OutOfSampleVariantResult
    holdout_result: OutOfSampleVariantResult
    comparison_result: str = Field(min_length=1)
    gate_conclusion: OutOfSampleGateConclusion
    gate_conclusion_translation: str = Field(min_length=1)
    data_quality_warnings: list[str] = Field(default_factory=list)
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_comparison_text(self) -> Self:
        """Keep comparison copy safe and research-only."""

        _validate_safe_output(
            " ".join(
                [
                    self.comparison_result,
                    self.gate_conclusion_translation,
                    *self.data_quality_warnings,
                ]
            ),
            context="out-of-sample variant comparison",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class OutOfSampleDataQualityWarning(BaseModel):
    """Warning that may block or weaken an out-of-sample check."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: str = "warning"
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_warning_text(self) -> Self:
        """Keep warning text conservative."""

        _validate_safe_output(
            self.message,
            context="out-of-sample warning",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class OutOfSampleGateRequest(BaseModel):
    """Request for a local out-of-sample gate."""

    instrument: str = "SPY"
    paired_instrument: str = "QQQ"
    pattern_family: IntradaySetupType = IntradaySetupType.OPENING_RANGE_FAILURE
    variant_ids: tuple[str, ...] = (
        "broad_baseline",
        "failed_push_from_above",
        "failed_selloff_from_below",
        "fast_failure",
        "slow_failure",
        "spy_qqq_disagreement",
    )
    split_strategy: OutOfSampleSplitStrategy = OutOfSampleSplitStrategy.CALENDAR_QUARTER_HOLDOUT
    holdout_start_date: date = date(2023, 1, 1)
    hold_minutes: int = Field(default=5, gt=0)
    slippage_ticks: int = Field(default=1, ge=0)
    commission_per_contract: float = Field(default=0, ge=0)
    minimum_discovery_examples: int = Field(default=10, gt=0)
    minimum_holdout_examples: int = Field(default=10, gt=0)
    fast_failure_minutes: int = Field(default=15, gt=0)
    meaningful_cost_change_share: float = Field(default=0.20, ge=0, le=1)

    @field_validator("instrument", "paired_instrument")
    @classmethod
    def normalize_instruments(cls, value: str) -> str:
        """Normalize symbols for local file matching."""

        return normalize_symbol(value)

    @model_validator(mode="after")
    def validate_request(self) -> Self:
        """Validate the first supported gate request."""

        if self.pattern_family != IntradaySetupType.OPENING_RANGE_FAILURE:
            raise ValueError("Phase 7X-2I only supports Early Move Failed")
        if self.instrument == self.paired_instrument:
            raise ValueError("paired_instrument must differ from instrument")
        if len(set(self.variant_ids)) != len(self.variant_ids):
            raise ValueError("variant_ids must be unique")
        return self


class OutOfSampleGateResult(BaseModel):
    """Research-only out-of-sample gate result."""

    gate_id: str = Field(min_length=1)
    instrument: str = Field(min_length=1)
    paired_instrument: str = Field(min_length=1)
    pattern_family: str = Field(min_length=1)
    variant_ids: list[str]
    split_strategy: OutOfSampleSplitStrategy
    discovery_period: OutOfSampleGatePeriod | None = None
    holdout_period: OutOfSampleGatePeriod | None = None
    discovery_result: str = Field(min_length=1)
    holdout_result: str = Field(min_length=1)
    comparison_result: str = Field(min_length=1)
    gate_conclusion: OutOfSampleGateConclusion
    gate_conclusion_translation: str = Field(min_length=1)
    bottom_line: str = Field(min_length=1)
    what_edgelab_checked: str = Field(min_length=1)
    what_changed_on_later_data: str = Field(min_length=1)
    what_this_means: str = Field(min_length=1)
    what_edgelab_should_test_next: str = Field(min_length=1)
    why_this_might_be_misleading: str = Field(min_length=1)
    proof_limitations: str = Field(min_length=1)
    variant_comparisons: list[OutOfSampleVariantComparison]
    data_quality_warnings: list[OutOfSampleDataQualityWarning] = Field(default_factory=list)
    cache_metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = OUT_OF_SAMPLE_GATE_SCHEMA_VERSION
    code_version: str = OUT_OF_SAMPLE_GATE_CODE_VERSION
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_gate_text(self) -> Self:
        """Keep gate output conservative and research-only."""

        _validate_safe_output(
            " ".join(
                [
                    self.discovery_result,
                    self.holdout_result,
                    self.comparison_result,
                    self.gate_conclusion_translation,
                    self.bottom_line,
                    self.what_edgelab_checked,
                    self.what_changed_on_later_data,
                    self.what_this_means,
                    self.what_edgelab_should_test_next,
                    self.why_this_might_be_misleading,
                    self.proof_limitations,
                    *[warning.message for warning in self.data_quality_warnings],
                ]
            ),
            context="out-of-sample gate result",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


def conclusion_translation(conclusion: OutOfSampleGateConclusion) -> str:
    """Return beginner-friendly conclusion copy."""

    return {
        OutOfSampleGateConclusion.HELD_UP_IN_FIRST_CHECK: (
            "Still looked interesting in the later period, but still unproven."
        ),
        OutOfSampleGateConclusion.BECAME_UNCLEAR: (
            "The later examples were mixed, so EdgeLab did not get a clear answer."
        ),
        OutOfSampleGateConclusion.NOT_ENOUGH_HOLDOUT_EXAMPLES: (
            "There were too few later examples to judge."
        ),
        OutOfSampleGateConclusion.WEAKER_ON_HOLDOUT: (
            "The later period looked worse than the earlier period."
        ),
        OutOfSampleGateConclusion.BLOCKED_BY_DATA_QUALITY: (
            "A data problem prevents a fair check."
        ),
        OutOfSampleGateConclusion.NEEDS_MORE_DATA: ("EdgeLab needs more history before deciding."),
    }[conclusion]


def _validate_safe_output(
    text: str,
    *,
    context: str,
    research_only_status: str = "Research only",
    real_money_status: str = "Not allowed",
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
    for phrase in [
        "validated edge",
        "signal readiness",
        "paper-mode readiness",
        "real-money readiness",
        "real out-of-sample confirmation",
    ]:
        if phrase in lowered:
            raise ValueError(f"{context} must not imply readiness")
