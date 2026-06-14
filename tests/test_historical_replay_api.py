from fastapi.testclient import TestClient

from edgelab.app.main import app

client = TestClient(app)


def test_historical_replay_endpoint_returns_research_result() -> None:
    response = client.get("/intraday/replay/RPLAY/replay-breakout-complete")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["research_only_status"] == "Research only"
    assert data["real_money_status"] == "Not allowed"
    assert data["bottom_line"]
    assert data["setup_candidates"]
    assert data["hypothetical_trades"]


def test_historical_replay_card_endpoint_returns_markdown() -> None:
    response = client.get("/intraday/replay/RPLAY/replay-breakout-complete/card")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "## Bottom line" in response.text
    assert "## Real-money status" in response.text
    assert "Not allowed" in response.text


def test_historical_replay_sample_endpoint_returns_local_fixture() -> None:
    response = client.get("/intraday/replay/sample")

    assert response.status_code == 200
    data = response.json()
    assert data["research_only_status"] == "Research only"
    assert data["real_money_status"] == "Not allowed"
    assert data["quality_issues"] is not None
