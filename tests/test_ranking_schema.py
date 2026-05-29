import pytest
from pydantic import ValidationError

from edgelab.ranking.schema import (
    EvidenceStrength,
    MetricScore,
    RankingConclusion,
    RankingDimension,
    StrategyScorecard,
)


def build_scorecard(**overrides: object) -> StrategyScorecard:
    data: dict[str, object] = {
        "scorecard_id": "scorecard-sample",
        "title": "Sample Scorecard",
        "evidence_strength": EvidenceStrength.WEAK,
        "conclusion": RankingConclusion.NEEDS_MORE_TESTING,
        "overall_score": 50.0,
        "dimension_scores": [
            MetricScore(
                dimension=RankingDimension.RETURN_QUALITY,
                score=50,
                plain_english_reason="Sample reason.",
            )
        ],
        "plain_english_summary": "Sample evidence is thin.",
        "why_it_ranked_this_way": ["Risk and evidence quality matter."],
        "caution": "Research-only sample.",
    }
    data.update(overrides)
    return StrategyScorecard(**data)


def test_metric_score_requires_score_bounds() -> None:
    with pytest.raises(ValidationError):
        MetricScore(
            dimension=RankingDimension.RETURN_QUALITY,
            score=101,
            plain_english_reason="Too high.",
        )


def test_scorecard_requires_overall_score_bounds() -> None:
    with pytest.raises(ValidationError):
        build_scorecard(overall_score=-1)


def test_insufficient_evidence_cannot_be_promising() -> None:
    with pytest.raises(ValidationError, match="insufficient evidence"):
        build_scorecard(
            evidence_strength=EvidenceStrength.INSUFFICIENT,
            conclusion=RankingConclusion.PROMISING_RESEARCH_CANDIDATE,
        )


def test_scorecard_cannot_allow_real_money() -> None:
    with pytest.raises(ValidationError, match="real-money use"):
        build_scorecard(real_money_status="Allowed")


def test_scorecard_rejects_action_instruction_phrases() -> None:
    with pytest.raises(ValidationError, match="action instructions"):
        build_scorecard(plain_english_summary="buy now")
