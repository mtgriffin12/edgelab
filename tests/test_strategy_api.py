from fastapi.testclient import TestClient

from edgelab.app.main import app


def test_get_strategies_returns_data() -> None:
    client = TestClient(app)

    response = client.get("/strategies")

    assert response.status_code == 200
    assert len(response.json()) == 5


def test_get_strategy_returns_valid_strategy() -> None:
    client = TestClient(app)

    response = client.get("/strategies/relative-strength-pullback")

    assert response.status_code == 200
    assert response.json()["strategy_id"] == "relative-strength-pullback"
    assert response.json()["eligible_for_live_trading"] is False


def test_get_strategy_card_returns_markdown_text() -> None:
    client = TestClient(app)

    response = client.get("/strategies/relative-strength-pullback/card")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "## Current Conclusion" in response.text


def test_get_strategy_returns_404_for_unknown_strategy() -> None:
    client = TestClient(app)

    response = client.get("/strategies/not-real")

    assert response.status_code == 404
