import pytest

from edgelab.discovery.library import StrategyDiscoveryLibrary
from edgelab.discovery.schema import (
    DiscoveryLane,
    EdgeBehaviorType,
    EdgeHypothesisStatus,
    StrategyProvenance,
    has_baseline_requirement,
)


def test_sample_discovery_library_loads_known_and_innovation_records() -> None:
    library = StrategyDiscoveryLibrary.with_samples()
    records = library.list_records()

    assert len(records) == 9
    assert library.get("relative-strength-pullback") is not None
    assert library.get("social-euphoria-without-price-confirmation") is not None


def test_discovery_library_rejects_duplicate_ids() -> None:
    library = StrategyDiscoveryLibrary.with_samples()
    record = library.get("relative-strength-pullback")
    assert record is not None

    with pytest.raises(ValueError, match="Duplicate discovery_id"):
        library.add(record)


def test_filter_by_lane() -> None:
    library = StrategyDiscoveryLibrary.with_samples()

    known = library.filter_by_lane(DiscoveryLane.KNOWN_STRATEGY_LIBRARY)
    innovation = library.filter_by_lane(DiscoveryLane.EDGE_INNOVATION_LAB)

    assert len(known) == 4
    assert len(innovation) == 5


def test_filter_by_provenance() -> None:
    library = StrategyDiscoveryLibrary.with_samples()

    novel = library.filter_by_provenance(StrategyProvenance.NOVEL_HYPOTHESIS)

    assert {record.discovery_id for record in novel} == {
        "good-news-weak-price-warning",
        "social-euphoria-without-price-confirmation",
    }


def test_filter_by_behavior_type() -> None:
    library = StrategyDiscoveryLibrary.with_samples()

    records = library.filter_by_behavior_type(EdgeBehaviorType.SENTIMENT_DISAGREEMENT)

    assert "broad-fear-company-calm-pullback" in {record.discovery_id for record in records}


def test_filter_by_status() -> None:
    library = StrategyDiscoveryLibrary.with_samples()

    records = library.filter_by_status(EdgeHypothesisStatus.BASELINE_REQUIRED)

    assert records
    assert all(record.status == EdgeHypothesisStatus.BASELINE_REQUIRED for record in records)


def test_filter_by_current_regime_fit_minimum_score() -> None:
    library = StrategyDiscoveryLibrary.with_samples()

    records = library.filter_by_min_regime_fit(6)

    assert {record.discovery_id for record in records} == {
        "relative-strength-pullback",
        "etf-risk-on-risk-off-rotation",
        "breakout-with-volume-confirmation",
    }


def test_adaptive_and_novel_records_have_baseline_requirements() -> None:
    library = StrategyDiscoveryLibrary.with_samples()

    records = [
        record
        for record in library.list_records()
        if record.provenance
        in {
            StrategyProvenance.ADAPTIVE_CANONICAL,
            StrategyProvenance.NOVEL_HYPOTHESIS,
        }
    ]

    assert records
    assert all(has_baseline_requirement(record) for record in records)


def test_export_all_returns_dictionaries() -> None:
    library = StrategyDiscoveryLibrary.with_samples()

    exported = library.export_all()

    assert isinstance(exported[0], dict)
    assert "discovery_id" in exported[0]
