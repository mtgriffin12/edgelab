from __future__ import annotations

from fastapi.testclient import TestClient

from edgelab.app.main import app

client = TestClient(app)


def test_idea_batch_list_api_returns_local_batches_without_ai_calls() -> None:
    response = client.get("/intraday/research/idea-batches")

    assert response.status_code == 200
    data = response.json()
    assert data["research_only_status"] == "Research only"
    assert data["real_money_status"] == "Not allowed"
    assert data["evidence_details"]["does_not_call_ai"] is True
    assert data["idea_batches"][0]["batch_id"] == "ai_intraday_ideas_001"
    assert "First Range Breakout Demo" in data["accepted_ideas"]
    assert "Moon Phase Demo" in data["rejected_ideas"]


def test_idea_batch_detail_api_is_validation_only() -> None:
    response = client.get("/intraday/research/idea-batches/ai_intraday_ideas_001")

    assert response.status_code == 200
    data = response.json()
    assert data["batch_id"] == "ai_intraday_ideas_001"
    assert data["ideas_submitted"] == 5
    assert data["accepted_ideas"] == [
        "First Range Breakout Demo",
        "Gap Fade Demo",
        "SPY QQQ Difference Demo",
    ]
    assert data["rejected_ideas"] == ["unsafe_claim_001", "Moon Phase Demo"]
    assert data["current_conclusion"] == "Not computed on the list page."
    assert data["real_money_status"] == "Not allowed"


def test_idea_batch_results_api_returns_scoreboard() -> None:
    response = client.get("/intraday/research/idea-batches/ai_intraday_ideas_001/results")

    assert response.status_code == 200
    data = response.json()
    assert data["ideas_submitted"] == 5
    assert data["ideas_tested"] == 3
    assert data["best_idea_if_any"]
    assert data["current_conclusion"]
    assert data["next_action"]
    assert data["securities_tested"] == [
        "AAPL",
        "AMZN",
        "DIA",
        "EEM",
        "META",
        "MSFT",
        "QQQ",
        "SPY",
        "TSLA",
        "VXX",
    ]
    assert {idea["idea_id"] for idea in data["rejected_ideas"]} == {
        "moon_phase_demo",
        "unsafe_claim_001",
    }
    vxx = {
        item["symbol"]: item for item in data["evidence_details"]["provider_data_quality_by_symbol"]
    }["VXX"]
    assert vxx["ready_sessions"] == 144
    assert vxx["quality_issues"] == 859
    assert data["research_only_status"] == "Research only"
    assert data["real_money_status"] == "Not allowed"


def test_idea_batch_card_api_is_concise_and_safe() -> None:
    response = client.get("/intraday/research/idea-batches/ai_intraday_ideas_001/card")

    assert response.status_code == 200
    text = response.text.lower()
    for phrase in [
        "headline",
        "ideas tested",
        "securities tested",
        "best idea if any",
        "ideas rejected",
        "ideas needing more examples",
        "ideas with mixed results / no clear answer",
        "next action",
        "real-money status",
        "no ai call was made",
    ]:
        assert phrase in text
    assert len(response.text) < 2500
    for forbidden in [
        "buy now",
        "sell now",
        "short now",
        "ready for real money",
        "validated edge",
        "ai found a strategy",
    ]:
        assert forbidden not in text


def test_missing_idea_batch_returns_404() -> None:
    response = client.get("/intraday/research/idea-batches/missing-batch/results")

    assert response.status_code == 404


def test_idea_batch_schema_endpoint_exposes_copyable_contract() -> None:
    response = client.get("/intraday/research/ai-idea-spec/schema")

    assert response.status_code == 200
    data = response.json()
    assert data["research_only_status"] == "Research only"
    assert data["real_money_status"] == "Not allowed"
    assert data["does_not_call_ai"] is True
    assert data["does_not_save_results"] is True
    assert data["required_top_level_fields"] == [
        "batch_id",
        "batch_name",
        "created_for",
        "ideas",
        "research_only_status",
        "real_money_status",
    ]
    assert "plain_english_name" in data["required_idea_fields"]
    assert "safety_notes" in data["required_idea_fields"]
    assert "gap_fade" in data["allowed_rule_families"]
    assert "reject_unsupported" in data["allowed_rule_families"]
    assert "buy/sell/short instructions" in data["forbidden_language_categories"]
    assert data["minimal_valid_example"]["real_money_status"] == "Not allowed"


