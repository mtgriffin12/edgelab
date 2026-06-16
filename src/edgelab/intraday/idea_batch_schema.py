"""Schemas for structured local intraday idea batches."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from edgelab.intraday.pattern_results_schema import OVERCONFIDENT_RESEARCH_PHRASES
from edgelab.intraday.schema import normalize_symbol, reject_action_instructions

IDEA_BATCH_SCHEMA_VERSION = "phase_7x_2l_v1"
IDEA_BATCH_CODE_VERSION = "phase_7x_2l"

IDEA_BATCH_FORBIDDEN_PHRASES = [
    *OVERCONFIDENT_RESEARCH_PHRASES,
    "validated edge",
    "signal readiness",
    "paper-mode readiness",
    "paper mode readiness",
    "real-money readiness",
    "live signal",
    "live trading",
    "paper mode",
    "ready to trade",
    "guaranteed",
    "reliable",
    "proven",
    "proof",
    "prove",
    "proves",
    "profit",
    "profitable",
    "recommend",
    "recommendation",
    "buy",
    "sell",
    "short",
    "tune after seeing results",
    "change thresholds after seeing results",
    "adjust after seeing results",
    "already works",
    "will work",
    "should work",
]

IDEA_BATCH_REQUIRED_TOP_LEVEL_FIELDS = [
    "batch_id",
    "batch_name",
    "created_for",
    "ideas",
    "research_only_status",
    "real_money_status",
]

IDEA_BATCH_REQUIRED_IDEA_FIELDS = [
    "idea_id",
    "plain_english_name",
    "hypothesis",
    "supported_rule_family",
    "instruments_to_test",
    "required_data",
    "exact_rule_definition",
    "fixed_parameters",
    "why_test_this",
    "useful_result_definition",
    "failed_or_unclear_result_definition",
    "expected_failure_modes",
    "safety_notes",
]

IDEA_BATCH_FORBIDDEN_LANGUAGE_CATEGORIES = [
    "buy/sell/short instructions",
    "trade recommendations",
    "profit claims",
    "proof claims",
    "guaranteed",
    "reliable",
    "validated edge",
    "live trading language",
    "paper-mode readiness",
    "real-money readiness",
    "threshold tuning after seeing results",
    "language implying the idea already works",
]


class IdeaBatchRuleFamily(StrEnum):
    """Rule families EdgeLab can accept or reject deterministically."""

    FIRST_RANGE_BREAKOUT = "first_range_breakout"
    FIRST_RANGE_FAILURE = "first_range_failure"
    GAP_FADE = "gap_fade"
    GAP_CONTINUATION = "gap_continuation"
    RECLAIM = "reclaim"
    TREND_CONTINUATION = "trend_continuation"
    SYMBOL_DIVERGENCE = "symbol_divergence"
    VOLUME_OR_RANGE_FILTER = "volume_or_range_filter"
    REJECT_UNSUPPORTED = "reject_unsupported"


def idea_batch_minimal_example() -> dict[str, Any]:
    """Return a minimal local idea batch that matches the current schema."""

    return {
        "batch_id": "my_intraday_ideas_001",
        "batch_name": "My Intraday Idea Batch",
        "created_for": "local research",
        "research_only_status": "Research only",
        "real_money_status": "Not allowed",
        "ideas": [
            {
                "idea_id": "gap_down_reclaim_001",
                "plain_english_name": "Gap Down Reclaim",
                "hypothesis": (
                    "When a symbol opens lower and quickly returns inside the early range, "
                    "the recovery can be checked with fixed local rules."
                ),
                "supported_rule_family": "reclaim",
                "instruments_to_test": ["AAPL", "AMZN", "MSFT", "META", "TSLA", "SPY", "QQQ"],
                "required_data": "1-minute bars and the first-hour price range",
                "exact_rule_definition": (
                    "Find mornings where price opens weak, moves below the early range, "
                    "then returns back inside the early range."
                ),
                "fixed_parameters": {
                    "range_minutes": 15,
                    "test_horizon_minutes": 10,
                },
                "why_test_this": (
                    "A quick recovery after early weakness may be worth checking locally."
                ),
                "useful_result_definition": (
                    "Useful would mean enough examples moved in the tested direction "
                    "more often than they moved against it."
                ),
                "failed_or_unclear_result_definition": (
                    "Unclear would mean there were too few examples or the outcomes were split."
                ),
                "expected_failure_modes": [
                    "too few examples",
                    "mixed results / no clear answer",
                    "local data problem",
                ],
                "safety_notes": "Research only. Local history check only.",
            }
        ],
    }


def idea_batch_schema_help() -> dict[str, Any]:
    """Return copyable schema help for local structured idea batches."""

    return {
        "description": (
            "Paste a structured JSON idea batch. EdgeLab validates the ideas, rejects unsafe "
            "or unsupported ones, and runs supported ideas against local historical data. "
            "This endpoint does not call AI."
        ),
        "required_top_level_fields": IDEA_BATCH_REQUIRED_TOP_LEVEL_FIELDS,
        "required_idea_fields": IDEA_BATCH_REQUIRED_IDEA_FIELDS,
        "allowed_rule_families": [item.value for item in IdeaBatchRuleFamily],
        "forbidden_language_categories": IDEA_BATCH_FORBIDDEN_LANGUAGE_CATEGORIES,
        "minimal_valid_example": idea_batch_minimal_example(),
        "research_only_status": "Research only",
        "real_money_status": "Not allowed",
        "does_not_call_ai": True,
        "does_not_save_results": True,
    }


class IdeaBatchResultLabel(StrEnum):
    """Plain result labels for idea batch testing."""

    WORTH_TESTING_ON_MORE_HISTORY = "worth_testing_on_more_history"
    MIXED_RESULTS_NO_CLEAR_ANSWER = "mixed_results_no_clear_answer"
    NEEDS_MORE_EXAMPLES = "needs_more_examples"
    UNSUPPORTED_RULE = "unsupported_rule"
    DATA_PROBLEM = "data_problem"
    REJECT_FOR_NOW = "reject_for_now"


class AIProposedIntradayIdea(BaseModel):
    """One locked hypothesis proposed outside EdgeLab and tested locally."""

    idea_id: str = Field(min_length=1)
    plain_english_name: str = Field(min_length=1)
    hypothesis: str = Field(min_length=1)
    supported_rule_family: IdeaBatchRuleFamily
    instruments_to_test: tuple[str, ...] = Field(min_length=1)
    required_data: str = Field(min_length=1)
    exact_rule_definition: str = Field(min_length=1)
    fixed_parameters: dict[str, Any] = Field(default_factory=dict)
    why_test_this: str = Field(min_length=1)
    useful_result_definition: str = Field(min_length=1)
    failed_or_unclear_result_definition: str = Field(min_length=1)
    expected_failure_modes: tuple[str, ...] = Field(min_length=1)
    safety_notes: str = Field(min_length=1)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @field_validator("instruments_to_test")
    @classmethod
    def normalize_symbols(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Normalize and de-duplicate proposed symbols."""

        normalized = tuple(dict.fromkeys(normalize_symbol(symbol) for symbol in value))
        if not normalized:
            raise ValueError("instruments_to_test cannot be empty")
        return normalized

    @model_validator(mode="after")
    def validate_safe_idea(self) -> Self:
        """Reject unsafe or non-deterministic proposed ideas."""

        _validate_safe_text(
            " ".join(
                [
                    self.idea_id,
                    self.plain_english_name,
                    self.hypothesis,
                    self.required_data,
                    self.exact_rule_definition,
                    " ".join(f"{key} {value}" for key, value in self.fixed_parameters.items()),
                    self.why_test_this,
                    self.useful_result_definition,
                    self.failed_or_unclear_result_definition,
                    *self.expected_failure_modes,
                    self.safety_notes,
                ]
            ),
            context="AI-proposed intraday idea",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class IdeaBatch(BaseModel):
    """A raw idea batch envelope.

    Ideas intentionally remain raw records here so the runner can reject one unsafe idea
    without failing the whole batch.
    """

    batch_id: str = Field(min_length=1)
    batch_name: str = Field(min_length=1)
    created_for: str = Field(min_length=1)
    ideas: list[dict[str, Any]] = Field(min_length=1)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"
    schema_version: str = IDEA_BATCH_SCHEMA_VERSION

    @model_validator(mode="after")
    def validate_batch_status(self) -> Self:
        """Keep batch envelopes research-only."""

        if self.research_only_status != "Research only":
            raise ValueError("idea batch must remain research-only")
        if self.real_money_status != "Not allowed":
            raise ValueError("idea batch real-money status must be Not allowed")
        _validate_safe_text(
            " ".join([self.batch_id, self.batch_name, self.created_for]),
            context="idea batch envelope",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class IdeaBatchDescription(BaseModel):
    """Lightweight idea batch metadata for list pages."""

    batch_id: str
    batch_name: str
    created_for: str
    ideas_submitted: int
    accepted_ideas: list[str]
    rejected_ideas: list[str]
    securities_tested: list[str]
    best_idea_if_any: str
    current_conclusion: str
    next_action: str
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"


class IdeaBatchIdeaResult(BaseModel):
    """One idea's validation or local test result."""

    idea_id: str
    plain_english_name: str
    supported_rule_family: str
    accepted_for_testing: bool
    classification: IdeaBatchResultLabel
    classification_label: str
    securities_tested: list[str]
    current_conclusion: str
    next_action: str
    rejection_reason: str | None = None
    evidence_score: int = Field(default=0, ge=0, le=100)
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"


class IdeaBatchResult(BaseModel):
    """Research-only result for one structured idea batch."""

    batch_id: str
    batch_name: str
    created_for: str
    ideas_submitted: int
    ideas_tested: int
    securities_tested: list[str]
    best_idea_if_any: str
    current_conclusion: str
    next_action: str
    accepted_ideas: list[IdeaBatchIdeaResult]
    rejected_ideas: list[IdeaBatchIdeaResult]
    ideas_needing_more_examples: list[str]
    ideas_mixed_results: list[str]
    ideas_rejected_for_now: list[str]
    ranked_results: list[IdeaBatchIdeaResult]
    cache_metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = IDEA_BATCH_SCHEMA_VERSION
    code_version: str = IDEA_BATCH_CODE_VERSION
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"


def idea_batch_label(classification: IdeaBatchResultLabel) -> str:
    """Return user-facing wording for an idea batch result."""

    return {
        IdeaBatchResultLabel.WORTH_TESTING_ON_MORE_HISTORY: ("Worth testing on more history"),
        IdeaBatchResultLabel.MIXED_RESULTS_NO_CLEAR_ANSWER: ("Mixed results / no clear answer"),
        IdeaBatchResultLabel.NEEDS_MORE_EXAMPLES: "Needs more examples",
        IdeaBatchResultLabel.UNSUPPORTED_RULE: (
            "EdgeLab cannot test this idea with current local rules"
        ),
        IdeaBatchResultLabel.DATA_PROBLEM: "Local data problem blocked the test",
        IdeaBatchResultLabel.REJECT_FOR_NOW: "Reject for now",
    }[classification]


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
        re.search(rf"\b{re.escape(phrase)}\b", lowered) for phrase in IDEA_BATCH_FORBIDDEN_PHRASES
    ):
        raise ValueError(f"{context} must not contain unsafe research language")
