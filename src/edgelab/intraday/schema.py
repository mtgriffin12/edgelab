"""Research-only intraday schemas."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

ACTION_INSTRUCTION_PHRASES = [
    "buy now",
    "sell now",
    "short now",
    "go short",
    "enter short",
    "enter a trade",
    "place an order",
    "submit an order",
    "execute a trade",
    "open a trade",
    "trade now",
    "ready for real money",
    "approved for real money",
]


class IntradayInstrumentType(StrEnum):
    """Supported intraday instrument categories."""

    INDEX_FUTURE = "index_future"
    MICRO_INDEX_FUTURE = "micro_index_future"
    INDEX_ETF_REFERENCE = "index_etf_reference"
    EQUITY_REFERENCE = "equity_reference"
    SYNTHETIC_INDEX_REFERENCE = "synthetic_index_reference"
    SYNTHETIC_EQUITY_REFERENCE = "synthetic_equity_reference"
    OTHER = "other"


class IntradaySessionType(StrEnum):
    """Supported synthetic intraday session segments."""

    OVERNIGHT = "overnight"
    PREMARKET = "premarket"
    REGULAR_FIRST_HOUR = "regular_first_hour"
    REGULAR_SESSION = "regular_session"
    AFTER_HOURS = "after_hours"


class IntradayBarInterval(StrEnum):
    """Supported intraday bar intervals."""

    ONE_MINUTE = "one_minute"
    FIVE_MINUTE = "five_minute"


class CandleDirection(StrEnum):
    """Candle close direction relative to the open."""

    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class CandleShape(StrEnum):
    """Simple deterministic candle shape labels."""

    STRONG_UP = "strong_up"
    STRONG_DOWN = "strong_down"
    INDECISION = "indecision"
    REVERSAL_LIKE = "reversal_like"
    ORDINARY = "ordinary"
    INVALID = "invalid"


class IntradayEventType(StrEnum):
    """Measurable first-hour event labels."""

    OPENING_GAP_UP = "opening_gap_up"
    OPENING_GAP_DOWN = "opening_gap_down"
    OPENING_RANGE_BREAKOUT = "opening_range_breakout"
    OPENING_RANGE_FAILURE = "opening_range_failure"
    FAILED_OPENING_PUSH = "failed_opening_push"
    FAILED_OPENING_SELLOFF = "failed_opening_selloff"
    OVERNIGHT_HIGH_SWEEP = "overnight_high_sweep"
    OVERNIGHT_LOW_SWEEP = "overnight_low_sweep"
    MOMENTUM_CONTINUATION = "momentum_continuation"
    MOMENTUM_EXHAUSTION = "momentum_exhaustion"
    VWAP_RECLAIM_PLACEHOLDER = "vwap_reclaim_placeholder"
    VWAP_REJECTION_PLACEHOLDER = "vwap_rejection_placeholder"
    PAIRED_SYMBOL_WEAKER_THAN_REFERENCE = "paired_symbol_weaker_than_reference"
    PAIRED_SYMBOL_STRONGER_THAN_REFERENCE = "paired_symbol_stronger_than_reference"
    NQ_WEAKER_THAN_SP_REFERENCE = "nq_weaker_than_sp_reference"
    NQ_STRONGER_THAN_SP_REFERENCE = "nq_stronger_than_sp_reference"
    NO_TRADE_CHOPPY_OPEN = "no_trade_choppy_open"
    NO_TRADE_LOW_RANGE = "no_trade_low_range"
    NO_TRADE_CONFLICTING_SIGNALS = "no_trade_conflicting_signals"


class IntradaySetupType(StrEnum):
    """Research-only setup families."""

    OPENING_RANGE_BREAKOUT = "opening_range_breakout"
    OPENING_RANGE_FAILURE = "opening_range_failure"
    FAILED_OPENING_PUSH = "failed_opening_push"
    FAILED_OPENING_SELLOFF = "failed_opening_selloff"
    OVERNIGHT_LEVEL_SWEEP = "overnight_level_sweep"
    GAP_FADE = "gap_fade"
    GAP_CONTINUATION = "gap_continuation"
    INDEX_DIVERGENCE = "index_divergence"
    NO_TRADE = "no_trade"


class IntradaySetupDirection(StrEnum):
    """Descriptive context only; not an action instruction."""

    LONG_CONTEXT = "long_context"
    SHORT_CONTEXT = "short_context"
    NO_TRADE_CONTEXT = "no_trade_context"


class IntradaySetupStatus(StrEnum):
    """Research-only setup status."""

    DETECTED = "detected"
    WATCH_ONLY = "watch_only"
    INVALIDATED = "invalidated"
    SIMULATED = "simulated"
    SKIPPED = "skipped"
    UNSUPPORTED = "unsupported"


class NoTradeReasonType(StrEnum):
    """Reasons EdgeLab may sit out."""

    CHOPPY_OPEN = "choppy_open"
    LOW_RANGE = "low_range"
    CONFLICTING_SIGNALS = "conflicting_signals"
    INSUFFICIENT_DATA = "insufficient_data"
    UNSUPPORTED_SETUP = "unsupported_setup"


class IntradaySpikeVerdict(StrEnum):
    """Research-spike verdict, not a performance verdict."""

    WORKFLOW_SUPPORTED = "workflow_supported"
    NEEDS_RULE_REFINEMENT = "needs_rule_refinement"
    INSUFFICIENT_FIXTURE_COVERAGE = "insufficient_fixture_coverage"
    NOT_PROMISING_IN_SYNTHETIC_TEST = "not_promising_in_synthetic_test"


class IntradayQualityIssue(BaseModel):
    """Structured intraday quality issue."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: str = "warning"
    symbol: str | None = None
    session_id: str | None = None
    timestamp: datetime | None = None
    row_number: int | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_optional_symbol(cls, value: str | None) -> str | None:
        """Normalize optional symbols."""

        if value is None:
            return None
        return normalize_symbol(value)


