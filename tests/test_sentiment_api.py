from fastapi.testclient import TestClient

from edgelab.app.main import app


def test_sentiment_symbols_endpoint_returns_fixture_symbols() -> None:
    client = TestClient(app)

    response = client.get("/sentiment/symbols")

    assert response.status_code == 200
    assert response.json() == {"symbols": ["AAPL", "QQQ", "SPY"]}


def test_sentiment_events_endpoint_returns_events() -> None:
    client = TestClient(app)

    response = client.get("/sentiment/SPY/events")

    assert response.status_code == 200
    assert response.json()["symbol"] == "SPY"
    assert len(response.json()["events"]) == 3


def test_sentiment_summary_endpoint_returns_summary() -> None:
    client = TestClient(app)

    response = client.get("/sentiment/QQQ/summary")

    assert response.status_code == 200
    assert response.json()["symbol"] == "QQQ"
    assert response.json()["event_count"] == 3


def test_sentiment_snapshot_endpoint_returns_snapshot() -> None:
    client = TestClient(app)

    response = client.get("/sentiment/AAPL/snapshot")

    assert response.status_code == 200
    assert response.json()["symbol"] == "AAPL"
    assert "trade_bias_context" in response.json()


def test_sentiment_quality_endpoint_returns_quality_issues() -> None:
    client = TestClient(app)

    response = client.get("/sentiment/AAPL/quality")

    assert response.status_code == 200
    assert response.json() == {"symbol": "AAPL", "quality_issues": []}


def test_sentiment_unknown_symbol_returns_404() -> None:
    client = TestClient(app)

    response = client.get("/sentiment/MISSING/events")

    assert response.status_code == 404
