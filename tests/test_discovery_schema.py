from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from edgelab.discovery.regime import make_regime_fit
from edgelab.discovery.schema import (
    BaselineRequirement,
    DiscoveryLane,
    EdgeBehaviorType,
    EdgeHypothesisStatus,
    StrategyDiscoveryRecord,
    StrategyProvenance,
    has_baseline_requirement,
)


def build_discovery_record(**overrides: object) -> StrategyDiscoveryRecord:
    data: dict[str, object] = {
        "discovery_id": "sample-discovery",
        "title": "Sample Discovery",
        "lane": DiscoveryLane.KNOWN_STRATEGY_LIBRARY,
        "provenance": StrategyProvenance.CANONICAL,
        "behavior_type": EdgeBehaviorType.MOMENTUM,
        "plain_english_summary": "A sample local research idea.",
        "market_behavior": "Persistent strength can sometimes continue.",
        "why_it_might_work": "Market participants may keep favoring strong assets.",
        "why_it_might_work_now": "The static sample can describe this idea.",
        "why_others_might_miss_it": "Simple screens may ignore context.",
        "baseline_to_beat": BaselineRequirement(
            description="Plain momentum",
            must_beat="Beat simple momentum after costs.",
        ),
        "evidence_needed": ["Historical test versus baseline"],
        "disproof_conditions": ["Does not beat the baseline"],
        "best_market_conditions": ["orderly markets"],
        "worst_market_conditions": ["broad stress"],
        "data_needed": ["daily bars"],
        "complexity_score": 3,
        "novelty_score": 2,
        "overfitting_risk_score": 4,
        "current_regime_fit": make_regime_fit(
            6,
            "Static sample suggests possible fit.",
            ["daily bars"],
            ["real regime data"],
        ),
        "status": EdgeHypothesisStatus.IDEA,
        "created_at": datetime(2026, 5, 28, tzinfo=UTC),
    }
    data.update(overrides)
    return StrategyDiscoveryRecord(**data)


def test_discovery_record_accepts_valid_sample() -> None:
    record = build_discovery_record()

    assert record.discovery_id == "sample-discovery"
    assert has_baseline_requirement(record)


@pytest.mark.parametrize("bad_id", ["", "Bad Id", "bad/id", "bad.id"])
def test_discovery_id_must_be_machine_friendly(bad_id: str) -> None:
    with pytest.raises(ValidationError, match="discovery_id"):
        build_discovery_record(discovery_id=bad_id)


def test_required_text_fields_are_validated() -> None:
    with pytest.raises(ValidationError):
        build_discovery_record(title="")


def test_score_ranges_are_validated() -> None:
    with pytest.raises(ValidationError):
        build_discovery_record(overfitting_risk_score=11)

    with pytest.raises(ValidationError):
        build_discovery_record(
            current_regime_fit=make_regime_fit(
                11,
                "Too high.",
                [],
                [],
            )
        )


def test_novel_hypotheses_require_baseline_to_beat() -> None:
    with pytest.raises(ValidationError):
        build_discovery_record(
            provenance=StrategyProvenance.NOVEL_HYPOTHESIS,
            baseline_to_beat=BaselineRequirement(description="", must_beat=""),
        )


def test_adaptive_canonical_records_require_adaptation_notes() -> None:
    with pytest.raises(ValidationError, match="adaptive_canonical"):
        build_discovery_record(provenance=StrategyProvenance.ADAPTIVE_CANONICAL)


def test_rejected_records_require_rejection_reasons() -> None:
    with pytest.raises(ValidationError, match="rejected records"):
        build_discovery_record(
            provenance=StrategyProvenance.REJECTED,
            status=EdgeHypothesisStatus.REJECTED,
        )
