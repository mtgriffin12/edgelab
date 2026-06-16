"""Schemas for local intraday strategy discovery sprints."""

from __future__ import annotations

import re
from datetime import date
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from edgelab.intraday.pattern_results_schema import OVERCONFIDENT_RESEARCH_PHRASES
from edgelab.intraday.schema import normalize_symbol, reject_action_instructions

DISCOVERY_SPRINT_SCHEMA_VERSION = "phase_7x_2k_v1"
DISCOVERY_SPRINT_CODE_VERSION = "phase_7x_2k"

DISCOVERY_SPRINT_FORBIDDEN_PHRASES = [
    *OVERCONFIDENT_RESEARCH_PHRASES,
    "validated edge",
    "signal readiness",
    "paper-mode readiness",
    "real-money readiness",
    "live signal",
    "paper mode",
    "ready to trade",
    "should work",
    "will work",
    "recommend",
    "recommendation",
    "buy",
    "sell",
    "short",
    "tune after seeing results",
    "change thresholds after seeing results",
]


class DiscoverySprintClassification(StrEnum):
    """Plain result labels for strategy discovery."""

    NO_CLEAR_PATTERN = "no_clear_pattern"
    NOT_ENOUGH_EXAMPLES = "not_enough_examples"
    DATA_PROBLEM = "data_problem"
    LOOKED_BETTER_AT_FIRST = "looked_better_at_first"
    HELD_UP_ON_LATER_CHECK = "held_up_on_later_check"
    DID_NOT_HOLD_UP_LATER = "did_not_hold_up_later"
    WORTH_MORE_TESTING = "worth_more_testing"
    REJECT_FOR_NOW = "reject_for_now"


class SupportedRuleFamily(StrEnum):
    """Deterministic rule families EdgeLab can test locally."""

    FAILED_EARLY_MOVE = "failed_early_move"
    GAP_FADE = "gap_fade"
    GAP_CONTINUATION = "gap_continuation"
    FIRST_15_MINUTE_BREAKOUT = "first_15_minute_breakout"
    FIRST_30_MINUTE_BREAKOUT = "first_30_minute_breakout"
    OPENING_RANGE_RECLAIM = "opening_range_reclaim"
    STRONG_OPEN_WEAK_FOLLOW_THROUGH = "strong_open_weak_follow_through"
    SPY_QQQ_DIVERGENCE = "spy_qqq_divergence"


