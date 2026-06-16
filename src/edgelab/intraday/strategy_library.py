"""Fixed local intraday strategy ideas for discovery sprints."""

from __future__ import annotations

from edgelab.intraday.discovery_sprint_schema import (
    StrategyIdeaDefinition,
    SupportedRuleFamily,
)

STRATEGY_LIBRARY_VERSION = "phase_7x_2k_v1"
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
            plain_english_summary=(
                "A failed early move is a morning where price pushes outside an early range but "
                "cannot stay there."
            ),
            plain_english_rule=(
                "The first strong move of the morning pushes beyond an early range, then comes "
                "back inside it."
            ),
            what_is_tested=(
                "EdgeLab checks mornings where price made an early push but could not hold it."
            ),
            example_definition=(
                "A morning counts when price moves outside the early range, then falls back "
                "inside it."
            ),
            useful_result_definition=(
                "Useful would mean the same kind of failed move is often followed by a similar "
                "next move."
            ),
            failed_or_unclear_definition=(
                "Unclear means the next move was split between helpful and unhelpful outcomes, "
                "so EdgeLab could not learn a clear rule."
            ),
            current_result_interpretation_template=(
                "Read the current result as EdgeLab checking whether failed early moves repeated "
                "clearly across local mornings."
            ),
            required_data=(
                "One-minute local first-hour bars across the discovered local universe."
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
            plain_english_summary=(
                "A gap fade is a morning where price opens away from a prior reference point and "
                "then comes back toward it."
            ),
            plain_english_rule=(
                "The market opens away from the prior reference level, then moves back toward it."
            ),
            what_is_tested=(
                "EdgeLab checks whether opening away from the prior reference point often leads "
                "to a move back toward that point."
            ),
            example_definition=(
                "A morning counts when the open is far enough from the prior reference point to "
                "test a move back toward it."
            ),
            useful_result_definition=(
                "Useful would mean those mornings often move back toward the reference point far "
                "enough to matter."
            ),
            failed_or_unclear_definition=(
                "Unclear means there were too few examples, or the move back was split with "
                "moves away from the reference point."
            ),
            current_result_interpretation_template=(
                "Read the current result as EdgeLab checking whether opening gaps often faded "
                "back toward the prior reference point."
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
            plain_english_summary=(
                "Gap continuation checks whether an opening move away from a prior reference "
                "point keeps going."
            ),
            plain_english_rule=(
                "The market opens away from the prior reference level and keeps moving away from "
                "it."
            ),
            what_is_tested=(
                "EdgeLab checks whether a morning that opens away from the prior reference point "
                "keeps moving in that same direction."
            ),
            example_definition=(
                "A morning counts when the open is far enough from the prior reference point to "
                "test follow-through away from it."
            ),
            useful_result_definition=(
                "Useful would mean those openings often keep moving away from the reference point "
                "far enough to matter."
            ),
            failed_or_unclear_definition=(
                "Unclear means there were too few examples, or many moves stalled or came back "
                "toward the reference point."
            ),
            current_result_interpretation_template=(
                "Read the current result as EdgeLab checking whether opening gaps often kept "
                "moving away from the prior reference point."
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
            plain_english_summary=(
                "This checks whether leaving the first 15 minutes of trading gives a useful clue "
                "about the next move."
            ),
            plain_english_rule=(
                "Price leaves the first 15-minute range and keeps moving in that direction."
            ),
            what_is_tested=(
                "EdgeLab checks whether a move beyond the first 15 minutes of trading tends to "
                "continue."
            ),
            example_definition=(
                "A morning counts when price breaks above or below the first 15-minute range."
            ),
            useful_result_definition=(
                "Useful would mean breaks in one direction often keep moving far enough to matter."
            ),
            failed_or_unclear_definition=(
                "Unclear means many breaks stalled, reversed, or did not move enough."
            ),
            current_result_interpretation_template=(
                "Read the current result as EdgeLab checking whether first 15-minute breaks "
                "usually followed through."
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
            plain_english_summary=(
                "This checks whether leaving the first 30 minutes of trading gives a useful clue "
                "about the next move."
            ),
            plain_english_rule=(
                "Price leaves the first 30-minute range and keeps moving in that direction."
            ),
            what_is_tested=(
                "EdgeLab checks whether a move beyond the first 30 minutes of trading tends to "
                "continue."
            ),
            example_definition=(
                "A morning counts when price breaks above or below the first 30-minute range."
            ),
            useful_result_definition=(
                "Useful would mean breaks in one direction often keep moving far enough to matter."
            ),
            failed_or_unclear_definition=(
                "Unclear means many breaks stalled, reversed, or did not move enough."
            ),
            current_result_interpretation_template=(
                "Read the current result as EdgeLab checking whether first 30-minute breaks "
                "usually followed through."
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
            plain_english_summary=(
                "Opening Range Reclaim checks whether price returning through an early level "
                "gives a useful clue."
            ),
            plain_english_rule=(
                "Price loses an early range level, then gets back through that level during the "
                "first hour."
            ),
            what_is_tested=(
                "EdgeLab checks whether price retaking an early level after losing it gives a "
                "useful clue."
            ),
            example_definition=(
                "A morning counts when price moves outside the early range, then returns through "
                "that range."
            ),
            useful_result_definition=(
                "Useful would mean reclaiming the level is often followed by a similar next move."
            ),
            failed_or_unclear_definition=(
                "Unclear means reclaiming the level did not consistently lead anywhere."
            ),
            current_result_interpretation_template=(
                "Read the current result as EdgeLab checking whether reclaiming an early level "
                "usually led to a useful next move."
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
            plain_english_summary=(
                "This checks mornings where the first part looks strong, but the next part does "
                "not confirm it."
            ),
            plain_english_rule=(
                "The first part of the morning is strong, but the next part does not follow "
                "through."
            ),
            what_is_tested=(
                "EdgeLab checks whether an early strong move often loses strength soon after."
            ),
            example_definition=(
                "A morning counts when the first part of trading moves clearly, then the next "
                "part does not continue that move."
            ),
            useful_result_definition=(
                "Useful would mean the weak follow-through is often followed by a similar next "
                "move."
            ),
            failed_or_unclear_definition=(
                "Unclear means the follow-through was split, too small, or not common enough."
            ),
            current_result_interpretation_template=(
                "Read the current result as EdgeLab checking whether early strength fading was a "
                "clear repeated clue."
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
            plain_english_summary=(
                "This checks mornings where SPY and QQQ do not move the same way early in the "
                "session."
            ),
            plain_english_rule=(
                "SPY and QQQ disagree during the first part of the morning, then EdgeLab checks "
                "whether that disagreement mattered later."
            ),
            what_is_tested=(
                "EdgeLab checks whether early disagreement between SPY and QQQ gives a useful "
                "clue about what happens next."
            ),
            example_definition=(
                "A morning counts when SPY and QQQ point in different directions during the "
                "early part of the session."
            ),
            useful_result_definition=(
                "Useful would mean those disagreements are often followed by a similar next move."
            ),
            failed_or_unclear_definition=(
                "Unclear means disagreements led to split outcomes or did not move enough."
            ),
            current_result_interpretation_template=(
                "Read the current result as EdgeLab checking whether SPY/QQQ disagreement was a "
                "clear repeated clue."
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
