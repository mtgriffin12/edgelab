from fastapi.testclient import TestClient

from edgelab.app.main import app


def test_market_data_symbols_endpoint_returns_fixture_symbols() -> None:
    client = TestClient(app)

    response = client.get("/market-data/symbols")

    assert response.status_code == 200
    assert response.json() == {"symbols": ["AAPL", "QQQ", "SPY"]}


def test_market_data_bars_endpoint_returns_bars() -> None:
    client = TestClient(app)

    response = client.get("/market-data/SPY/bars")

    assert response.status_code == 200
    assert response.json()["symbol"] == "SPY"
    assert len(response.json()["bars"]) == 5


def test_market_data_summary_endpoint_returns_summary() -> None:
    client = TestClient(app)

    response = client.get("/market-data/QQQ/summary")

    assert response.status_code == 200
    assert response.json()["symbol"] == "QQQ"
    assert response.json()["row_count"] == 5
    assert response.json()["quality_issue_count"] == 0


def test_market_data_quality_endpoint_returns_quality_issues() -> None:
    client = TestClient(app)

    response = client.get("/market-data/AAPL/quality")

    assert response.status_code == 200
    assert response.json() == {"symbol": "AAPL", "quality_issues": []}
