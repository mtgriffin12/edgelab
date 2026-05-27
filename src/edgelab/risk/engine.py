"""Deterministic risk engine placeholders."""

from typing import Literal

from pydantic import BaseModel, Field

Mode = Literal["research", "paper", "live"]


class RiskDecision(BaseModel):
    """A deterministic risk decision."""

    allowed: bool
    mode: Mode
    reasons: list[str] = Field(default_factory=list)


def evaluate_basic_risk(mode: Mode) -> RiskDecision:
    """Allow research and paper placeholders while rejecting live trading."""

    if mode == "live":
        return RiskDecision(
            allowed=False,
            mode=mode,
            reasons=["Live trading is disabled in Phase 0."],
        )

    return RiskDecision(
        allowed=True,
        mode=mode,
        reasons=["Research and paper-mode placeholders are allowed in Phase 0."],
    )
