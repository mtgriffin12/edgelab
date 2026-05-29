from edgelab.ranking.ranker import StrategyRankingEngine
from edgelab.ranking.schema import RankingConclusion


def test_ranking_engine_returns_sorted_scorecards() -> None:
    result = StrategyRankingEngine().rank()
    scores = [scorecard.overall_score for scorecard in result.scorecards]

    assert result.scorecards
    assert scores == sorted(scores, reverse=True)


def test_ranking_engine_identifies_top_research_candidates() -> None:
    result = StrategyRankingEngine().rank()

    assert result.top_research_candidates
    assert all(
        scorecard.conclusion
        in {
            RankingConclusion.PROMISING_RESEARCH_CANDIDATE,
            RankingConclusion.BEATS_BASELINE_IN_SAMPLE,
            RankingConclusion.NEEDS_MORE_TESTING,
        }
        for scorecard in result.top_research_candidates
    )


def test_ranking_engine_identifies_weak_candidates() -> None:
    result = StrategyRankingEngine().rank()

    assert result.weak_candidates
    assert any(
        scorecard.conclusion == RankingConclusion.UNSUPPORTED
        for scorecard in result.weak_candidates
    )


def test_ranking_engine_can_filter_by_conclusion() -> None:
    engine = StrategyRankingEngine()
    result = engine.rank()

    unsupported = engine.filter_by_conclusion(
        RankingConclusion.UNSUPPORTED,
        result.scorecards,
    )

    assert unsupported
    assert all(card.conclusion == RankingConclusion.UNSUPPORTED for card in unsupported)
