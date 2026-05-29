from edgelab.discovery.genealogy import StrategyGenealogy
from edgelab.discovery.library import StrategyDiscoveryLibrary
from edgelab.discovery.schema import StrategyProvenance


def build_genealogy() -> StrategyGenealogy:
    return StrategyGenealogy(StrategyDiscoveryLibrary.with_samples().list_records())


def test_genealogy_identifies_root_ideas() -> None:
    genealogy = build_genealogy()

    roots = {record.discovery_id for record in genealogy.root_ideas()}

    assert "relative-strength-pullback" in roots
    assert "broad-fear-company-calm-pullback" not in roots


def test_genealogy_identifies_child_ideas() -> None:
    genealogy = build_genealogy()

    children = {
        record.discovery_id for record in genealogy.child_ideas("relative-strength-pullback")
    }

    assert "broad-fear-company-calm-pullback" in children
    assert "guidance-cut-mean-reversion-veto" in children


def test_genealogy_traces_lineage() -> None:
    genealogy = build_genealogy()

    lineage = genealogy.trace_lineage("broad-fear-company-calm-pullback")

    assert [node.discovery_id for node in lineage] == [
        "relative-strength-pullback",
        "broad-fear-company-calm-pullback",
    ]
    assert lineage[-1].provenance == StrategyProvenance.ADAPTIVE_CANONICAL


def test_genealogy_explains_difference_from_parent() -> None:
    genealogy = build_genealogy()

    explanation = genealogy.describe_difference_from_parent("broad-fear-company-calm-pullback")

    assert "mood separation" in explanation


def test_genealogy_handles_missing_records() -> None:
    genealogy = build_genealogy()

    details = genealogy.genealogy_for("missing-idea")

    assert details["found"] is False
    assert details["lineage"] == []
