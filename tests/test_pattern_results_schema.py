import pytest

from edgelab.intraday.pattern_results import (
    classify_overall_result,
    classify_setup_examples,
    classify_sit_out_rules,
)
from edgelab.intraday.pattern_results_schema import (
    MultiSessionReplayRequest,
    MultiSessionReplaySummary,
    NoTradeUsefulnessLabel,
    PatternResultClassification,
)


def test_pattern_result_classification_values() -> None:
    assert {classification.value for classification in PatternResultClassification} == {
        "not_enough_examples",
        "blocked_by_data_quality",
        "weak_or_inconsistent",
        "interesting_but_unproven",
        "worth_more_testing",
        "sit_out_rules_need_review",
    }


def test_multi_session_summary_enforces_research_only_and_not_allowed() -> None:
    request = MultiSessionReplayRequest()

    with pytest.raises(ValueError, match="research-only"):
        MultiSessionReplaySummary(
            summary_id="test-summary",
            request=request,
            sessions_found=0,
            sessions_tested=0,
            usable_sessions=0,
            skipped_due_to_data=0,
            setup_count=0,
            sit_out_count=0,
            completed_pretend_result_count=0,
            favorable_count=0,
            failed_count=0,
            flat_count=0,
            cost_changed_conclusion_count=0,
            classification=PatternResultClassification.NOT_ENOUGH_EXAMPLES,
            bottom_line="Not enough examples yet.",
            what_edgelab_tested="EdgeLab tested local mornings.",
            what_usually_happened="Nothing repeated yet.",
            anything_worth_more_testing="Nothing earns stronger language yet.",
            when_edgelab_sat_out="EdgeLab did not record a sit-out.",
            whether_sitting_out_helped="More examples are needed.",
            why_this_might_be_misleading="Tiny fixtures are workflow tests only.",
            what_edgelab_should_test_next="Add more clean local mornings.",
            research_only_status="Live mode",
        )

    with pytest.raises(ValueError, match="real-money status"):
        MultiSessionReplaySummary(
            summary_id="test-summary",
            request=request,
            sessions_found=0,
            sessions_tested=0,
            usable_sessions=0,
            skipped_due_to_data=0,
            setup_count=0,
            sit_out_count=0,
            completed_pretend_result_count=0,
            favorable_count=0,
            failed_count=0,
            flat_count=0,
            cost_changed_conclusion_count=0,
            classification=PatternResultClassification.NOT_ENOUGH_EXAMPLES,
            bottom_line="Not enough examples yet.",
            what_edgelab_tested="EdgeLab tested local mornings.",
            what_usually_happened="Nothing repeated yet.",
            anything_worth_more_testing="Nothing earns stronger language yet.",
            when_edgelab_sat_out="EdgeLab did not record a sit-out.",
            whether_sitting_out_helped="More examples are needed.",
            why_this_might_be_misleading="Tiny fixtures are workflow tests only.",
            what_edgelab_should_test_next="Add more clean local mornings.",
            real_money_status="Allowed",
        )


def test_multi_session_summary_rejects_action_and_overconfident_language() -> None:
    with pytest.raises(ValueError, match="action instructions"):
        _summary_with_bottom_line("buy now")

    with pytest.raises(ValueError, match="overconfident"):
        _summary_with_bottom_line("This pattern is proven.")


def test_classification_helpers_are_conservative() -> None:
    assert (
        classify_overall_result(
            sessions_tested=10,
            usable_sessions=5,
            skipped_due_to_data=5,
            minimum_useful_sessions=30,
        )
        == PatternResultClassification.BLOCKED_BY_DATA_QUALITY
    )
    assert (
        classify_overall_result(
            sessions_tested=10,
            usable_sessions=10,
            skipped_due_to_data=0,
            minimum_useful_sessions=30,
        )
        == PatternResultClassification.NOT_ENOUGH_EXAMPLES
    )
    assert (
        classify_setup_examples(
            usable_sessions=30,
            completed_examples=30,
            favorable_count=20,
            failed_count=5,
            flat_count=5,
            average_pretend_result=10,
            minimum_useful_sessions=30,
            minimum_setup_examples=10,
            minimum_worth_more_testing_examples=20,
        )
        == PatternResultClassification.WORTH_MORE_TESTING
    )
    assert (
        classify_setup_examples(
            usable_sessions=30,
            completed_examples=10,
            favorable_count=7,
            failed_count=2,
            flat_count=1,
            average_pretend_result=1,
            minimum_useful_sessions=30,
            minimum_setup_examples=10,
            minimum_worth_more_testing_examples=20,
        )
        == PatternResultClassification.INTERESTING_BUT_UNPROVEN
    )
    assert (
        classify_setup_examples(
            usable_sessions=30,
            completed_examples=10,
            favorable_count=4,
            failed_count=4,
            flat_count=2,
            average_pretend_result=-1,
            minimum_useful_sessions=30,
            minimum_setup_examples=10,
            minimum_worth_more_testing_examples=20,
        )
        == PatternResultClassification.WEAK_OR_INCONSISTENT
    )


def test_sit_out_classification_helper_flags_review_cases() -> None:
    assert (
        classify_sit_out_rules(sit_out_count=3, missed_looking_count=0, minimum_examples=10)
        == NoTradeUsefulnessLabel.NEEDS_MORE_EXAMPLES
    )
    assert (
        classify_sit_out_rules(sit_out_count=10, missed_looking_count=4, minimum_examples=10)
        == NoTradeUsefulnessLabel.HARMFUL
    )
    assert (
        classify_sit_out_rules(sit_out_count=10, missed_looking_count=0, minimum_examples=10)
        == NoTradeUsefulnessLabel.USEFUL
    )


def _summary_with_bottom_line(bottom_line: str) -> MultiSessionReplaySummary:
    return MultiSessionReplaySummary(
        summary_id="test-summary",
        request=MultiSessionReplayRequest(),
        sessions_found=0,
        sessions_tested=0,
        usable_sessions=0,
        skipped_due_to_data=0,
        setup_count=0,
        sit_out_count=0,
        completed_pretend_result_count=0,
        favorable_count=0,
        failed_count=0,
        flat_count=0,
        cost_changed_conclusion_count=0,
        classification=PatternResultClassification.NOT_ENOUGH_EXAMPLES,
        bottom_line=bottom_line,
        what_edgelab_tested="EdgeLab tested local mornings.",
        what_usually_happened="Nothing repeated yet.",
        anything_worth_more_testing="Nothing earns stronger language yet.",
        when_edgelab_sat_out="EdgeLab did not record a sit-out.",
        whether_sitting_out_helped="More examples are needed.",
        why_this_might_be_misleading="Tiny fixtures are workflow tests only.",
        what_edgelab_should_test_next="Add more clean local mornings.",
    )
