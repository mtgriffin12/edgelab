from edgelab.candidates.schema import CandidateScreeningRequest, CandidateStatus
from edgelab.candidates.screener import CandidateEquityScreener


def test_screener_returns_fixture_candidates() -> None:
    result = CandidateEquityScreener().screen()

    assert result.candidate_count == 3
    assert {candidate.symbol for candidate in result.candidates} == {"AAPL", "QQQ", "SPY"}


def test_screener_filters_requested_symbols() -> None:
    result = CandidateEquityScreener().screen(CandidateScreeningRequest(symbols=["spy"]))

    assert [candidate.symbol for candidate in result.candidates] == ["SPY"]


def test_screener_research_watchlist_returns_visible_candidates() -> None:
    watchlist = CandidateEquityScreener().research_watchlist()

    assert watchlist
    assert all(
        candidate.status
        in {
            CandidateStatus.RESEARCH_CANDIDATE,
            CandidateStatus.INTERESTING_BUT_INCOMPLETE,
            CandidateStatus.WATCHLIST_ONLY,
        }
        for candidate in watchlist
    )


def test_candidates_are_research_only() -> None:
    result = CandidateEquityScreener().screen()

    for candidate in result.candidates:
        assert candidate.real_money_status == "Not allowed"
        assert "buy now" not in candidate.plain_english_summary.lower()
        assert "ready for real money" not in candidate.plain_english_summary.lower()


def test_candidate_contains_market_and_sentiment_context() -> None:
    candidate = CandidateEquityScreener().get_candidate("spy-research-candidate")

    assert candidate is not None
    assert candidate.market_snapshot is not None
    assert candidate.sentiment_snapshot is not None
    assert candidate.matched_scorecard_ids
