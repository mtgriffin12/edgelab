from fastapi.testclient import TestClient

from edgelab.app.main import app

client = TestClient(app)


def test_variant_study_api_routes_return_research_only_payloads() -> None:
    response = client.get("/intraday/variant-study/spy/early-move-failed")

    assert response.status_code == 200
    payload = response.json()
    assert payload["research_only_status"] == "Research only"
    assert payload["real_money_status"] == "Not allowed"
    for key in [
        "bottom_line",
        "what_edgelab_tested",
        "what_looked_different",
        "which_version_deserves_more_testing",
        "why_this_might_be_misleading",
        "what_edgelab_should_test_next",
        "baseline_comparison",
        "variant_summaries",
        "quality_issues",
        "cache_metadata",
        "evidence_details",
    ]:
        assert key in payload
    text = response.text.lower()
    assert "buy now" not in text
    assert "sell now" not in text
    assert "short now" not in text
    assert "validated edge" not in text
    assert "ready for real money" not in text


def test_variant_study_card_route_returns_plain_sections() -> None:
    response = client.get("/intraday/variant-study/spy/early-move-failed/card")

    assert response.status_code == 200
    assert "## Bottom line" in response.text
    assert "## Evidence details" in response.text
    assert "Real-money status: Not allowed" in response.text
