"""Strategy discovery lab schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


class DiscoveryLane(StrEnum):
    """Discovery lanes for strategy ideas."""

    KNOWN_STRATEGY_LIBRARY = "known_strategy_library"
    EDGE_INNOVATION_LAB = "edge_innovation_lab"


class StrategyProvenance(StrEnum):
    """Where a discovery idea came from."""

    CANONICAL = "canonical"
    ADAPTIVE_CANONICAL = "adaptive_canonical"
    NOVEL_HYPOTHESIS = "novel_hypothesis"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


class EdgeHypothesisStatus(StrEnum):
    """Research status for a discovery hypothesis."""

    IDEA = "idea"
    RESEARCH_CANDIDATE = "research_candidate"
    BASELINE_REQUIRED = "baseline_required"
    NEEDS_BACKTEST = "needs_backtest"
    NEEDS_ROBUSTNESS_TESTING = "needs_robustness_testing"
    REJECTED = "rejected"
    PROMOTED_TO_STRATEGY_REGISTRY = "promoted_to_strategy_registry"


class EdgeBehaviorType(StrEnum):
    """Market behavior a discovery idea tries to explain."""

    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    PANIC_REVERSAL = "panic_reversal"
    EARNINGS_DRIFT = "earnings_drift"
    SECTOR_ROTATION = "sector_rotation"
    SENTIMENT_DISAGREEMENT = "sentiment_disagreement"
    CROWDING_RISK = "crowding_risk"
    REGIME_FOLLOWING = "regime_following"
    VOLATILITY_EXPANSION = "volatility_expansion"
    VOLATILITY_CONTRACTION = "volatility_contraction"
    LIQUIDITY_DISLOCATION = "liquidity_dislocation"
    QUALITY_PULLBACK = "quality_pullback"
    OTHER = "other"


class RegimeFitLabel(StrEnum):
    """Plain labels for scaffolded regime fit."""

    POOR_FIT = "poor_fit"
    WEAK_FIT = "weak_fit"
    POSSIBLE_FIT = "possible_fit"
    STRONG_FIT = "strong_fit"
    INSUFFICIENT_DATA = "insufficient_data"


class BaselineRequirement(BaseModel):
    """Simpler idea that a discovery record must beat."""

    baseline_id: str | None = None
    description: str = Field(min_length=1)
    must_beat: str = Field(min_length=1)


class CurrentRegimeFit(BaseModel):
    """Scaffolded local assessment of current environment fit."""

    score: int = Field(ge=0, le=10)
    label: RegimeFitLabel
    plain_english_reason: str = Field(min_length=1)
    matching_conditions: list[str] = Field(default_factory=list)
    missing_conditions: list[str] = Field(default_factory=list)
    caution: str = Field(min_length=1)


class StrategyGenealogyNode(BaseModel):
    """Parent/child relationship metadata for discovery ideas."""

    discovery_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    provenance: StrategyProvenance
    parent_discovery_id: str | None = None
    plain_english_difference: str = Field(default="Root idea")


class ExperimentLedgerEntry(BaseModel):
    """Scaffolded experiment memory for discovery ideas."""

    experiment_id: str = Field(min_length=1)
    discovery_id: str = Field(min_length=1)
    strategy_id: str | None = None
    experiment_type: str = Field(min_length=1)
    hypothesis: str = Field(min_length=1)
    baseline_compared: str = Field(min_length=1)
    data_used: str = Field(min_length=1)
    result_summary: str = Field(min_length=1)
    outcome: str = Field(pattern="^(not_run|inconclusive|failed|improved|promising|rejected)$")
    lessons_learned: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StrategyDiscoveryRecord(BaseModel):
    """Research-only discovery record for a strategy idea."""

    discovery_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    lane: DiscoveryLane
    provenance: StrategyProvenance
    behavior_type: EdgeBehaviorType
    plain_english_summary: str = Field(min_length=1)
    market_behavior: str = Field(min_length=1)
    why_it_might_work: str = Field(min_length=1)
    why_it_might_work_now: str = Field(min_length=1)
    why_others_might_miss_it: str = Field(min_length=1)
    baseline_to_beat: BaselineRequirement
    evidence_needed: list[str] = Field(min_length=1)
    disproof_conditions: list[str] = Field(min_length=1)
    best_market_conditions: list[str] = Field(min_length=1)
    worst_market_conditions: list[str] = Field(min_length=1)
    data_needed: list[str] = Field(min_length=1)
    complexity_score: int = Field(ge=0, le=10)
    novelty_score: int = Field(ge=0, le=10)
    overfitting_risk_score: int = Field(ge=0, le=10)
    current_regime_fit: CurrentRegimeFit
    parent_discovery_id: str | None = None
    derived_strategy_id: str | None = None
    status: EdgeHypothesisStatus = EdgeHypothesisStatus.IDEA
    rejection_reasons: list[str] = Field(default_factory=list)
    adaptation_notes: str | None = None
    created_by: str = "system_fixture"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("discovery_id")
    @classmethod
    def validate_discovery_id(cls, value: str) -> str:
        """Validate machine-friendly discovery IDs."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("discovery_id must be non-empty")
        if normalized.lower() != normalized or " " in normalized:
            raise ValueError("discovery_id must be machine-friendly")
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-_")
        if any(character not in allowed for character in normalized):
            raise ValueError("discovery_id must be machine-friendly")
        return normalized

    @model_validator(mode="after")
    def validate_discovery_record(self) -> Self:
        """Validate baseline, adaptation, and rejection rules."""

        if self.provenance == StrategyProvenance.NOVEL_HYPOTHESIS and not has_baseline_requirement(
            self
        ):
            raise ValueError("novel_hypothesis records must have a baseline_to_beat")
        if self.provenance == StrategyProvenance.ADAPTIVE_CANONICAL and not self.adaptation_notes:
            raise ValueError("adaptive_canonical records must identify what changed")
        if self.provenance == StrategyProvenance.REJECTED and not self.rejection_reasons:
            raise ValueError("rejected records must include rejection reasons")
        if self.status == EdgeHypothesisStatus.REJECTED and not self.rejection_reasons:
            raise ValueError("rejected records must include rejection reasons")
        return self


def has_baseline_requirement(record: StrategyDiscoveryRecord) -> bool:
    """Return whether a discovery record has a usable baseline requirement."""

    baseline = record.baseline_to_beat
    return bool(baseline.description.strip() and baseline.must_beat.strip())
