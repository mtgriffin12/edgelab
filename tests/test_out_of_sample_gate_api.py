from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

import edgelab.app.main as main
from edgelab.intraday.out_of_sample_gate_schema import (
    OutOfSampleGateConclusion,
    OutOfSampleGatePeriod,
    OutOfSampleGateResult,
    OutOfSampleSplitStrategy,
    OutOfSampleVariantComparison,
    OutOfSampleVariantResult,
    conclusion_translation,
)

client = TestClient(main.app)


def test_out_of_sample_gate_api_routes_return_research_only_payloads(monkeypatch) -> None:
    monkeypatch.setattr(main, "out_of_sample_gate_service", _FakeOutOfSampleGateService())

    response = client.get("/intraday/out-of-sample/spy/early-move-failed")
    detail = client.get("/intraday/out-of-sample/spy/early-move-failed/failed_push_from_above")

    assert response.status_code == 200
    assert detail.status_code == 200
    payload = response.json()
    assert payload["research_only_status"] == "Research only"
    assert payload["real_money_status"] == "Not allowed"
    for key in [
        "bottom_line",
        "what_edgelab_checked",
        "what_changed_on_later_data",
        "what_this_means",
        "what_edgelab_should_test_next",
        "why_this_might_be_misleading",
        "proof_limitations",
        "variant_comparisons",
        "cache_metadata",
        "evidence_details",
    ]:
        assert key in payload
    assert detail.json()["variant"]["variant_id"] == "failed_push_from_above"
    text = response.text.lower()
    assert "holdout-style check" in text
    assert "buy now" not in text
    assert "sell now" not in text
    assert "short now" not in text
    assert "validated edge" not in text
    assert "ready for real money" not in text


def test_out_of_sample_gate_card_route_returns_plain_sections(monkeypatch) -> None:
    monkeypatch.setattr(main, "out_of_sample_gate_service", _FakeOutOfSampleGateService())

    response = client.get("/intraday/out-of-sample/spy/early-move-failed/card")

    assert response.status_code == 200
    assert "## Bottom line" in response.text
    assert "## What EdgeLab checked" in response.text
    assert "## Evidence details" in response.text
    assert "Real-money status: Not allowed" in response.text


class _FakeOutOfSampleGateService:
    def run(self, request=None) -> OutOfSampleGateResult:
        return _sample_gate_result()


def _sample_gate_result() -> OutOfSampleGateResult:
    comparison = OutOfSampleVariantComparison(
        variant_id="failed_push_from_above",
        plain_english_label="Failed push from above",
        discovery_result=_sample_variant_result("Discovery looked interesting but unproven."),
        holdout_result=_sample_variant_result("Later examples were mixed."),
        comparison_result="The later period became mixed, so EdgeLab did not get a clear answer.",
        gate_conclusion=OutOfSampleGateConclusion.BECAME_UNCLEAR,
        gate_conclusion_translation=conclusion_translation(
            OutOfSampleGateConclusion.BECAME_UNCLEAR
        ),
    )
    return OutOfSampleGateResult(
        gate_id="spy-early-move-failed-out-of-sample",
        instrument="SPY",
        paired_instrument="QQQ",
        pattern_family="opening_range_failure",
        variant_ids=["failed_push_from_above"],
        split_strategy=OutOfSampleSplitStrategy.CALENDAR_QUARTER_HOLDOUT,
        discovery_period=OutOfSampleGatePeriod(
            label="Discovery period",
            start_date=date(2022, 9, 30),
            end_date=date(2022, 12, 30),
            session_count=63,
            plain_english_summary="Earlier local examples.",
        ),
        holdout_period=OutOfSampleGatePeriod(
            label="Holdout period",
            start_date=date(2023, 1, 3),
            end_date=date(2023, 9, 29),
            session_count=188,
            plain_english_summary="Later local examples.",
        ),
        discovery_result="Discovery period: failed push from above looked more interesting.",
        holdout_result="Holdout period: later examples were mixed.",
        comparison_result="EdgeLab compared the fixed version across time.",
        gate_conclusion=OutOfSampleGateConclusion.BECAME_UNCLEAR,
        gate_conclusion_translation=conclusion_translation(
            OutOfSampleGateConclusion.BECAME_UNCLEAR
        ),
        bottom_line="The SPY failed early move variant became mixed on the later period.",
        what_edgelab_checked="EdgeLab ran a holdout-style check on fixed local rules.",
        what_changed_on_later_data="The later examples did not give a clear answer.",
        what_this_means="This is useful for deciding what to study next.",
        what_edgelab_should_test_next="Keep the rules fixed and test more local history.",
        why_this_might_be_misleading="This is not proof.",
        proof_limitations=(
            "This is a holdout-style check using the current local file. It is not proof."
        ),
        variant_comparisons=[comparison],
        cache_metadata={"cache_status": "fresh"},
    )


def _sample_variant_result(text: str) -> OutOfSampleVariantResult:
    return OutOfSampleVariantResult(
        variant_id="failed_push_from_above",
        plain_english_label="Failed push from above",
        examples_found=12,
        examples_completed=12,
        moved_as_expected_count=7,
        moved_against_test_count=4,
        did_not_move_enough_count=1,
        average_pretend_result=0.4,
        cost_changed_result_count=0,
        plain_english_result=text,
    )
