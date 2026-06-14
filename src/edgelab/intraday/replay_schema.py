"""Historical intraday replay schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from edgelab.intraday.historical_schema import HistoricalIntradayReadiness, normalize_to_utc
from edgelab.intraday.schema import (
    IntradayHypotheticalTrade,
    IntradaySetupCandidate,
    normalize_symbol,
    reject_action_instructions,
)


class HistoricalReplayStatus(StrEnum):
    """Replay status for one local historical intraday session."""

    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    BLOCKED_BY_DATA_QUALITY = "blocked_by_data_quality"
    UNSUPPORTED = "unsupported"
    RESEARCH_ONLY = "research_only"


class HistoricalReplayStepType(StrEnum):
    """Point-in-time replay step labels."""

    SESSION_LOADED = "session_loaded"
    PREMARKET_CONTEXT = "premarket_context"
    REGULAR_OPEN = "regular_open"
    OPENING_RANGE_BUILDING = "opening_range_building"
    OPENING_RANGE_READY = "opening_range_ready"
    EVENT_DETECTED = "event_detected"
    SETUP_DETECTED = "setup_detected"
    NO_TRADE_MARKED = "no_trade_marked"
    HYPOTHETICAL_ENTRY_MARKED = "hypothetical_entry_marked"
    HYPOTHETICAL_EXIT_MARKED = "hypothetical_exit_marked"
    REPLAY_COMPLETED = "replay_completed"
    INSUFFICIENT_DATA = "insufficient_data"


class HistoricalReplayDecisionType(StrEnum):
    """Research-only replay decisions."""

    KEEP_WATCHING = "keep_watching"
    SIT_OUT = "sit_out"
    SETUP_MARKED_FOR_RESEARCH = "setup_marked_for_research"
    HYPOTHETICAL_RESULT_RECORDED = "hypothetical_result_recorded"
    INSUFFICIENT_DATA = "insufficient_data"
    BLOCKED_BY_QUALITY = "blocked_by_quality"


class HistoricalReplayQualityIssue(BaseModel):
    """Replay-specific quality issue."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: str = "warning"
    symbol: str | None = None
    session_id: str | None = None
    replay_time_utc: datetime | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_optional_symbol(cls, value: str | None) -> str | None:
        """Normalize optional symbols."""

        if value is None:
            return None
        return normalize_symbol(value)

    @field_validator("replay_time_utc")
    @classmethod
    def normalize_optional_replay_time(cls, value: datetime | None) -> datetime | None:
        """Normalize optional replay timestamps to UTC."""

        if value is None:
            return None
        return normalize_to_utc(value)

    @model_validator(mode="after")
    def validate_issue_text(self) -> Self:
        """Reject user-facing action instructions in issue text."""

        reject_action_instructions(self.message, "replay quality issue")
        return self