class IntradayInstrument(BaseModel):
    """Synthetic intraday instrument metadata."""

    symbol: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    instrument_type: IntradayInstrumentType
    point_value: float = Field(gt=0)
    tick_size: float = Field(gt=0)
    tick_value: float = Field(gt=0)
    plain_english_description: str = Field(min_length=1)

    @field_validator("symbol")
    @classmethod
    def normalize_instrument_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        return normalize_symbol(value)


class IntradayBar(BaseModel):
    """Normalized intraday OHLCV bar."""

    symbol: str = Field(min_length=1)
    timestamp: datetime
    interval: IntradayBarInterval
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)
    session_type: IntradaySessionType
    session_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    ingested_at: datetime

    @field_validator("symbol")
    @classmethod
    def normalize_bar_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        return normalize_symbol(value)

    @field_validator("session_id", "source")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        """Require non-empty text after stripping."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("value must be non-empty")
        return normalized

    @model_validator(mode="after")
    def validate_ohlc_relationships(self) -> Self:
        """Validate OHLC relationships."""

        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be greater than or equal to open, close, and low")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be less than or equal to open, close, and high")
        return self


class OpeningBenchmarks(BaseModel):
    """Opening reference levels for one synthetic session."""

    symbol: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    session_date: date
    prior_regular_close: float | None = Field(default=None, gt=0)
    overnight_high: float | None = Field(default=None, gt=0)
    overnight_low: float | None = Field(default=None, gt=0)
    premarket_high: float | None = Field(default=None, gt=0)
    premarket_low: float | None = Field(default=None, gt=0)
    regular_open: float | None = Field(default=None, gt=0)
    opening_range_high: float | None = Field(default=None, gt=0)
    opening_range_low: float | None = Field(default=None, gt=0)
    opening_gap_pct: float | None = None
    first_hour_high: float | None = Field(default=None, gt=0)
    first_hour_low: float | None = Field(default=None, gt=0)
    plain_english_summary: str = Field(min_length=1)
    quality_issues: list[IntradayQualityIssue] = Field(default_factory=list)

    @field_validator("symbol")
    @classmethod
    def normalize_benchmark_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        return normalize_symbol(value)


class IntradayEvent(BaseModel):
    """One measurable intraday event."""

    event_type: IntradayEventType
    symbol: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    timestamp: datetime
    direction: IntradaySetupDirection | None = None
    related_price: float | None = Field(default=None, gt=0)
    related_level_name: str | None = None
    plain_english_summary: str = Field(min_length=1)
    quality_issues: list[IntradayQualityIssue] = Field(default_factory=list)

    @field_validator("symbol")
    @classmethod
    def normalize_event_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        return normalize_symbol(value)

    @model_validator(mode="after")
    def validate_event_copy(self) -> Self:
        """Reject action instructions in event explanations."""

        reject_action_instructions(self.plain_english_summary, "event text")
        return self


class NoTradeReason(BaseModel):
    """Reason EdgeLab may choose no setup."""

    reason_type: NoTradeReasonType
    message: str = Field(min_length=1)
    severity: str = "warning"

    @model_validator(mode="after")
    def validate_reason_copy(self) -> Self:
        """Reject action instructions in no-trade reasons."""

        reject_action_instructions(self.message, "no-trade reason")
        return self


class IntradaySetupCandidate(BaseModel):
    """A research-only intraday setup candidate."""

    setup_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    session_date: date
    setup_type: IntradaySetupType
    direction: IntradaySetupDirection
    status: IntradaySetupStatus
    detected_at: datetime
    signal_bar_timestamp: datetime
    benchmark_context: OpeningBenchmarks
    supporting_events: list[IntradayEvent] = Field(default_factory=list)
    no_trade_reasons: list[NoTradeReason] = Field(default_factory=list)
    plain_english_summary: str = Field(min_length=1)
    why_it_appeared: list[str] = Field(min_length=1)
    what_would_invalidate_it: list[str] = Field(min_length=1)
    what_is_missing: list[str] = Field(min_length=1)
    why_edgelab_might_sit_out: list[str] = Field(min_length=1)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @field_validator("symbol")
    @classmethod
    def normalize_setup_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        return normalize_symbol(value)

    @model_validator(mode="after")
    def validate_research_only_setup(self) -> Self:
        """Keep setup output conservative and research-only."""

        if self.real_money_status != "Not allowed":
            raise ValueError("setup real-money status must be Not allowed")
        reject_action_instructions(_setup_text(self), "setup text")
        if self.direction == IntradaySetupDirection.NO_TRADE_CONTEXT and not self.no_trade_reasons:
            raise ValueError("no-trade setups must include a no-trade reason")
        return self


class IntradaySimulationAssumptions(BaseModel):
    """Assumptions for one local hypothetical intraday simulation."""

    initial_capital: float = Field(default=50000, gt=0)
    max_hypothetical_position_value: float = Field(default=50000, gt=0)
    contract_count: int = Field(default=1, gt=0)
    hold_minutes: int = Field(default=5, gt=0)
    stop_points: float | None = Field(default=None, gt=0)
    target_points: float | None = Field(default=None, gt=0)
    slippage_ticks: int = Field(default=1, ge=0)
    commission_per_contract: float = Field(default=0, ge=0)
    allow_short_context: bool = True
    max_one_setup_per_day: bool = True


class IntradayHypotheticalTrade(BaseModel):
    """A hypothetical fixture-backed trade result."""

    trade_id: str = Field(min_length=1)
    setup_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    direction: IntradaySetupDirection
    signal_time: datetime
    entry_time: datetime
    entry_price: float = Field(gt=0)
    exit_time: datetime
    exit_price: float = Field(gt=0)
    contract_count: int = Field(gt=0)
    gross_points: float
    gross_pnl: float
    estimated_costs: float = Field(ge=0)
    net_pnl: float
    result_label: str = Field(min_length=1)
    plain_english_reason: str = Field(min_length=1)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @field_validator("symbol")
    @classmethod
    def normalize_trade_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        return normalize_symbol(value)

    @model_validator(mode="after")
    def validate_trade_text(self) -> Self:
        """Keep hypothetical trades research-only."""

        if self.real_money_status != "Not allowed":
            raise ValueError("hypothetical trade real-money status must be Not allowed")
        reject_action_instructions(self.plain_english_reason, "hypothetical trade text")
        return self


class IntradaySimulationResult(BaseModel):
    """Research-only intraday simulation result."""

    result_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    session_date: date
    setup_count: int = Field(ge=0)
    simulated_trade_count: int = Field(ge=0)
    no_trade_reason_count: int = Field(ge=0)
    total_net_pnl: float
    average_net_pnl: float
    best_trade_net_pnl: float
    worst_trade_net_pnl: float
    win_rate_pct: float = Field(ge=0, le=100)
    spike_verdict: IntradaySpikeVerdict
    setup_candidates: list[IntradaySetupCandidate] = Field(default_factory=list)
    hypothetical_trades: list[IntradayHypotheticalTrade] = Field(default_factory=list)
    quality_issues: list[IntradayQualityIssue] = Field(default_factory=list)
    plain_english_summary: str = Field(min_length=1)
    conclusion: str = Field(min_length=1)
    real_money_status: str = "Not allowed"

    @field_validator("symbol")
    @classmethod
    def normalize_result_symbol(cls, value: str) -> str:
        """Normalize symbols to uppercase."""

        return normalize_symbol(value)

    @model_validator(mode="after")
    def validate_result_text(self) -> Self:
        """Keep simulation results conservative."""

        if self.real_money_status != "Not allowed":
            raise ValueError("simulation real-money status must be Not allowed")
        reject_action_instructions(
            " ".join([self.plain_english_summary, self.conclusion]), "simulation result text"
        )
        if self.simulated_trade_count != len(self.hypothetical_trades):
            raise ValueError("simulated trade count must match hypothetical trades")
        return self


def normalize_symbol(value: str) -> str:
    """Normalize a non-empty symbol."""

    normalized = value.strip().upper()
    if not normalized:
        raise ValueError("symbol must be non-empty")
    return normalized


def reject_action_instructions(text: str, field_name: str) -> None:
    """Reject user-facing action instructions while allowing context labels."""

    lowered = text.lower()
    if any(phrase in lowered for phrase in ACTION_INSTRUCTION_PHRASES):
        raise ValueError(f"{field_name} must not contain action instructions")


def utc_now() -> datetime:
    """Return current UTC timestamp."""

    return datetime.now(UTC)


def _setup_text(setup: IntradaySetupCandidate) -> str:
    return " ".join(
        [
            setup.plain_english_summary,
            " ".join(setup.why_it_appeared),
            " ".join(setup.what_would_invalidate_it),
            " ".join(setup.what_is_missing),
            " ".join(setup.why_edgelab_might_sit_out),
            " ".join(reason.message for reason in setup.no_trade_reasons),
            " ".join(event.plain_english_summary for event in setup.supporting_events),
        ]
    )
