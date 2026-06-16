from fastapi.testclient import TestClient

from edgelab.app.main import app

client = TestClient(app)


def test_discovery_sprint_api_surfaces_research_only_scoreboard() -> None:
    response = client.get("/intraday/discovery-sprint")

    assert response.status_code == 200
    data = response.json()
    assert data["strategy_count"] == 8
    assert data["strategy_ideas_tested"] == [
        "Failed Early Move",
        "Gap Fade",
        "Gap Continuation",
        "First 15-Minute Breakout",
        "First 30-Minute Breakout",
        "Opening Range Reclaim",
        "Strong Open / Weak Follow-Through",
        "SPY/QQQ Divergence",
    ]
    assert "symbols_tested" in data
    assert "best_candidate_if_any" in data
    assert "current_conclusion" in data
    assert "data_quality_by_symbol" in data["evidence_details"]
    assert data["research_only_status"] == "Research only"
    assert data["real_money_status"] == "Not allowed"
    assert (
        sum(
            instrument["usable_sessions"]
            for strategy in data["strategy_results"]
            for instrument in strategy["instrument_results"]
        )
        > 0
    )
    assert (
        sum(
            instrument["completed_examples"]
            for strategy in data["strategy_results"]
            for instrument in strategy["instrument_results"]
        )
        > 0
    )
    assert {item["strategy_id"] for item in data["strategy_results"]} == {
        "failed_early_move",
        "gap_fade",
        "gap_continuation",
        "first_15_minute_breakout",
        "first_30_minute_breakout",
        "opening_range_reclaim",
        "strong_open_weak_follow_through",
        "spy_qqq_divergence",
    }


def test_strategy_idea_api_supports_slug_and_id_lookup() -> None:
    scoreboard = client.get("/intraday/research/strategy-ideas")
    by_slug = client.get("/intraday/research/strategy-ideas/failed-early-move")
    by_id = client.get("/intraday/research/strategy-ideas/failed_early_move")
    missing = client.get("/intraday/research/strategy-ideas/missing-idea")

    assert scoreboard.status_code == 200
    scoreboard_data = scoreboard.json()
    assert scoreboard_data["symbols_tested"] == [
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
    assert scoreboard_data["strategy_ideas_tested"]
    assert scoreboard_data["best_candidate_if_any"]
    assert scoreboard_data["current_conclusion"]
    assert scoreboard_data["next_action"]
    assert scoreboard_data["evidence_details"]["data_quality_by_symbol"]
    assert by_slug.status_code == 200
    assert by_id.status_code == 200
    assert missing.status_code == 404
    assert by_slug.json()["strategy_id"] == "failed_early_move"
    assert by_id.json()["url_slug"] == "failed-early-move"
    assert by_slug.json()["symbols_tested"]
    assert by_slug.json()["best_candidate_if_any"]
    assert by_slug.json()["next_action"]


def test_pair_specific_strategy_stays_spy_qqq_only() -> None:
    response = client.get("/intraday/research/strategy-ideas/spy-qqq-divergence")

    assert response.status_code == 200
    data = response.json()
    assert data["symbols_tested"] == ["QQQ", "SPY"]
    assert data["securities_tested"] == "QQQ, SPY"


def test_ai_idea_schema_endpoint_does_not_call_ai_or_advance_ideas() -> None:
    response = client.get("/intraday/research/ai-idea-spec/schema")

    assert response.status_code == 200
    data = response.json()
    assert data["research_only_status"] == "Research only"
    assert data["real_money_status"] == "Not allowed"
    assert data["example"]["supported_rule_family"] == "gap_fade"
    text = response.text.lower()
    assert "does not call ai" in text
    assert "ready for real money" not in text
    assert "validated edge" not in text


def test_discovery_sprint_markdown_card_stays_research_only() -> None:
    response = client.get("/intraday/discovery-sprint/card")

    assert response.status_code == 200
    text = response.text.lower()
    for phrase in [
        "headline",
        "securities tested",
        "strategies tested",
        "main result",
        "best candidates",
        "ideas to reject for now",
        "ideas needing more examples",
        "next research action",
    ]:
        assert phrase in text
    assert "aapl, amzn, dia, eem, meta, msft, qqq, spy, tsla, vxx" in text
    assert "gap fade, gap continuation" in text
    assert "spy/qqq divergence" in text
    assert len(response.text) < 2500
    assert "real-money status: not allowed" in text
    assert "local historical research only" in text
    assert "ready for real money" not in text
    assert "validated edge" not in text
    assert "buy now" not in text
    assert "sell now" not in text
