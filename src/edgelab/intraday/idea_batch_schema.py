"""Schemas for structured local intraday idea batches."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from edgelab.intraday.schema import normalize_symbol

IDEA_BATCH_SCHEMA_VERSION = "phase_7x_2l_v1"
IDEA_BATCH_CODE_VERSION = "phase_7x_2l"

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

IDEA_BATCH_FIELD_TYPES = {
    "batch_id": "string",
    "batch_name": "string",
    "created_for": "string",
    "research_only_status": "string, must equal Research only",
    "real_money_status": "string, must equal Not allowed",
    "ideas": "non-empty array of idea objects",
    "idea_id": "string",
    "plain_english_name": "string",
    "hypothesis": "string",
    "supported_rule_family": "string from allowed_rule_families",
    "instruments_to_test": "non-empty array of strings",
    "required_data": "array of strings",
    "exact_rule_definition": "string",
    "fixed_parameters": "object with JSON-compatible values",
    "why_test_this": "string",
    "useful_result_definition": "string",
    "failed_or_unclear_result_definition": "string",
    "expected_failure_modes": "non-empty array of strings",
    "safety_notes": "string",
}


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
                "required_data": [
                    "1-minute bars",
                    "first-hour price range",
                ],
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
            "Paste a structured JSON idea batch. EdgeLab checks the JSON shape, separates "
            "unsupported rule families, and runs supported ideas against local historical "
            "data. This endpoint does not call AI."
        ),
        "required_top_level_fields": IDEA_BATCH_REQUIRED_TOP_LEVEL_FIELDS,
        "required_idea_fields": IDEA_BATCH_REQUIRED_IDEA_FIELDS,
        "field_types": IDEA_BATCH_FIELD_TYPES,
        "allowed_rule_families": [item.value for item in IdeaBatchRuleFamily],
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
    instruments_to_test: list[str] = Field(min_length=1)
    required_data: list[str] = Field(min_length=1)
    exact_rule_definition: str = Field(min_length=1)
    fixed_parameters: dict[str, Any] = Field(default_factory=dict)
    why_test_this: str = Field(min_length=1)
    useful_result_definition: str = Field(min_length=1)
    failed_or_unclear_result_definition: str = Field(min_length=1)
    expected_failure_modes: list[str] = Field(min_length=1)
    safety_notes: str = Field(min_length=1)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @field_validator("instruments_to_test")
    @classmethod
    def normalize_symbols(cls, value: list[str]) -> list[str]:
        """Normalize and de-duplicate proposed symbols."""

        normalized = list(dict.fromkeys(normalize_symbol(symbol) for symbol in value))
        if not normalized:
            raise ValueError("instruments_to_test cannot be empty")
        return normalized

    @field_validator("fixed_parameters")
    @classmethod
    def validate_fixed_parameters(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Accept normal JSON objects and reject non-JSON Python values."""

        for key, item in value.items():
            if not _is_json_compatible(item):
                raise ValueError(f"fixed_parameters.{key} must be a JSON-compatible value")
        return value

    @model_validator(mode="after")
    def validate_status_fields(self) -> Self:
        """Keep individual idea records inside the research-only boundary."""

        _validate_research_status(
            context="AI-proposed intraday idea",
            research_only_status=self.research_only_status,
            real_money_status=self.real_money_status,
        )
        return self


class IdeaBatch(BaseModel):
    """A raw idea batch envelope.

    Ideas intentionally remain raw records here so the runner can reject one malformed idea
    without failing the whole batch.
    """

    batch_id: str = Field(min_length=1)
    batch_name: str = Field(min_length=1)
    created_for: str = Field(min_length=1)
    ideas: list[dict[str, Any]] = Field(min_length=1)
    research_only_status: str = Field(min_length=1)
    real_money_status: str = Field(min_length=1)
    schema_version: str = IDEA_BATCH_SCHEMA_VERSION

    @model_validator(mode="after")
    def validate_batch_status(self) -> Self:
        """Keep batch envelopes research-only."""

        if self.research_only_status != "Research only":
            raise ValueError("idea batch must remain research-only")
        if self.real_money_status != "Not allowed":
            raise ValueError("idea batch real-money status must be Not allowed")
        _validate_research_status(
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


def _validate_research_status(
    context: str,
    research_only_status: str,
    real_money_status: str,
) -> None:
    if research_only_status != "Research only":
        raise ValueError(f"{context} must remain research-only")
    if real_money_status != "Not allowed":
        raise ValueError(f"{context} real-money status must be Not allowed")


def _is_json_compatible(value: object) -> bool:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, list):
        return all(_is_json_compatible(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_json_compatible(item) for key, item in value.items()
        )
    return False
