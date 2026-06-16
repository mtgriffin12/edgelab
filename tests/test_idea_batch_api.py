from __future__ import annotations

from fastapi.testclient import TestClient

from edgelab.app.main import app

client = TestClient(app)


def test_idea_batch_list_api_returns_local_batches_without_ai_calls() -> None:
    response = client.get("/intraday/research/idea-batches")

    assert response.status_code == 200
    data = response.json()
    assert data["research_only_status"] == "Research only"
    assert data["real_money_status"] == "Not allowed"
    assert data["evidence_details"]["does_not_call_ai"] is True
    assert data["idea_batches"][0]["batch_id"] == "ai_intraday_ideas_001"
    assert "First Range Breakout Demo" in data["accepted_ideas"]
    assert "Moon Phase Demo" in data["rejected_ideas"]


def test_idea_batch_detail_api_is_validation_only() -> None:
    response = client.get("/intraday/research/idea-batches/ai_intraday_ideas_001")

    assert response.status_code == 200
    data = response.json()
    assert data["batch_id"] == "ai_intraday_ideas_001"
    assert data["ideas_submitted"] == 5
    assert data["accepted_ideas"] == [
        "First Range Breakout Demo",
        "Gap Fade Demo",
        "SPY QQQ Difference Demo",
    ]
    assert data["rejected_ideas"] == ["unsafe_claim_001", "Moon Phase Demo"]
    assert data["current_conclusion"] == "Not computed on the list page."
    assert data["real_money_status"] == "Not allowed"


def test_idea_batch_results_api_returns_scoreboard() -> None:
    response = client.get("/intraday/research/idea-batches/ai_intraday_ideas_001/results")

    assert response.status_code == 200
    data = response.json()
    assert data["ideas_submitted"] == 5
    assert data["ideas_tested"] == 3
    assert data["best_idea_if_any"]
    assert data["current_conclusion"]
    assert data["next_action"]
    assert data["securities_tested"] == [
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
    assert {idea["idea_id"] for idea in data["rejected_ideas"]} == {
        "moon_phase_demo",
        "unsafe_claim_001",
    }
    vxx = {
        item["symbol"]: item for item in data["evidence_details"]["provider_data_quality_by_symbol"]
    }["VXX"]
    assert vxx["ready_sessions"] == 144
    assert vxx["quality_issues"] == 859
    assert data["research_only_status"] == "Research only"
    assert data["real_money_status"] == "Not allowed"


def test_idea_batch_card_api_is_concise_and_safe() -> None:
    response = client.get("/intraday/research/idea-batches/ai_intraday_ideas_001/card")

    assert response.status_code == 200
    text = response.text.lower()
    for phrase in [
        "headline",
        "ideas tested",
        "securities tested",
        "best idea if any",
        "ideas rejected",
        "ideas needing more examples",
        "ideas with mixed results / no clear answer",
        "next action",
        "real-money status",
        "no ai call was made",
    ]:
        assert phrase in text
    assert len(response.text) < 2500
    for forbidden in [
        "buy now",
        "sell now",
        "short now",
        "ready for real money",
        "validated edge",
        "ai found a strategy",
    ]:
        assert forbidden not in text


def test_missing_idea_batch_returns_404() -> None:
    response = client.get("/intraday/research/idea-batches/missing-batch/results")

    assert response.status_code == 404