class HistoricalReplayRequest(BaseModel):
    """Request for replaying one historical intraday session."""

    symbol: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    hold_minutes: int = Field(default=5, gt=0)
    slippage_ticks: int = Field(default=1, ge=0)
    commission_per_contract: float = Field(default=0, ge=0)
    max_one_setup_per_day: bool = True
    include_evidence_details: bool = True

    @field_validator("symbol")
    @classmethod
    def normalize_request_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        return normalize_symbol(value)

    @field_validator("session_id")
    @classmethod
    def strip_session_id(cls, value: str) -> str:
        """Require a non-empty session ID after stripping."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("session_id must be non-empty")
        return normalized


class HistoricalReplayStep(BaseModel):
    """One point-in-time replay step."""

    step_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    replay_time_utc: datetime
    step_type: HistoricalReplayStepType
    bars_visible_count: int = Field(ge=0)
    latest_visible_bar_utc: datetime | None = None
    plain_english_summary: str = Field(min_length=1)
    what_edgelab_knew: str = Field(min_length=1)
    what_changed: str = Field(min_length=1)
    quality_issues: list[HistoricalReplayQualityIssue] = Field(default_factory=list)
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    real_money_status: str = "Not allowed"

    @field_validator("symbol")
    @classmethod
    def normalize_step_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        return normalize_symbol(value)

    @field_validator("replay_time_utc", "latest_visible_bar_utc")
    @classmethod
    def normalize_step_times(cls, value: datetime | None) -> datetime | None:
        """Normalize replay step timestamps to UTC."""

        if value is None:
            return None
        return normalize_to_utc(value)

    @model_validator(mode="after")
    def validate_step_text(self) -> Self:
        """Keep replay steps conservative."""

        if self.real_money_status != "Not allowed":
            raise ValueError("replay step real-money status must be Not allowed")
        reject_action_instructions(
            " ".join([self.plain_english_summary, self.what_edgelab_knew, self.what_changed]),
            "replay step text",
        )
        if (
            self.latest_visible_bar_utc is not None
            and self.latest_visible_bar_utc > self.replay_time_utc
        ):
            raise ValueError("latest visible bar must not be after replay time")
        return self


class HistoricalReplayDecision(BaseModel):
    """One research-only replay decision."""

    decision_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    replay_time_utc: datetime
    decision_type: HistoricalReplayDecisionType
    plain_english_summary: str = Field(min_length=1)
    why: str = Field(min_length=1)
    what_would_change_our_mind: str = Field(min_length=1)
    what_to_check_next: str = Field(min_length=1)
    linked_setup_id: str | None = None
    linked_trade_id: str | None = None
    real_money_status: str = "Not allowed"

    @field_validator("symbol")
    @classmethod
    def normalize_decision_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        return normalize_symbol(value)

    @field_validator("replay_time_utc")
    @classmethod
    def normalize_decision_time(cls, value: datetime) -> datetime:
        """Normalize decision timestamps to UTC."""

        return normalize_to_utc(value)

    @model_validator(mode="after")
    def validate_decision_text(self) -> Self:
        """Keep decisions conservative and research-only."""

        if self.real_money_status != "Not allowed":
            raise ValueError("replay decision real-money status must be Not allowed")
        reject_action_instructions(
            " ".join(
                [
                    self.plain_english_summary,
                    self.why,
                    self.what_would_change_our_mind,
                    self.what_to_check_next,
                ]
            ),
            "replay decision text",
        )
        return self


class HistoricalReplaySummary(BaseModel):
    """Compact plain-English replay summary."""

    bottom_line: str = Field(min_length=1)
    what_edgelab_tested: str = Field(min_length=1)
    what_happened: str = Field(min_length=1)
    why_it_might_be_misleading: str = Field(min_length=1)
    next_review_item: str = Field(min_length=1)
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_summary_text(self) -> Self:
        """Keep summary copy safe."""

        if self.real_money_status != "Not allowed":
            raise ValueError("replay summary real-money status must be Not allowed")
        reject_action_instructions(
            " ".join(
                [
                    self.bottom_line,
                    self.what_edgelab_tested,
                    self.what_happened,
                    self.why_it_might_be_misleading,
                    self.next_review_item,
                ]
            ),
            "replay summary text",
        )
        return self


class HistoricalReplayCardContext(BaseModel):
    """Context for rendering a replay card."""

    result: HistoricalReplayResult


class HistoricalReplayResult(BaseModel):
    """Research-only historical intraday replay result."""

    replay_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    status: HistoricalReplayStatus
    session_readiness: HistoricalIntradayReadiness
    steps: list[HistoricalReplayStep] = Field(default_factory=list)
    decisions: list[HistoricalReplayDecision] = Field(default_factory=list)
    setup_candidates: list[IntradaySetupCandidate] = Field(default_factory=list)
    hypothetical_trades: list[IntradayHypotheticalTrade] = Field(default_factory=list)
    quality_issues: list[HistoricalReplayQualityIssue] = Field(default_factory=list)
    bottom_line: str = Field(min_length=1)
    what_edgelab_tested: str = Field(min_length=1)
    what_happened: str = Field(min_length=1)
    why_it_might_be_misleading: str = Field(min_length=1)
    next_review_item: str = Field(min_length=1)
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @field_validator("symbol")
    @classmethod
    def normalize_result_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        return normalize_symbol(value)

    @model_validator(mode="after")
    def validate_result_text(self) -> Self:
        """Keep replay results conservative and internally consistent."""

        if self.research_only_status != "Research only":
            raise ValueError("replay result must remain research-only")
        if self.real_money_status != "Not allowed":
            raise ValueError("replay result real-money status must be Not allowed")
        reject_action_instructions(
            " ".join(
                [
                    self.bottom_line,
                    self.what_edgelab_tested,
                    self.what_happened,
                    self.why_it_might_be_misleading,
                    self.next_review_item,
                ]
            ),
            "replay result text",
        )
        return self
