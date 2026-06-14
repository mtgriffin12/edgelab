from fastapi.testclient import TestClient

from edgelab.app.main import app

client = TestClient(app)


def test_multi_session_summary_endpoint_returns_research_only_result() -> None:
    response = client.get("/intraday/multi-session-summary")

    assert response.status_code == 200
    data = response.json()
    assert data["research_only_status"] == "Research only"
    assert data["real_money_status"] == "Not allowed"
    assert "Not enough examples yet" in data["bottom_line"]
    assert data["quality_issues"] is not None
    assert data["evidence_details"]


def test_multi_session_summary_card_endpoint_returns_markdown() -> None:
    response = client.get("/intraday/multi-session-summary/card")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "## Bottom line" in response.text
    assert "## Evidence details" in response.text
    assert "Not allowed" in response.text


def test_pattern_results_endpoints_return_summary_shape() -> None:
    for path in ["/intraday/pattern-results", "/intraday/pattern-results/RPLAY"]:
        response = client.get(path)

        assert response.status_code == 200
        data = response.json()
        assert data["research_only_status"] == "Research only"
        assert data["real_money_status"] == "Not allowed"
        assert "setup_type_summaries" in data
        assert "bottom_line" in data


def test_no_trade_analysis_endpoints_return_summary_shape() -> None:
    for path in ["/intraday/no-trade-analysis", "/intraday/no-trade-analysis/RPLAY"]:
        response = client.get(path)

        assert response.status_code == 200
        data = response.json()
        assert data["research_only_status"] == "Research only"
        assert data["real_money_status"] == "Not allowed"
        assert "no_trade_reason_summaries" in data
        assert "bottom_line" in data