class StrategyIdeaDefinition(BaseModel):
    """One fixed local strategy idea definition."""

    strategy_id: SupportedRuleFamily
    url_slug: str = Field(min_length=1)
    name: str = Field(min_length=1)
    plain_english_summary: str = Field(min_length=1)
    plain_english_rule: str = Field(min_length=1)
    what_is_tested: str = Field(min_length=1)
    example_definition: str = Field(min_length=1)
    useful_result_definition: str = Field(min_length=1)
    failed_or_unclear_definition: str = Field(min_length=1)
    current_result_interpretation_template: str = Field(min_length=1)
    required_data: str = Field(min_length=1)
    useful_first_result: str = Field(min_length=1)
    unclear_or_failed_result: str = Field(min_length=1)
    result_classification_rules: dict[str, str] = Field(default_factory=dict)
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_strategy_text(self) -> Self:
        """Keep strategy definitions safe and research-only."""

        _validate_safe_output(
            " ".join(
                [
                    self.name,
                    self.plain_english_summary,
                    self.plain_english_rule,
                    self.what_is_tested,
                    self.example_definition,
                    self.useful_result_definition,
                    self.failed_or_unclear_definition,
                    self.current_result_interpretation_template,
                    self.required_data,
                    self.useful_first_result,
                    self.unclear_or_failed_result,
                    *self.result_classification_rules.values(),
                ]
            ),
            context="strategy idea definition",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class AIProposedIntradayIdea(BaseModel):
    """Safe future-facing structure for AI-proposed hypotheses."""

    proposed_id: str = Field(min_length=1)
    proposed_name: str = Field(min_length=1)
    plain_english_hypothesis: str = Field(min_length=1)
    supported_rule_family: SupportedRuleFamily
    instruments_to_test: tuple[str, ...] = Field(min_length=1)
    required_data: str = Field(min_length=1)
    fixed_rule_definition: str = Field(min_length=1)
    allowed_parameters: tuple[str, ...] = Field(default_factory=tuple)
    disallowed_parameters: tuple[str, ...] = Field(default_factory=tuple)
    expected_failure_modes: tuple[str, ...] = Field(min_length=1)
    reason_to_test: str = Field(min_length=1)
    safety_notes: str = Field(min_length=1)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @field_validator("instruments_to_test")
    @classmethod
    def normalize_symbols(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Normalize proposed symbols."""

        return tuple(normalize_symbol(symbol) for symbol in value)

    @model_validator(mode="after")
    def validate_ai_idea(self) -> Self:
        """Reject unsafe or non-deterministic AI idea specs."""

        text = " ".join(
            [
                self.proposed_name,
                self.plain_english_hypothesis,
                self.required_data,
                self.fixed_rule_definition,
                *self.allowed_parameters,
                *self.disallowed_parameters,
                *self.expected_failure_modes,
                self.reason_to_test,
                self.safety_notes,
            ]
        )
        _validate_safe_output(
            text,
            context="AI-proposed idea spec",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        lowered = text.lower()
        if "after seeing results" in lowered:
            raise ValueError("AI-proposed idea spec must not tune thresholds after results")
        if "visually inspect" in lowered or "chart" in lowered:
            raise ValueError("AI-proposed idea spec must be testable with local bars")
        return self


class DiscoverySprintRequest(BaseModel):
    """Request for a local deterministic discovery sprint."""

    symbols: tuple[str, ...] | None = None
    start_date: date | None = None
    end_date: date | None = None
    later_check_start_date: date = date(2023, 1, 1)
    hold_minutes: int = Field(default=5, gt=0)
    slippage_ticks: int = Field(default=1, ge=0)
    commission_per_contract: float = Field(default=0, ge=0)
    minimum_useful_sessions: int = Field(default=30, gt=0)
    minimum_examples: int = Field(default=10, gt=0)
    minimum_worth_more_testing_examples: int = Field(default=20, gt=0)

    @field_validator("symbols")
    @classmethod
    def normalize_optional_symbols(cls, value: tuple[str, ...] | None) -> tuple[str, ...] | None:
        """Normalize requested symbols."""

        if value is None:
            return None
        normalized = tuple(dict.fromkeys(normalize_symbol(symbol) for symbol in value))
        if not normalized:
            raise ValueError("symbols cannot be empty")
        return normalized

    @model_validator(mode="after")
    def validate_date_order(self) -> Self:
        """Validate optional date range."""

        if self.start_date is not None and self.end_date is not None:
            if self.start_date > self.end_date:
                raise ValueError("start_date must be on or before end_date")
        return self


class InstrumentDiscoveryResult(BaseModel):
    """One strategy result for one local instrument."""

    symbol: str = Field(min_length=1)
    sessions_tested: int = Field(ge=0)
    usable_sessions: int = Field(ge=0)
    examples_found: int = Field(ge=0)
    completed_examples: int = Field(ge=0)
    moved_as_expected_count: int = Field(ge=0)
    moved_against_test_count: int = Field(ge=0)
    did_not_move_enough_count: int = Field(ge=0)
    first_slice_examples: int = Field(ge=0)
    later_slice_examples: int = Field(ge=0)
    first_slice_result: str = Field(min_length=1)
    later_slice_result: str = Field(min_length=1)
    classification: DiscoverySprintClassification
    classification_label: str = Field(min_length=1)
    plain_english_summary: str = Field(min_length=1)
    data_warnings: list[str] = Field(default_factory=list)
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @field_validator("symbol")
    @classmethod
    def normalize_result_symbol(cls, value: str) -> str:
        """Normalize result symbols."""

        return normalize_symbol(value)

    @model_validator(mode="after")
    def validate_result_text(self) -> Self:
        """Keep instrument result output safe."""

        _validate_safe_output(
            " ".join(
                [
                    self.first_slice_result,
                    self.later_slice_result,
                    self.classification_label,
                    self.plain_english_summary,
                    *self.data_warnings,
                ]
            ),
            context="instrument discovery result",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class StrategyDiscoveryResult(BaseModel):
    """One strategy idea result in the discovery sprint."""

    strategy_id: SupportedRuleFamily
    url_slug: str = Field(min_length=1)
    strategy_name: str = Field(min_length=1)
    plain_english_summary: str = Field(min_length=1)
    what_is_tested: str = Field(min_length=1)
    example_definition: str = Field(min_length=1)
    useful_result_definition: str = Field(min_length=1)
    failed_or_unclear_definition: str = Field(min_length=1)
    current_result_interpretation: str = Field(min_length=1)
    securities_tested: str = Field(min_length=1)
    tests_run: str = Field(min_length=1)
    best_current_pattern_candidate: str = Field(min_length=1)
    current_conclusion: str = Field(min_length=1)
    status: str = Field(min_length=1)
    next_research_action: str = Field(min_length=1)
    classification: DiscoverySprintClassification
    evidence_score: int = Field(ge=0, le=100)
    instrument_results: list[InstrumentDiscoveryResult]
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_strategy_result_text(self) -> Self:
        """Keep strategy result output safe."""

        _validate_safe_output(
            " ".join(
                [
                    self.strategy_name,
                    self.plain_english_summary,
                    self.what_is_tested,
                    self.example_definition,
                    self.useful_result_definition,
                    self.failed_or_unclear_definition,
                    self.current_result_interpretation,
                    self.securities_tested,
                    self.tests_run,
                    self.best_current_pattern_candidate,
                    self.current_conclusion,
                    self.status,
                    self.next_research_action,
                ]
            ),
            context="strategy discovery result",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class DiscoverySprintResult(BaseModel):
    """Research-only multi-instrument discovery sprint result."""

    sprint_id: str = Field(min_length=1)
    symbols_tested: list[str]
    strategy_ideas_tested: list[str]
    strategy_count: int = Field(ge=0)
    date_range: str = Field(min_length=1)
    later_check_range: str = Field(min_length=1)
    bottom_line: str = Field(min_length=1)
    best_candidate_if_any: str = Field(min_length=1)
    current_conclusion: str = Field(min_length=1)
    what_edgelab_tested: str = Field(min_length=1)
    what_edgelab_found: str = Field(min_length=1)
    what_deserves_more_testing: str = Field(min_length=1)
    what_did_not_advance: str = Field(min_length=1)
    next_research_action: str = Field(min_length=1)
    strategy_results: list[StrategyDiscoveryResult]
    ranked_shortlist: list[StrategyDiscoveryResult]
    ai_idea_intake_summary: str = Field(min_length=1)
    cache_metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = DISCOVERY_SPRINT_SCHEMA_VERSION
    code_version: str = DISCOVERY_SPRINT_CODE_VERSION
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_sprint_result_text(self) -> Self:
        """Keep sprint result output safe."""

        _validate_safe_output(
            " ".join(
                [
                    self.bottom_line,
                    self.best_candidate_if_any,
                    self.current_conclusion,
                    self.what_edgelab_tested,
                    self.what_edgelab_found,
                    self.what_deserves_more_testing,
                    self.what_did_not_advance,
                    self.next_research_action,
                    self.ai_idea_intake_summary,
                ]
            ),
            context="discovery sprint result",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


def classification_label(classification: DiscoverySprintClassification) -> str:
    """Return plain user-facing classification copy."""

    return {
        DiscoverySprintClassification.NO_CLEAR_PATTERN: "Mixed results / no clear answer",
        DiscoverySprintClassification.NOT_ENOUGH_EXAMPLES: "Needs more examples",
        DiscoverySprintClassification.DATA_PROBLEM: "Local data problem blocked the test",
        DiscoverySprintClassification.LOOKED_BETTER_AT_FIRST: (
            "One version looked better at first"
        ),
        DiscoverySprintClassification.HELD_UP_ON_LATER_CHECK: ("Still looked worth testing later"),
        DiscoverySprintClassification.DID_NOT_HOLD_UP_LATER: ("Did not clearly hold up later"),
        DiscoverySprintClassification.WORTH_MORE_TESTING: "Worth testing on more history",
        DiscoverySprintClassification.REJECT_FOR_NOW: "Reject for now",
    }[classification]


def _validate_safe_output(
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
        re.search(rf"\b{re.escape(phrase)}\b", lowered)
        for phrase in DISCOVERY_SPRINT_FORBIDDEN_PHRASES
    ):
        raise ValueError(f"{context} must not contain unsafe research language")
