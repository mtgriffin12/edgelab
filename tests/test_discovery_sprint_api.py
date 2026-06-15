from fastapi.testclient import TestClient

from edgelab.app.main import app

client = TestClient(app)


def test_discovery_sprint_api_surfaces_research_only_scoreboard() -> None:
    response = client.get("/intraday/discovery-sprint")

    assert response.status_code == 200
    data = response.json()
    assert data["strategy_count"] == 8
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
    by_slug = client.get("/intraday/research/strategy-ideas/failed-early-move")
    by_id = client.get("/intraday/research/strategy-ideas/failed_early_move")
    missing = client.get("/intraday/research/strategy-ideas/missing-idea")

    assert by_slug.status_code == 200
    assert by_id.status_code == 200
    assert missing.status_code == 404
    assert by_slug.json()["strategy_id"] == "failed_early_move"
    assert by_id.json()["url_slug"] == "failed-early-move"


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
    assert "real-money status: not allowed" in text
    assert "local historical research only" in text
    assert "ready for real money" not in text
    assert "validated edge" not in text
    assert "buy now" not in text
    assert "sell now" not in text
