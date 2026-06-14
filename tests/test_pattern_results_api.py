from fastapi.testclient import TestClient

from edgelab.app import main
from edgelab.intraday.comparative_study_schema import (
    ComparativeStudyClassification,
    ComparativeStudyRequest,
    ComparativeStudyResult,
    SetupFamilyComparison,
    SymbolComparisonSummary,
)
from edgelab.intraday.schema import IntradaySetupType
from edgelab.research_runs.schema import ResearchRunFreshnessStatus

client = TestClient(main.app)


def test_multi_session_summary_endpoint_returns_research_only_result() -> None:
    response = client.get("/intraday/multi-session-summary")

    assert response.status_code == 200
    data = response.json()
    assert data["research_only_status"] == "Research only"
    assert data["real_money_status"] == "Not allowed"
    assert "Not enough examples yet" in data["bottom_line"]
    assert data["quality_issues"] is not None
    assert data["evidence_details"]


def test_multi_session_summary_card_endpoint_returns_markdown() -> None:
    response = client.get("/intraday/multi-session-summary/card")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "## Bottom line" in response.text
    assert "## Evidence details" in response.text
    assert "Not allowed" in response.text


def test_pattern_results_endpoints_return_summary_shape() -> None:
    for path in ["/intraday/pattern-results", "/intraday/pattern-results/RPLAY"]:
        response = client.get(path)

        assert response.status_code == 200
        data = response.json()
        assert data["research_only_status"] == "Research only"
        assert data["real_money_status"] == "Not allowed"
        assert "setup_type_summaries" in data
        assert "bottom_line" in data


def test_no_trade_analysis_endpoints_return_summary_shape() -> None:
    for path in ["/intraday/no-trade-analysis", "/intraday/no-trade-analysis/RPLAY"]:
        response = client.get(path)

        assert response.status_code == 200
        data = response.json()
        assert data["research_only_status"] == "Research only"
        assert data["real_money_status"] == "Not allowed"
        assert "no_trade_reason_summaries" in data
        assert "bottom_line" in data


def test_comparative_study_api_and_card_routes(monkeypatch) -> None:
    monkeypatch.setattr(main, "comparative_study_service", _FakeComparativeStudyService())

    for path in [
        "/intraday/comparative-study/spy-qqq",
        "/intraday/comparative-study/spy-qqq/opening-range-failure",
    ]:
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["research_only_status"] == "Research only"
        assert data["real_money_status"] == "Not allowed"
        assert data["classification"] == "spy_more_interesting"
        assert "recommendation" not in data["bottom_line"].lower()

    card = client.get("/intraday/comparative-study/spy-qqq/card")
    assert card.status_code == 200
    assert card.headers["content-type"].startswith("text/plain")
    assert "## Bottom line" in card.text
    assert "## What EdgeLab compared" in card.text
    assert "## Evidence details" in card.text
    assert "Not allowed" in card.text


class _FakeComparativeStudyService:
    def compare(self, request: ComparativeStudyRequest | None = None) -> ComparativeStudyResult:
        request = request or ComparativeStudyRequest()
        symbol_summaries = [
            SymbolComparisonSummary(
                symbol="SPY",
                saved_run_freshness=ResearchRunFreshnessStatus.FRESH,
                saved_run_message="This saved result still matches the local source file.",
                comparison_available=True,
                sessions_tested=251,
                usable_sessions=251,
                possible_setup_count=62,
                sit_out_count=81,
                completed_pretend_result_count=62,
                helpful_afterward_count=32,
                wrong_way_afterward_count=30,
                flat_afterward_count=0,
                incomplete_pretend_result_count=0,
                setup_classification="interesting_but_unproven",
                plain_english_summary="SPY had enough local examples to review.",
            ),
            SymbolComparisonSummary(
                symbol="QQQ",
                saved_run_freshness=ResearchRunFreshnessStatus.FRESH,
                saved_run_message="This saved result still matches the local source file.",
                comparison_available=True,
                sessions_tested=251,
                usable_sessions=251,
                possible_setup_count=82,
                sit_out_count=26,
                completed_pretend_result_count=82,
                helpful_afterward_count=40,
                wrong_way_afterward_count=42,
                flat_afterward_count=0,
                incomplete_pretend_result_count=0,
                setup_classification="weak_or_inconsistent",
                plain_english_summary="QQQ had enough local examples to review.",
            ),
        ]
        comparison = SetupFamilyComparison(
            setup_family=IntradaySetupType.OPENING_RANGE_FAILURE,
            classification=ComparativeStudyClassification.SPY_MORE_INTERESTING,
            symbol_summaries=symbol_summaries,
            bottom_line="SPY looked more interesting in this local historical sample.",
            what_edgelab_compared="EdgeLab compared failed early moves in SPY and QQQ.",
            what_looked_different="SPY and QQQ did not show the same research label.",
            why_that_might_matter="The difference can guide the next local research test.",
            why_this_might_be_misleading="This is one local historical sample with simple rules.",
            what_edgelab_should_test_next="Compare opening gap size and first-hour range width.",
        )
        return ComparativeStudyResult(
            study_id="spy-qqq-opening-range-failure",
            request=request,
            comparison_available=True,
            classification=ComparativeStudyClassification.SPY_MORE_INTERESTING,
            setup_family_comparison=comparison,
            bottom_line=comparison.bottom_line,
            what_edgelab_compared=comparison.what_edgelab_compared,
            what_looked_different=comparison.what_looked_different,
            why_that_might_matter=comparison.why_that_might_matter,
            why_this_might_be_misleading=comparison.why_this_might_be_misleading,
            what_edgelab_should_test_next=comparison.what_edgelab_should_test_next,
        )
