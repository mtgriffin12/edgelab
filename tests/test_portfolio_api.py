from fastapi.testclient import TestClient

from edgelab.app.main import app

client = TestClient(app)


def test_api_reads_sample_portfolios() -> None:
    response = client.get("/portfolios/sample")

    assert response.status_code == 200
    data = response.json()
    assert data["portfolio_count"] == 4
    assert data["quality_issues"]


def test_api_reads_model_portfolios() -> None:
    response = client.get("/portfolios/model")

    assert response.status_code == 200
    portfolios = response.json()
    assert any(portfolio["portfolio_id"] == "core-research-portfolio" for portfolio in portfolios)


def test_api_reads_one_model_portfolio() -> None:
    response = client.get("/portfolios/model/core-research-portfolio")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "EdgeLab Core Research Portfolio"
    assert data["real_money_status"] == "Not allowed"


def test_api_missing_model_portfolio_returns_404() -> None:
    response = client.get("/portfolios/model/not-real")

    assert response.status_code == 404


def test_api_reads_model_portfolio_card_as_markdown() -> None:
    response = client.get("/portfolios/model/core-research-portfolio/card")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "## Bottom Line" in response.text


def test_api_reads_portfolio_styles() -> None:
    response = client.get("/portfolios/styles")

    assert response.status_code == 200
    assert "core_research" in response.json()["styles"]
    assert "benchmark_comparison" in response.json()["styles"]


def test_api_reads_portfolio_monitoring_notes() -> None:
    response = client.get("/portfolios/model/core-research-portfolio/monitoring")

    assert response.status_code == 200
    assert response.json()["monitoring_notes"]
