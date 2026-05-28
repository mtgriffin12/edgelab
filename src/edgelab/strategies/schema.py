"""Pydantic strategy specification models."""

import re
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

MACHINE_FRIENDLY_ID = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")


class AssetClass(StrEnum):
    """Supported strategy asset classes."""

    US_EQUITIES = "us_equities"
    ETFS = "etfs"
    US_EQUITIES_AND_ETFS = "us_equities_and_etfs"
    OPTIONS = "options"
    CRYPTO = "crypto"


class TradingHorizon(StrEnum):
    """Supported research horizons."""

    DAILY = "daily"
    MULTI_DAY_SWING = "multi_day_swing"
    INTRADAY = "intraday"


class StrategyStatus(StrEnum):
    """Lifecycle state for a strategy candidate."""

    DRAFT = "draft"
    RESEARCH_CANDIDATE = "research_candidate"
    BACKTEST_CANDIDATE = "backtest_candidate"
    REJECTED = "rejected"
    RETIRED = "retired"


class StrategyDirection(StrEnum):
    """Directional posture represented by a strategy."""

    LONG_ONLY = "long_only"
    SHORT_ONLY = "short_only"
    LONG_SHORT = "long_short"
    MARKET_NEUTRAL = "market_neutral"
    CASH_NO_TRADE = "cash_no_trade"


class SignalType(StrEnum):
    """Type of evidence used by a strategy signal."""

    PRICE = "price"
    VOLUME = "volume"
    SENTIMENT = "sentiment"
    FUNDAMENTAL = "fundamental"
    MACRO = "macro"
    MARKET_REGIME = "market_regime"
    RISK = "risk"


class StrategyUniverse(BaseModel):
    """Assets and filters a strategy may consider."""

    description: str = Field(min_length=1)
    symbols: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)


class StrategySignal(BaseModel):
    """A structured signal definition."""

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    signal_type: SignalType
    inputs: list[str] = Field(default_factory=list)
    rule: str = Field(min_length=1)


class EntryRule(BaseModel):
    """A deterministic entry condition."""

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    rule: str = Field(min_length=1)


class ExitRule(BaseModel):
    """A deterministic exit condition."""

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    rule: str = Field(min_length=1)


class PositionSizingRule(BaseModel):
    """A position sizing rule for research and validation."""

    method: str = Field(min_length=1)
    description: str = Field(min_length=1)
    max_position_size: str | None = None


class RiskRule(BaseModel):
    """A deterministic risk constraint for a strategy."""

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    veto_condition: str = Field(min_length=1)


class MarketRegimeFilter(BaseModel):
    """Market regime context for a strategy."""

    description: str = Field(min_length=1)
    allowed_regimes: list[str] = Field(default_factory=list)
    blocked_regimes: list[str] = Field(default_factory=list)


class StrategyEvidenceRequirement(BaseModel):
    """Evidence required before promotion."""

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    minimum_threshold: str = Field(min_length=1)


class StrategySpec(BaseModel):
    """A testable trading strategy specification."""

    strategy_id: str
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    thesis: str = Field(min_length=1)
    asset_class: AssetClass = AssetClass.US_EQUITIES_AND_ETFS
    direction: StrategyDirection = StrategyDirection.LONG_ONLY
    horizon: TradingHorizon = TradingHorizon.MULTI_DAY_SWING
    universe: StrategyUniverse
    signals: list[StrategySignal] = Field(min_length=1)
    entry_rules: list[EntryRule] = Field(min_length=1)
    exit_rules: list[ExitRule] = Field(min_length=1)
    position_sizing: PositionSizingRule
    risk_rules: list[RiskRule] = Field(min_length=1)
    holding_period: str = Field(min_length=1)
    market_regime_filter: MarketRegimeFilter | None = None
    expected_edge: str = Field(min_length=1)
    failure_conditions: list[str] = Field(min_length=1)
    evidence_required: list[StrategyEvidenceRequirement] = Field(min_length=1)
    status: StrategyStatus = StrategyStatus.RESEARCH_CANDIDATE
    rejection_reasons: list[str] = Field(default_factory=list)
    eligible_for_research: bool = True
    eligible_for_backtesting: bool = False
    eligible_for_paper_trading: bool = False
    eligible_for_live_trading: bool = False
    uses_margin: bool = False

    @field_validator("strategy_id")
    @classmethod
    def validate_strategy_id(cls, value: str) -> str:
        """Require stable machine-friendly identifiers."""

        if not value or not MACHINE_FRIENDLY_ID.fullmatch(value):
            raise ValueError("strategy_id must be non-empty, lowercase, and machine-friendly")
        return value

    @model_validator(mode="after")
    def validate_eligibility(self) -> Self:
        """Prevent unsafe promotion states."""

        if self.eligible_for_live_trading and not self.eligible_for_paper_trading:
            raise ValueError("live trading eligibility requires paper trading eligibility")

        if self.eligible_for_paper_trading and not self.eligible_for_backtesting:
            raise ValueError("paper trading eligibility requires backtesting eligibility")

        has_future_only_scope = (
            self.asset_class in {AssetClass.OPTIONS, AssetClass.CRYPTO}
            or self.horizon == TradingHorizon.INTRADAY
            or self.direction in {StrategyDirection.SHORT_ONLY, StrategyDirection.LONG_SHORT}
            or self.uses_margin
        )
        if has_future_only_scope and (
            self.eligible_for_paper_trading or self.eligible_for_live_trading
        ):
            raise ValueError(
                "options, crypto, intraday, shorting, and margin strategies are future-only"
            )

        return self
