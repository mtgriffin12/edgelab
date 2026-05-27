"""Pydantic strategy specification models."""

from pydantic import BaseModel, Field


class StrategyUniverse(BaseModel):
    """Assets and filters a strategy may consider."""

    asset_class: str = "US equities and ETFs"
    symbols: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)


class StrategySignal(BaseModel):
    """A structured signal definition."""

    name: str
    description: str
    inputs: list[str] = Field(default_factory=list)
    rule: str


class StrategyRiskRule(BaseModel):
    """A deterministic risk constraint for a strategy."""

    name: str
    description: str
    veto_condition: str


class StrategySpec(BaseModel):
    """A testable trading strategy specification."""

    strategy_id: str
    name: str
    description: str
    asset_class: str = "US equities and ETFs"
    universe: StrategyUniverse
    signals: list[StrategySignal] = Field(default_factory=list)
    entry_rule: str
    exit_rule: str
    position_sizing_rule: str
    risk_rules: list[StrategyRiskRule] = Field(default_factory=list)
    holding_period: str
    market_regime_filter: str | None = None
    expected_edge: str
    failure_conditions: list[str] = Field(default_factory=list)
    eligible_for_paper_trading: bool = False
    eligible_for_live_trading: bool = False
