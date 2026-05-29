from fastapi.testclient import TestClient

from edgelab.app.main import app

client = TestClient(app)


def test_api_reads_sample_candidates() -> None:
    response = client.get("/candidates/sample")

    assert response.status_code == 200
    data = response.json()
    assert data["candidate_count"] == 3
    assert data["quality_issues"]


def test_api_reads_equity_candidates() -> None:
    response = client.get("/candidates/equities")

    assert response.status_code == 200
    candidates = response.json()
    assert any(candidate["candidate_id"] == "spy-research-candidate" for candidate in candidates)


def test_api_reads_one_equity_candidate() -> None:
    response = client.get("/candidates/equities/spy-research-candidate")

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "SPY"
    assert data["real_money_status"] == "Not allowed"


def test_api_missing_candidate_returns_404() -> None:
    response = client.get("/candidates/equities/not-real")

    assert response.status_code == 404


def test_api_reads_candidate_card_as_markdown() -> None:
    response = client.get("/candidates/equities/spy-research-candidate/card")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "## Bottom Line" in response.text


def test_api_reads_candidate_symbols() -> None:
    response = client.get("/candidates/symbols")

    assert response.status_code == 200
    assert response.json()["symbols"] == ["AAPL", "QQQ", "SPY"]


def test_api_reads_research_watchlist() -> None:
    response = client.get("/candidates/research-watchlist")

    assert response.status_code == 200
    assert response.json()
