from fastapi.testclient import TestClient

from edgelab.app.main import app

client = TestClient(app)


def test_historical_provider_capabilities_endpoint() -> None:
    response = client.get("/intraday/history/provider-capabilities")

    assert response.status_code == 200
    data = response.json()
    assert data["real_money_status"] == "Not allowed"
    local_provider = data["providers"][0]
    assert local_provider["supports_external_calls"] is False
    assert local_provider["requires_credentials"] is False


def test_historical_sessions_endpoint_lists_local_sessions() -> None:
    response = client.get("/intraday/history/sessions")

    assert response.status_code == 200
    data = response.json()
    session_ids = {session["session_id"] for session in data["sessions"]}
    assert "spy-2024-01-02-historical" in session_ids
    assert data["research_only_status"] == "Research only"
    assert data["real_money_status"] == "Not allowed"


def test_historical_symbol_sessions_endpoint() -> None:
    response = client.get("/intraday/history/SPY/sessions")

    assert response.status_code == 200
    data = response.json()
    assert data["sessions"][0]["symbol"] == "SPY"
    assert data["sessions"][0]["readiness"] == "ready_for_replay"


def test_historical_session_detail_endpoint() -> None:
    response = client.get("/intraday/history/SPY/sessions/spy-2024-01-02-historical")

    assert response.status_code == 200
    data = response.json()
    assert data["sessions"][0]["session_id"] == "spy-2024-01-02-historical"
    assert data["bars_loaded"] == 5
    assert "bars" not in data


def test_historical_session_bars_endpoint() -> None:
    response = client.get("/intraday/history/SPY/sessions/spy-2024-01-02-historical/bars")

    assert response.status_code == 200
    data = response.json()
    assert len(data["bars"]) == 5
    assert data["bars"][0]["symbol"] == "SPY"
    assert data["bars"][0]["timestamp_utc"].endswith("Z")
    assert data["bars"][0]["raw_timestamp"] == "2024-01-02T09:30:00"
    assert data["real_money_status"] == "Not allowed"


def test_historical_missing_session_returns_404() -> None:
    response = client.get("/intraday/history/SPY/sessions/missing-session")

    assert response.status_code == 404
