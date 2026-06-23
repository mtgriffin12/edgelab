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
        "User Wording Claim Demo",
    ]
    assert data["rejected_ideas"] == ["Moon Phase Demo"]
    assert data["current_conclusion"] == "Not computed on the list page."
    assert data["real_money_status"] == "Not allowed"


def test_idea_batch_results_api_returns_scoreboard() -> None:
    response = client.get("/intraday/research/idea-batches/ai_intraday_ideas_001/results")

    assert response.status_code == 200
    data = response.json()
    assert data["ideas_submitted"] == 5
    assert data["ideas_tested"] == 4
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
    assert {idea["idea_id"] for idea in data["rejected_ideas"]} == {"moon_phase_demo"}
    vxx = {
        item["symbol"]: item for item in data["evidence_details"]["provider_data_quality_by_symbol"]
    }["VXX"]
    assert vxx["ready_sessions"] == 144
    assert vxx["quality_issues"] == 859
    assert data["research_only_status"] == "Research only"
    assert data["real_money_status"] == "Not allowed"
    assert data["evidence_details"]["ideas_advanced_count"] == 0
    assert data["evidence_details"]["closest_to_interesting_idea"]
    assert data["evidence_details"]["recommended_next_research_focus"]
    first_result = data["ranked_results"][0]
    assert first_result["outcome_label"]
    assert first_result["symbols_tested"] == first_result["securities_tested"]
    assert first_result["example_count_total"] >= 0
    assert first_result["example_count_by_symbol"]
    assert first_result["symbol_result_summary"]
    assert first_result["symbol_result_summary"][0]["matched_examples"] >= 0
    assert first_result["symbol_result_summary"][0]["simple_result_label"] in {
        "Helpful",
        "Unhelpful",
        "Mixed results / no clear answer",
        "Too few examples",
        "Data problem",
    }
    assert first_result["closest_to_interesting_reason"]
    assert first_result["why_label_was_assigned"]
    assert first_result["what_to_try_next"]
    assert first_result["result_confidence_explanation"]


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
        "closest to interesting idea",
        "why it was closest",
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
    assert "forbidden_language_categories" not in data
    assert "safety_errors" not in data
    assert data["field_types"]["instruments_to_test"] == "non-empty array of strings"
    assert data["field_types"]["required_data"] == "array of strings"
    assert data["field_types"]["expected_failure_modes"] == "non-empty array of strings"
    assert data["field_types"]["fixed_parameters"] == "object with JSON-compatible values"
    assert data["minimal_valid_example"]["real_money_status"] == "Not allowed"
    assert isinstance(data["minimal_valid_example"]["ideas"][0]["required_data"], list)
    assert isinstance(data["minimal_valid_example"]["ideas"][0]["fixed_parameters"], dict)


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


