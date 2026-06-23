from __future__ import annotations

import pytest
from pydantic import ValidationError

from edgelab.intraday.idea_batch_schema import (
    AIProposedIntradayIdea,
    IdeaBatch,
    IdeaBatchRuleFamily,
)


def test_idea_batch_accepts_raw_ideas_for_individual_validation() -> None:
    batch = IdeaBatch(
        batch_id="demo_batch",
        batch_name="Demo Batch",
        created_for="Local research test",
        ideas=[_valid_idea()],
        research_only_status="Research only",
        real_money_status="Not allowed",
    )

    assert batch.research_only_status == "Research only"
    assert batch.real_money_status == "Not allowed"
    assert batch.ideas[0]["idea_id"] == "gap_fade_demo"


def test_supported_idea_schema_normalizes_symbols() -> None:
    idea = AIProposedIntradayIdea(**_valid_idea())

    assert idea.supported_rule_family == IdeaBatchRuleFamily.GAP_FADE
    assert idea.instruments_to_test == ["SPY", "QQQ"]
    assert idea.required_data == ["Local one-minute first-hour bars."]
    assert idea.expected_failure_modes == ["Needs more examples", "Mixed results / no clear answer"]


def test_supported_idea_schema_accepts_user_style_json_shape() -> None:
    idea = AIProposedIntradayIdea(
        **{
            **_valid_idea(),
            "required_data": ["Local one-minute bars", "First-hour range"],
            "fixed_parameters": {
                "range_minutes": 15,
                "minimum_confirming_symbols": 3,
                "test_horizon_minutes": 10,
                "range_width_bucket": "narrow",
                "allow_retest": True,
                "optional_note": None,
                "buckets": ["narrow", 2, 3.5, False, None],
            },
        }
    )

    assert idea.required_data == ["Local one-minute bars", "First-hour range"]
    assert idea.fixed_parameters["range_minutes"] == 15
    assert idea.fixed_parameters["range_width_bucket"] == "narrow"


def test_unsupported_rule_is_rejected_by_schema() -> None:
    with pytest.raises(ValidationError):
        AIProposedIntradayIdea(
            **{
                **_valid_idea(),
                "supported_rule_family": "visual_chart_pattern",
            }
        )


def test_batch_requires_research_status_fields() -> None:
    with pytest.raises(ValidationError):
        IdeaBatch(
            batch_id="demo_batch",
            batch_name="Demo Batch",
            created_for="Local research test",
            ideas=[_valid_idea()],
        )


@pytest.mark.parametrize(
    "idea_text",
    [
        "Check whether a short time after the open changes the local result.",
        "Check whether a short-term failed move is different from a slow one.",
        "Test mornings where price sells off early and then recovers.",
        "A selloff after the first range can be checked with locked local rules.",
        "The test watches whether price moves lower or moves higher after the setup.",
        "A failed move may continue or reverse; this only checks local history.",
        "Mixed results / no clear answer should keep the idea in research.",
        "Buy now.",
        "Sell now.",
        "Short this.",
        "Go long.",
        "Go short.",
        "Place an order.",
        "Trade this.",
        "This is guaranteed profit.",
        "This is a validated edge.",
        "This is paper ready.",
        "This is live ready.",
        "This is ready for real money.",
        "This works.",
        "This cannot fail.",
    ],
)
def test_idea_text_is_not_rejected_for_wording(idea_text: str) -> None:
    idea = AIProposedIntradayIdea(
        **{
            **_valid_idea(),
            "hypothesis": idea_text,
        }
    )

    assert idea.hypothesis == idea_text


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("instruments_to_test", "SPY"),
        ("required_data", "Local one-minute bars"),
        ("expected_failure_modes", "needs more examples"),
        ("fixed_parameters", "range_minutes=15"),
    ],
)
def test_user_style_json_shape_rejects_wrong_field_types(
    field: str,
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError):
        AIProposedIntradayIdea(
            **{
                **_valid_idea(),
                field: bad_value,
            }
        )


def test_supported_idea_schema_rejects_empty_instruments() -> None:
    with pytest.raises(ValidationError):
        AIProposedIntradayIdea(
            **{
                **_valid_idea(),
                "instruments_to_test": [],
            }
        )


def _valid_idea() -> dict[str, object]:
    return {
        "idea_id": "gap_fade_demo",
        "plain_english_name": "Gap Fade Demo",
        "hypothesis": "A local gap can be checked with a fixed local rule.",
        "supported_rule_family": "gap_fade",
        "instruments_to_test": ["spy", "QQQ", "SPY"],
        "required_data": ["Local one-minute first-hour bars."],
        "exact_rule_definition": "Use fixed settings before checking local outcomes.",
        "fixed_parameters": {"minimum_gap_percent": 0.25},
        "why_test_this": "It is simple and local bars can check it.",
        "useful_result_definition": "Useful would mean enough examples repeat locally.",
        "failed_or_unclear_result_definition": "Unclear means examples split or are thin.",
        "expected_failure_modes": ["Needs more examples", "Mixed results / no clear answer"],
        "safety_notes": "This is a locked local hypothesis only.",
    }
