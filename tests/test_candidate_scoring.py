from edgelab.candidates.schema import CandidateEvidenceStrength, CandidateStatus
from edgelab.candidates.scoring import (
    evidence_strength_for_score,
    score_candidate,
    status_for_candidate,
)


def test_candidate_score_bounds() -> None:
    score = score_candidate(
        highest_ranking_score=400,
        support_count=10,
        market_quality_issue_count=0,
        sentiment_quality_issue_count=0,
        risk_flag_count=0,
        sentiment_event_count=3,
    )

    assert 0 <= score <= 100


def test_candidate_score_penalizes_quality_issues() -> None:
    clean = score_candidate(
        highest_ranking_score=70,
        support_count=3,
        market_quality_issue_count=0,
        sentiment_quality_issue_count=0,
        risk_flag_count=1,
        sentiment_event_count=3,
    )
    flawed = score_candidate(
        highest_ranking_score=70,
        support_count=3,
        market_quality_issue_count=2,
        sentiment_quality_issue_count=2,
        risk_flag_count=1,
        sentiment_event_count=3,
    )

    assert flawed < clean


def test_candidate_score_penalizes_risk_flags() -> None:
    light_risk = score_candidate(
        highest_ranking_score=70,
        support_count=3,
        market_quality_issue_count=0,
        sentiment_quality_issue_count=0,
        risk_flag_count=1,
        sentiment_event_count=3,
    )
    heavy_risk = score_candidate(
        highest_ranking_score=70,
        support_count=3,
        market_quality_issue_count=0,
        sentiment_quality_issue_count=0,
        risk_flag_count=6,
        sentiment_event_count=3,
    )

    assert heavy_risk < light_risk


def test_unsupported_logic_forces_insufficient_strength() -> None:
    strength = evidence_strength_for_score(
        80,
        support_count=4,
        quality_issue_count=0,
        has_unsupported_logic=True,
    )

    assert strength == CandidateEvidenceStrength.INSUFFICIENT


def test_status_stays_conservative() -> None:
    status = status_for_candidate(
        72,
        CandidateEvidenceStrength.MODERATE,
        quality_issue_count=0,
        has_blocking_risk=False,
    )

    assert status == CandidateStatus.RESEARCH_CANDIDATE
