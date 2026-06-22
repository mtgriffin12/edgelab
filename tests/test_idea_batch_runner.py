from __future__ import annotations

from edgelab.intraday.idea_batch_runner import IdeaBatchRunner
from edgelab.intraday.idea_batch_schema import IdeaBatchResultLabel


def test_idea_batch_runner_loads_fixture_and_separates_unsupported_ideas() -> None:
    runner = IdeaBatchRunner()

    result = runner.run_batch("ai_intraday_ideas_001")
    cached = runner.run_batch("ai_intraday_ideas_001")

    assert result.batch_id == "ai_intraday_ideas_001"
    assert result.ideas_submitted == 5
    assert result.ideas_tested == 4
    assert len(result.accepted_ideas) == 4
    assert {idea.idea_id for idea in result.accepted_ideas} >= {"user_wording_claim_001"}
    assert {idea.idea_id for idea in result.rejected_ideas} == {"moon_phase_demo"}
    assert {idea.classification for idea in result.rejected_ideas} == {
        IdeaBatchResultLabel.UNSUPPORTED_RULE
    }
    assert result.ranked_results
    assert result.real_money_status == "Not allowed"
    assert result.research_only_status == "Research only"
    assert result.cache_metadata["cache_status"] in {"computed", "cached"}
    assert cached.cache_metadata["cache_status"] == "cached"


def test_idea_batch_runner_preserves_expanded_universe_and_vxx_quality() -> None:
    result = IdeaBatchRunner().run_batch("ai_intraday_ideas_001")

    assert result.securities_tested == [
        "AAPL",
        "AMZN",
        "DIA",
        "EEM",
        "META",
        "MSFT",
        "QQQ",
        "SPY",
        "TSLA",
        "VXX",
    ]
    quality = {
        item["symbol"]: item for item in result.evidence_details["provider_data_quality_by_symbol"]
    }
    assert quality["VXX"]["sessions"] == 251
    assert quality["VXX"]["ready_sessions"] == 144
    assert quality["VXX"]["quality_issues"] == 859


def test_idea_batch_runner_does_not_save_results_to_research_db() -> None:
    result = IdeaBatchRunner().run_batch("ai_intraday_ideas_001")

    assert result.cache_metadata["cache_status"] in {"computed", "cached"}
    assert "research_runs" not in str(result.evidence_details).lower()
