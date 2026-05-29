from fastapi.testclient import TestClient

from edgelab.app.main import app

client = TestClient(app)


def test_api_reads_sample_ranking_result() -> None:
    response = client.get("/rankings/sample")

    assert response.status_code == 200
    data = response.json()
    assert data["scorecards"]
    assert data["quality_issues"]


def test_api_reads_scorecards() -> None:
    response = client.get("/rankings/scorecards")

    assert response.status_code == 200
    scorecards = response.json()
    assert any(card["scorecard_id"] == "strategy-relative-strength-pullback" for card in scorecards)


def test_api_reads_one_scorecard() -> None:
    response = client.get("/rankings/scorecards/strategy-relative-strength-pullback")

    assert response.status_code == 200
    assert response.json()["title"] == "Relative Strength Pullback"


def test_api_missing_scorecard_returns_404() -> None:
    response = client.get("/rankings/scorecards/not-real")

    assert response.status_code == 404


def test_api_reads_scorecard_card_as_markdown() -> None:
    response = client.get("/rankings/scorecards/strategy-relative-strength-pullback/card")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "## Bottom Line" in response.text


def test_api_reads_top_research_candidates() -> None:
    response = client.get("/rankings/top-research-candidates")

    assert response.status_code == 200
    assert response.json()


def test_api_reads_weak_candidates() -> None:
    response = client.get("/rankings/weak-candidates")

    assert response.status_code == 200
    assert response.json()