def test_idea_batch_validate_api_accepts_realistic_safe_research_language() -> None:
    response = client.post(
        "/intraday/research/idea-batches/validate",
        json=_paste_batch(ideas=_realistic_safe_ai_ideas()),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["can_run"] is True
    assert data["ideas_submitted"] == 10
    assert len(data["accepted_ideas"]) == 10
    assert data["rejected_ideas"] == []
    assert data["unsupported_ideas"] == []
    assert data["validation_errors"] == []
    assert {idea["plain_english_name"] for idea in data["accepted_ideas"]} == {
        "Tech Leaders Confirm Breakout",
        "TSLA Leads, QQQ Confirms",
        "AAPL and MSFT Confirm QQQ Reclaim",
        "VXX Opposes Equity Breakout",
        "Narrow Open Expansion",
        "Wide Open Reversal",
        "Big Early Move Failure",
        "Early Drop Reclaim",
        "Early Spike Fade",
        "Index ETF Leads Single Stocks",
    }
    assert data["does_not_call_ai"] is True
    assert data["does_not_save_results"] is True
    assert data["real_money_status"] == "Not allowed"


def test_idea_batch_validate_api_accepts_user_style_10_idea_json_shape() -> None:
    response = client.post(
        "/intraday/research/idea-batches/validate",
        json=_paste_batch(ideas=_user_style_10_idea_batch()),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["can_run"] is True
    assert data["ideas_submitted"] == 10
    assert len(data["accepted_ideas"]) == 10
    assert data["rejected_ideas"] == []
    assert data["unsupported_ideas"] == []
    assert data["validation_errors"] == []
    assert "safety_errors" not in data


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


def test_idea_batch_validate_api_splits_unsupported_and_structural_errors() -> None:
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
                "idea_id": "wording_text_test",
                "plain_english_name": "wording_text_test",
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
        "Gap Fade Local Check",
        "wording_text_test",
    ]
    assert {idea["idea_id"] for idea in data["unsupported_ideas"]} == {"moon_phase_test"}
    assert {idea["idea_id"] for idea in data["rejected_ideas"]} == {"missing_name_test"}
    unsupported = data["unsupported_ideas"][0]
    assert unsupported["accepted_for_testing"] is False
    assert unsupported["example_count_total"] == 0
    assert unsupported["closest_to_interesting_reason"].startswith("Not tested")
    assert "local rule logic" in unsupported["closest_to_interesting_reason"]
    assert "supported rule families" in unsupported["what_to_try_next"]
    rejected = data["rejected_ideas"][0]
    assert rejected["why_label_was_assigned"].startswith("Not tested")
    assert any(
        "missing_name_test: missing required field: plain_english_name." in error
        for error in data["validation_errors"]
    )


def test_idea_batch_validate_api_returns_field_level_structural_errors() -> None:
    payload = _paste_batch(
        ideas=[
            {
                **_paste_idea("bad_required_data"),
                "required_data": "Local bars should be an array.",
            },
            {
                **_paste_idea("bad_fixed_parameters"),
                "fixed_parameters": "range_minutes=15",
            },
            {
                **_paste_idea("bad_expected_failure_modes"),
                "expected_failure_modes": "needs more examples",
            },
            {
                **_paste_idea("bad_instruments"),
                "instruments_to_test": "SPY",
            },
        ]
    )

    response = client.post("/intraday/research/idea-batches/validate", json=payload)

    assert response.status_code == 200
    errors = response.json()["validation_errors"]
    assert any(
        "bad_required_data: required_data must be a list of strings." in error for error in errors
    )
    assert any(
        "bad_fixed_parameters: fixed_parameters must be an object." in error for error in errors
    )
    assert any(
        "bad_expected_failure_modes: expected_failure_modes must be a list of strings." in error
        for error in errors
    )
    assert any(
        "bad_instruments: instruments_to_test must be a list of strings." in error
        for error in errors
    )


def test_idea_batch_validate_api_accepts_trading_instruction_wording() -> None:
    payload = _paste_batch(
        ideas=[
            {
                **_paste_idea(),
                "idea_id": "unsafe_instruction_test",
                "plain_english_name": "unsafe_instruction_test",
                "hypothesis": "Buy now because this works.",
            }
        ]
    )

    response = client.post("/intraday/research/idea-batches/validate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert [idea["idea_id"] for idea in data["accepted_ideas"]] == ["unsafe_instruction_test"]
    assert data["rejected_ideas"] == []
    assert data["validation_errors"] == []


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
                "idea_id": "wording_demo",
                "plain_english_name": "wording_demo",
                "hypothesis": "This says to buy the open.",
            },
        ]
    )

    response = client.post("/intraday/research/idea-batches/run", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["batch_name"] == "Paste Batch Test"
    assert data["ideas_submitted"] == 3
    assert data["ideas_tested"] == 2
    assert [idea["plain_english_name"] for idea in data["accepted_ideas"]] == [
        "Gap Fade Local Check",
        "wording_demo",
    ]
    assert {idea["idea_id"] for idea in data["unsupported_ideas"]} == {"unsupported_demo"}
    assert data["rejected_ideas"] == []
    assert data["scoreboard"]
    unsupported = data["unsupported_ideas"][0]
    assert unsupported["closest_to_interesting_reason"].startswith("Not tested")
    assert "supported rule families" in unsupported["what_to_try_next"]
    scoreboard_row = data["scoreboard"][0]
    assert scoreboard_row["outcome_label"]
    assert scoreboard_row["symbols_tested"] == scoreboard_row["securities_tested"]
    assert scoreboard_row["example_count_total"] >= 0
    assert scoreboard_row["example_count_by_symbol"]
    assert scoreboard_row["symbol_result_summary"]
    assert scoreboard_row["why_label_was_assigned"]
    assert scoreboard_row["what_to_try_next"]
    assert scoreboard_row["result_confidence_explanation"]
    assert data["does_not_call_ai"] is True
    assert data["does_not_save_results"] is True
    assert data["real_money_status"] == "Not allowed"


def test_idea_batch_run_api_runs_user_style_supported_ideas() -> None:
    response = client.post(
        "/intraday/research/idea-batches/run",
        json=_paste_batch(ideas=_user_style_10_idea_batch()),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ideas_submitted"] == 10
    assert data["ideas_tested"] == 10
    assert len(data["accepted_ideas"]) == 10
    assert data["rejected_ideas"] == []
    assert data["unsupported_ideas"] == []
    assert data["batch_summary"]["ideas_submitted"] == 10
    assert data["batch_summary"]["ideas_tested"] == 10
    assert data["batch_summary"]["ideas_advanced"] == 0
    assert data["batch_summary"]["closest_to_interesting_idea"]
    assert data["batch_summary"]["recommended_next_research_focus"]
    assert data["evidence_details"]["batch_plain_english_summary"].startswith("Nothing advanced.")
    assert len(data["scoreboard"]) == 10
    assert all(row["example_count_total"] >= 0 for row in data["scoreboard"])
    assert all(row["example_count_by_symbol"] for row in data["scoreboard"])
    assert all(row["symbol_result_summary"] for row in data["scoreboard"])
    assert all(row["why_label_was_assigned"] for row in data["scoreboard"])
    assert all(row["what_to_try_next"] for row in data["scoreboard"])
    assert all(row["result_confidence_explanation"] for row in data["scoreboard"])
    assert "safety_errors" not in data
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
        "required_data": ["1-minute bars", "first-hour range"],
        "exact_rule_definition": "Use the locked local gap fade rule without changing settings.",
        "fixed_parameters": {"minimum_gap_percent": 0.25},
        "why_test_this": "It is simple and local bars can check it.",
        "useful_result_definition": "Useful would mean enough examples repeat locally.",
        "failed_or_unclear_result_definition": "Unclear means examples split or are thin.",
        "expected_failure_modes": ["too few examples", "mixed results / no clear answer"],
        "safety_notes": "Research only. Local history check only.",
    }


def _realistic_safe_ai_ideas() -> list[dict[str, object]]:
    base: dict[str, object] = {
        "required_data": ["Local 1-minute bars", "first-hour price range"],
        "fixed_parameters": {"range_minutes": 15, "test_horizon_minutes": 10},
        "useful_result_definition": (
            "Useful would mean enough completed examples moved in the tested direction "
            "more often than they moved against it."
        ),
        "failed_or_unclear_result_definition": (
            "Unclear would mean too few examples or mixed results / no clear answer."
        ),
        "expected_failure_modes": [
            "needs more examples",
            "mixed results / no clear answer",
            "local data problem",
        ],
        "safety_notes": "Research only. Local history check only. No recommendation.",
    }
    ideas = [
        (
            "tech_leaders_confirm_breakout",
            "Tech Leaders Confirm Breakout",
            "Test whether a short-term early range move may continue when large tech names agree.",
            "first_range_breakout",
            ["AAPL", "MSFT", "META", "AMZN", "QQQ"],
            (
                "Find mornings where the first range breaks higher and several tech names "
                "move higher too."
            ),
            "This checks whether grouped movement matters more than one symbol alone.",
        ),
        (
            "tsla_leads_qqq_confirms",
            "TSLA Leads, QQQ Confirms",
            "Test whether TSLA moving first and QQQ following is different from isolated movement.",
            "trend_continuation",
            ["TSLA", "QQQ"],
            "Find mornings where TSLA moves higher early and QQQ confirms the same direction.",
            "This checks whether one high-attention name lines up with the broader basket.",
        ),
        (
            "aapl_msft_confirm_qqq_reclaim",
            "AAPL and MSFT Confirm QQQ Reclaim",
            "Test whether QQQ recovery is clearer when AAPL and MSFT recover too.",
            "reclaim",
            ["AAPL", "MSFT", "QQQ"],
            "Find mornings where QQQ returns inside the early range after weakness.",
            "This checks whether a recovery has broader support from large components.",
        ),
        (
            "vxx_opposes_equity_breakout",
            "VXX Opposes Equity Breakout",
            "Test whether VXX moving lower matters when equity symbols move higher.",
            "first_range_breakout",
            ["VXX", "SPY", "QQQ"],
            "Find mornings where SPY or QQQ move higher while VXX moves lower.",
            "This checks whether a risk-off reference disagrees with an equity move.",
        ),
        (
            "narrow_open_expansion",
            "Narrow Open Expansion",
            "Test whether a quiet first range later expands enough to matter.",
            "first_range_breakout",
            ["AAPL", "AMZN", "META", "MSFT", "QQQ", "SPY"],
            "Find mornings with a narrow first range and a later move outside that range.",
            "This checks whether quiet opens create enough examples for local testing.",
        ),
        (
            "wide_open_reversal",
            "Wide Open Reversal",
            "Test whether a wide first range is followed by a failed move.",
            "first_range_failure",
            ["AAPL", "AMZN", "META", "MSFT", "QQQ", "SPY"],
            "Find mornings with a wide first range and a later failed early move.",
            "This checks whether large early movement becomes less useful afterward.",
        ),
        (
            "big_early_move_failure",
            "Big Early Move Failure",
            "Test whether a strong early move fails after moving too far too fast.",
            "first_range_failure",
            ["AAPL", "AMZN", "META", "MSFT", "QQQ", "SPY", "TSLA"],
            "Find mornings where price makes a strong early move and then gives it back.",
            "This checks failed early move behavior across the local universe.",
        ),
        (
            "early_drop_reclaim",
            "Early Drop Reclaim",
            "Test whether price sells off early and then recovers into the first range.",
            "reclaim",
            ["AAPL", "AMZN", "META", "MSFT", "QQQ", "SPY", "TSLA"],
            "Find mornings where price moves lower early and later returns inside the first range.",
            "This checks whether early weakness sometimes reverses in local history.",
        ),
        (
            "early_spike_fade",
            "Early Spike Fade",
            "Test whether an early spike fades after the first range is formed.",
            "gap_fade",
            ["AAPL", "AMZN", "META", "MSFT", "QQQ", "SPY", "TSLA"],
            "Find mornings where the opening move fades after the early range.",
            "This checks whether early excitement often cools off in the local sample.",
        ),
        (
            "index_etf_leads_single_stocks",
            "Index ETF Leads Single Stocks",
            "Test whether SPY or QQQ moving first lines up with single-stock follow-through.",
            "symbol_divergence",
            ["SPY", "QQQ", "AAPL", "MSFT", "META", "AMZN"],
            "Find mornings where index ETFs and single stocks disagree early.",
            "This checks whether disagreement is useful enough to keep studying.",
        ),
    ]
    return [
        {
            **base,
            "idea_id": idea_id,
            "plain_english_name": name,
            "hypothesis": hypothesis,
            "supported_rule_family": rule_family,
            "instruments_to_test": instruments,
            "exact_rule_definition": exact_rule_definition,
            "why_test_this": why_test_this,
        }
        for (
            idea_id,
            name,
            hypothesis,
            rule_family,
            instruments,
            exact_rule_definition,
            why_test_this,
        ) in ideas
    ]


def _user_style_10_idea_batch() -> list[dict[str, object]]:
    phrases = [
        "Buy now because this works.",
        "sell now",
        "short this",
        "guaranteed profit",
        "validated edge",
        "paper ready",
        "live ready",
        "ready for real money",
        "go long",
        "place order",
    ]
    rule_families = [
        "first_range_breakout",
        "first_range_failure",
        "gap_fade",
        "gap_continuation",
        "reclaim",
        "trend_continuation",
        "symbol_divergence",
        "first_range_breakout",
        "gap_fade",
        "gap_continuation",
    ]
    return [
        {
            **_paste_idea(f"user_style_idea_{index:02d}"),
            "plain_english_name": f"User Style Idea {index:02d}",
            "hypothesis": f"Local research idea with user wording: {phrase}",
            "supported_rule_family": rule_family,
            "instruments_to_test": (
                ["SPY", "QQQ"] if rule_family == "symbol_divergence" else ["SPY"]
            ),
            "required_data": ["Local one-minute bars", "First-hour range"],
            "fixed_parameters": {
                "range_minutes": 15,
                "minimum_confirming_symbols": 3,
                "test_horizon_minutes": 10,
                "range_width_bucket": "narrow",
                "allow_retest": True,
                "optional_note": None,
            },
        }
        for index, (phrase, rule_family) in enumerate(
            zip(phrases, rule_families, strict=True),
            start=1,
        )
    ]