def test_idea_batch_validate_api_accepts_valid_batch() -> None:
    response = client.post("/intraday/research/idea-batches/validate", json=_paste_batch())

    assert response.status_code == 200
    data = response.json()
    assert data["batch_id"] == "paste_batch_test"
    assert data["can_run"] is True
    assert data["accepted_ideas"][0]["plain_english_name"] == "Gap Fade Local Check"
    assert data["rejected_ideas"] == []
    assert data["unsupported_ideas"] == []
    assert data["does_not_call_ai"] is True
    assert data["does_not_save_results"] is True
    assert data["real_money_status"] == "Not allowed"


def test_idea_batch_validate_api_rejects_invalid_json() -> None:
    response = client.post(
        "/intraday/research/idea-batches/validate",
        content="{",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["errors"] == ["Invalid JSON: check for a missing comma or bracket."]


def test_idea_batch_validate_api_rejects_missing_top_level_field() -> None:
    payload = _paste_batch()
    payload.pop("batch_name")

    response = client.post("/intraday/research/idea-batches/validate", json=payload)

    assert response.status_code == 400
    assert "Missing required field: batch_name." in response.json()["errors"]


def test_idea_batch_validate_api_splits_unsupported_and_unsafe_ideas() -> None:
    payload = _paste_batch(
        ideas=[
            _paste_idea(),
            {
                **_paste_idea(),
                "idea_id": "moon_phase_test",
                "plain_english_name": "Moon Phase Test",
                "supported_rule_family": "moon_phase",
            },
            {
                **_paste_idea(),
                "idea_id": "unsafe_text_test",
                "plain_english_name": "unsafe_text_test",
                "hypothesis": "This claims profit.",
            },
            {
                key: value
                for key, value in _paste_idea("missing_name_test").items()
                if key != "plain_english_name"
            },
        ]
    )

    response = client.post("/intraday/research/idea-batches/validate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert [idea["plain_english_name"] for idea in data["accepted_ideas"]] == [
        "Gap Fade Local Check"
    ]
    assert {idea["idea_id"] for idea in data["unsupported_ideas"]} == {"moon_phase_test"}
    assert {idea["idea_id"] for idea in data["rejected_ideas"]} == {
        "missing_name_test",
        "unsafe_text_test",
    }
    assert any("Unsafe language found" in error for error in data["safety_errors"])
    assert any(
        "Missing required field: plain_english_name." in error for error in data["safety_errors"]
    )


def test_idea_batch_run_api_runs_supported_safe_ideas_only() -> None:
    payload = _paste_batch(
        ideas=[
            _paste_idea(),
            {
                **_paste_idea(),
                "idea_id": "unsupported_demo",
                "plain_english_name": "Unsupported Demo",
                "supported_rule_family": "reject_unsupported",
            },
            {
                **_paste_idea(),
                "idea_id": "unsafe_demo",
                "plain_english_name": "unsafe_demo",
                "hypothesis": "This says to buy the open.",
            },
        ]
    )

    response = client.post("/intraday/research/idea-batches/run", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["batch_name"] == "Paste Batch Test"
    assert data["ideas_submitted"] == 3
    assert data["ideas_tested"] == 1
    assert data["accepted_ideas"][0]["plain_english_name"] == "Gap Fade Local Check"
    assert {idea["idea_id"] for idea in data["unsupported_ideas"]} == {"unsupported_demo"}
    assert {idea["idea_id"] for idea in data["rejected_ideas"]} == {"unsafe_demo"}
    assert data["scoreboard"]
    assert data["does_not_call_ai"] is True
    assert data["does_not_save_results"] is True
    assert data["real_money_status"] == "Not allowed"


def _paste_batch(ideas: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "batch_id": "paste_batch_test",
        "batch_name": "Paste Batch Test",
        "created_for": "local research",
        "research_only_status": "Research only",
        "real_money_status": "Not allowed",
        "ideas": ideas or [_paste_idea()],
    }


def _paste_idea(idea_id: str = "gap_fade_local_check") -> dict[str, object]:
    return {
        "idea_id": idea_id,
        "plain_english_name": "Gap Fade Local Check",
        "hypothesis": "A local opening gap can be checked with a fixed local rule.",
        "supported_rule_family": "gap_fade",
        "instruments_to_test": ["SPY", "QQQ"],
        "required_data": "1-minute bars and first-hour range.",
        "exact_rule_definition": "Use the locked local gap fade rule without changing settings.",
        "fixed_parameters": {"minimum_gap_percent": 0.25},
        "why_test_this": "It is simple and local bars can check it.",
        "useful_result_definition": "Useful would mean enough examples repeat locally.",
        "failed_or_unclear_result_definition": "Unclear means examples split or are thin.",
        "expected_failure_modes": ["too few examples", "mixed results / no clear answer"],
        "safety_notes": "Research only. Local history check only.",
    }
