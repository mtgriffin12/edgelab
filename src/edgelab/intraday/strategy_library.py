"""Fixed local intraday strategy ideas for discovery sprints."""

from __future__ import annotations

from edgelab.intraday.discovery_sprint_schema import (
    StrategyIdeaDefinition,
    SupportedRuleFamily,
)

STRATEGY_LIBRARY_VERSION = "phase_7x_2j_v1"
USEFUL_FIRST_RESULT = (
    "Enough local examples repeat across the available securities and still look worth "
    "checking later in the year."
)
UNCLEAR_OR_FAILED_RESULT = (
    "The examples are too few, mixed, blocked by local data, or only looked better at first."
)
RESULT_CLASSIFICATION_RULES = {
    "not_enough_examples": "Needs more examples before EdgeLab can judge it.",
    "no_clear_pattern": "Mixed results / no clear answer.",
    "worth_more_testing": "Worth testing on more history.",
    "reject_for_now": "Reject for now.",
}


def fixed_intraday_strategy_ideas() -> tuple[StrategyIdeaDefinition, ...]:
    """Return the fixed first local intraday strategy library."""

    return (
        StrategyIdeaDefinition(
            strategy_id=SupportedRuleFamily.FAILED_EARLY_MOVE,
            url_slug="failed-early-move",
            name="Failed Early Move",
            plain_english_rule=(
                "The first strong move of the morning pushes beyond an early range, then comes "
                "back inside it."
            ),
            required_data=(
                "One-minute local first-hour bars, plus SPY/QQQ pair context when present."
            ),
            useful_first_result=USEFUL_FIRST_RESULT,
            unclear_or_failed_result=UNCLEAR_OR_FAILED_RESULT,
            result_classification_rules=RESULT_CLASSIFICATION_RULES,
            evidence_details={"simple_rule_family": "early_move_failed"},
        ),
        StrategyIdeaDefinition(
            strategy_id=SupportedRuleFamily.GAP_FADE,
            url_slug="gap-fade",
            name="Gap Fade",
            plain_english_rule=(
                "The market opens away from the prior reference level, then moves back toward it."
            ),
            required_data="Local prior-reference level and one-minute first-hour bars.",
            useful_first_result=USEFUL_FIRST_RESULT,
            unclear_or_failed_result=UNCLEAR_OR_FAILED_RESULT,
            result_classification_rules=RESULT_CLASSIFICATION_RULES,
            evidence_details={"simple_rule_family": "gap_move"},
        ),
        StrategyIdeaDefinition(
            strategy_id=SupportedRuleFamily.GAP_CONTINUATION,
            url_slug="gap-continuation",
            name="Gap Continuation",
            plain_english_rule=(
                "The market opens away from the prior reference level and keeps moving away from "
                "it."
            ),
            required_data="Local prior-reference level and one-minute first-hour bars.",
            useful_first_result=USEFUL_FIRST_RESULT,
            unclear_or_failed_result=UNCLEAR_OR_FAILED_RESULT,
            result_classification_rules=RESULT_CLASSIFICATION_RULES,
            evidence_details={"simple_rule_family": "gap_move"},
        ),
        StrategyIdeaDefinition(
            strategy_id=SupportedRuleFamily.FIRST_15_MINUTE_BREAKOUT,
            url_slug="first-15-minute-breakout",
            name="First 15-Minute Breakout",
            plain_english_rule=(
                "Price leaves the first 15-minute range and keeps moving in that direction."
            ),
            required_data="At least 20 local first-hour minutes for each tested session.",
            useful_first_result=USEFUL_FIRST_RESULT,
            unclear_or_failed_result=UNCLEAR_OR_FAILED_RESULT,
            result_classification_rules=RESULT_CLASSIFICATION_RULES,
            evidence_details={"simple_rule_family": "early_range_break"},
        ),
        StrategyIdeaDefinition(
            strategy_id=SupportedRuleFamily.FIRST_30_MINUTE_BREAKOUT,
            url_slug="first-30-minute-breakout",
            name="First 30-Minute Breakout",
            plain_english_rule=(
                "Price leaves the first 30-minute range and keeps moving in that direction."
            ),
            required_data="At least 35 local first-hour minutes for each tested session.",
            useful_first_result=USEFUL_FIRST_RESULT,
            unclear_or_failed_result=UNCLEAR_OR_FAILED_RESULT,
            result_classification_rules=RESULT_CLASSIFICATION_RULES,
            evidence_details={"simple_rule_family": "early_range_break"},
        ),
        StrategyIdeaDefinition(
            strategy_id=SupportedRuleFamily.OPENING_RANGE_RECLAIM,
            url_slug="opening-range-reclaim",
            name="Opening Range Reclaim",
            plain_english_rule=(
                "Price loses an early range level, then gets back through that level during the "
                "first hour."
            ),
            required_data="One-minute local first-hour bars with enough bars after the reclaim.",
            useful_first_result=USEFUL_FIRST_RESULT,
            unclear_or_failed_result=UNCLEAR_OR_FAILED_RESULT,
            result_classification_rules=RESULT_CLASSIFICATION_RULES,
            evidence_details={"simple_rule_family": "range_reclaim"},
        ),
        StrategyIdeaDefinition(
            strategy_id=SupportedRuleFamily.STRONG_OPEN_WEAK_FOLLOW_THROUGH,
            url_slug="strong-open-weak-follow-through",
            name="Strong Open / Weak Follow-Through",
            plain_english_rule=(
                "The first part of the morning is strong, but the next part does not follow "
                "through."
            ),
            required_data="One-minute local first-hour bars with a clear first and second segment.",
            useful_first_result=USEFUL_FIRST_RESULT,
            unclear_or_failed_result=UNCLEAR_OR_FAILED_RESULT,
            result_classification_rules=RESULT_CLASSIFICATION_RULES,
            evidence_details={"simple_rule_family": "strong_open_fade"},
        ),
        StrategyIdeaDefinition(
            strategy_id=SupportedRuleFamily.SPY_QQQ_DIVERGENCE,
            url_slug="spy-qqq-divergence",
            name="SPY/QQQ Divergence",
            plain_english_rule=(
                "SPY and QQQ disagree during the first part of the morning, then EdgeLab checks "
                "whether that disagreement mattered later."
            ),
            required_data="Same-date local one-minute first-hour bars for SPY and QQQ.",
            useful_first_result=USEFUL_FIRST_RESULT,
            unclear_or_failed_result=UNCLEAR_OR_FAILED_RESULT,
            result_classification_rules=RESULT_CLASSIFICATION_RULES,
            evidence_details={"simple_rule_family": "paired_symbol_difference"},
        ),
    )


def strategy_by_id_or_slug(value: str) -> StrategyIdeaDefinition | None:
    """Return a strategy idea by internal ID or URL slug."""

    normalized = value.strip().lower().replace("_", "-")
    for idea in fixed_intraday_strategy_ideas():
        if idea.url_slug == normalized or idea.strategy_id.value.replace("_", "-") == normalized:
            return idea
    return None
