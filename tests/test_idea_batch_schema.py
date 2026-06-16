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
    )

    assert batch.research_only_status == "Research only"
    assert batch.real_money_status == "Not allowed"
    assert batch.ideas[0]["idea_id"] == "gap_fade_demo"


def test_supported_idea_schema_normalizes_symbols() -> None:
    idea = AIProposedIntradayIdea(**_valid_idea())

    assert idea.supported_rule_family == IdeaBatchRuleFamily.GAP_FADE
    assert idea.instruments_to_test == ("SPY", "QQQ")


def test_unsupported_rule_is_rejected_by_schema() -> None:
    with pytest.raises(ValidationError):
        AIProposedIntradayIdea(
            **{
                **_valid_idea(),
                "supported_rule_family": "visual_chart_pattern",
            }
        )


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "This says to buy the open.",
        "This is a trade recommendation.",
        "This claims profit.",
        "This claims proof.",
        "This is guaranteed.",
        "This is reliable.",
        "This is a validated edge.",
        "This is for live trading.",
        "This has paper-mode readiness.",
        "This has real-money readiness.",
        "Tune after seeing results.",
        "This idea already works.",
    ],
)
def test_unsafe_idea_language_is_rejected(unsafe_text: str) -> None:
    with pytest.raises((ValidationError, ValueError)):
        AIProposedIntradayIdea(
            **{
                **_valid_idea(),
                "hypothesis": unsafe_text,
            }
        )


def _valid_idea() -> dict[str, object]:
    return {
        "idea_id": "gap_fade_demo",
        "plain_english_name": "Gap Fade Demo",
        "hypothesis": "A local gap can be checked with a fixed local rule.",
        "supported_rule_family": "gap_fade",
        "instruments_to_test": ("spy", "QQQ", "SPY"),
        "required_data": "Local one-minute first-hour bars.",
        "exact_rule_definition": "Use fixed settings before checking local outcomes.",
        "fixed_parameters": {"minimum_gap_percent": 0.25},
        "why_test_this": "It is simple and local bars can check it.",
        "useful_result_definition": "Useful would mean enough examples repeat locally.",
        "failed_or_unclear_result_definition": "Unclear means examples split or are thin.",
        "expected_failure_modes": ("Needs more examples", "Mixed results / no clear answer"),
        "safety_notes": "This is a locked local hypothesis only.",
    }
