"""Markdown cards for intraday research spike outputs."""

from __future__ import annotations

from collections.abc import Iterable

from edgelab.intraday.comparative_study_schema import ComparativeStudyResult
from edgelab.intraday.discovery_sprint_schema import (
    DiscoverySprintClassification,
    DiscoverySprintResult,
)
from edgelab.intraday.idea_batch_schema import IdeaBatchResult
from edgelab.intraday.out_of_sample_gate_schema import OutOfSampleGateResult
from edgelab.intraday.pattern_results_schema import MultiSessionReplaySummary
from edgelab.intraday.prop_accounts import PropAccountSimulationResult
from edgelab.intraday.replay_schema import HistoricalReplayResult
from edgelab.intraday.schema import (
    IntradaySetupCandidate,
    IntradaySetupType,
    IntradaySimulationResult,
)
from edgelab.intraday.variant_study_schema import VariantStudyResult


def intraday_setup_to_markdown_card(setup: IntradaySetupCandidate) -> str:
    """Render one intraday setup candidate as plain-English Markdown."""

    return "\n".join(
        [
            f"# {setup.symbol} Intraday Setup Study",
            "",
            "## Bottom Line",
            setup.plain_english_summary,
            "",
            "## What Happened",
            *_bullets(event.plain_english_summary for event in setup.supporting_events),
            "",
            "## Why It Might Matter",
            *_bullets(setup.why_it_appeared),
            "",
            "## Why EdgeLab Would Sit Out",
            *_bullets(_sit_out_lines(setup)),
            "",
            "## Reasons To Be Careful",
            *_bullets(setup.what_is_missing),
            "",
            "## What Needs Real Historical Testing",
            "- Real one-minute intraday data.",
            "- More sessions across different market conditions.",
            "- Out-of-sample replay before any trust increases.",
            "",
            "## Real-Money Status",
            f"- {setup.real_money_status}",
        ]
    )


def intraday_simulation_to_markdown_card(result: IntradaySimulationResult) -> str:
    """Render a simulation result as plain-English Markdown."""

    return "\n".join(
        [
            f"# {result.symbol} Intraday Simulation Study",
            "",
            "## Bottom Line",
            result.plain_english_summary,
            "",
            "## What Happened",
            *_setup_lines(result.setup_candidates),
            "",
            "## Why It Might Matter",
            "- EdgeLab translated chart-like behavior into measurable fixture events.",
            "- The result can be reviewed as research workflow evidence only.",
            "",
            "## Why EdgeLab Would Sit Out",
            *_sit_out_result_lines(result),
            "",
            "## Hypothetical Result",
            *_trade_lines(result),
            "",
            "## Reasons To Be Careful",
            *_bullets(_quality_lines(result)),
            "",
            "## What Needs Real Historical Testing",
            "- Real historical intraday data.",
            "- Replay across many first-hour sessions.",
            "- Separate validation before any paper or live path.",
            "",
            "## Spike Verdict",
            f"- {result.spike_verdict.value.replace('_', ' ')}",
            "",
            "## Real-Money Status",
            f"- {result.real_money_status}",
        ]
    )


def prop_account_to_markdown_card(result: PropAccountSimulationResult) -> str:
    """Render a generic prop-account simulation as Markdown."""

    return "\n".join(
        [
            "# Generic Prop-Account Scaling Study",
            "",
            "## Bottom Line",
            result.plain_english_summary,
            "",
            "## What Happened",
            f"- Single-account sample result: ${result.single_account_net_pnl:,.2f}",
            f"- Copied-account total: ${result.copied_account_total_net_pnl:,.2f}",
            "",
            "## Why It Might Matter",
            "- Scaling changes economics, but it does not create an edge.",
            "- The same result repeated across accounts can enlarge both outcomes and mistakes.",
            "",
            "## Hypothetical Result",
            f"- Qualification target reached: {_yes_no(result.qualification_target_reached)}",
            f"- Max loss breached: {_yes_no(result.max_loss_breached)}",
            f"- Daily loss breached: {_yes_no(result.daily_loss_breached)}",
            f"- Payout split estimate: ${result.payout_split_estimate:,.2f}",
            "",
            "## Reasons To Be Careful",
            *_bullets(result.cautions),
            "",
            "## What Needs Real Historical Testing",
            "- A real historical sequence of intraday outcomes.",
            "- Program-specific rules reviewed outside this generic model.",
            "- Evidence that the underlying setup has durable behavior.",
            "",
            "## Real-Money Status",
            f"- {result.real_money_status}",
        ]
    )


def historical_replay_to_markdown_card(result: HistoricalReplayResult) -> str:
    """Render a historical replay as plain-English Markdown."""

    return "\n".join(
        [
            f"# {result.symbol} Past Morning Practice Test",
            "",
            "## Bottom line",
            result.bottom_line,
            "",
            "## What EdgeLab would have done in practice mode",
            *_bullets(_practice_mode_lines(result)),
            "",
            "## Pretend start and finish",
            *_bullets(_pretend_result_lines(result)),
            "",
            "## What happened afterward",
            result.what_happened,
            "",
            "## Why this might be misleading",
            result.why_it_might_be_misleading,
            "",
            "## What EdgeLab should test next",
            result.next_review_item,
            "",
            "## Real-money status: Not allowed",
            f"- {result.real_money_status}",
            "",
            "## Evidence details",
            *_bullets(_replay_evidence_lines(result)),
        ]
    )


def multi_session_replay_to_markdown_card(summary: MultiSessionReplaySummary) -> str:
    """Render a multi-session replay summary as plain-English Markdown."""

    return "\n".join(
        [
            "# Many-Morning Practice Test",
            "",
            "## Bottom line",
            summary.bottom_line,
            "",
            "## What EdgeLab tested",
            summary.what_edgelab_tested,
            "",
            "## What usually happened",
            summary.what_usually_happened,
            "",
            "## Whether anything deserves more testing",
            summary.anything_worth_more_testing,
            "",
            "## When EdgeLab sat out",
            summary.when_edgelab_sat_out,
            "",
            "## Whether sitting out seemed helpful",
            summary.whether_sitting_out_helped,
            "",
            "## Why this might be misleading",
            summary.why_this_might_be_misleading,
            "",
            "## What EdgeLab should test next",
            summary.what_edgelab_should_test_next,
            "",
            "## Real-money status: Not allowed",
            f"- {summary.real_money_status}",
            "",
            "## Evidence details",
            *_bullets(_multi_session_evidence_lines(summary)),
        ]
    )


def comparative_study_to_markdown_card(result: ComparativeStudyResult) -> str:
    """Render a SPY/QQQ comparative study as plain-English Markdown."""

    return "\n".join(
        [
            "# SPY vs QQQ Pattern Study",
            "",
            "## Bottom line",
            result.bottom_line,
            "",
            "## What EdgeLab compared",
            result.what_edgelab_compared,
            (
                "EdgeLab watches the first few minutes after the open. If price pushes outside "
                "that early range but cannot hold the move, EdgeLab marks it as a failed early "
                "move."
            ),
            "",
            "## What looked different",
            result.what_looked_different,
            "",
            "## Why that might matter",
            result.why_that_might_matter,
            "",
            "## Why this might be misleading",
            result.why_this_might_be_misleading,
            "",
            "## What EdgeLab should test next",
            result.what_edgelab_should_test_next,
            "",
            "## What this is leading toward",
            (
                "Eventually, EdgeLab should turn well-tested research patterns into a simple "
                "live watch message: sit out, keep watching, or practice setup found. Later, in "
                "paper mode, a setup would include a pretend start, planned finish, and reason "
                "to stop watching it. This does not exist yet as a live signal."
            ),
            "",
            "## Real-money status: Not allowed",
            f"- {result.real_money_status}",
            "",
            "## Evidence details",
            *_bullets(_comparative_evidence_lines(result)),
        ]
    )


def idea_batch_to_markdown_card(result: IdeaBatchResult) -> str:
    """Render a structured idea batch result as concise Markdown."""

    return "\n".join(
        [
            f"# {result.batch_name}",
            "",
            "## Headline",
            result.current_conclusion,
            "",
            "## Ideas Tested",
            *_bullets(item.plain_english_name for item in result.accepted_ideas),
            "",
            "## Securities Tested",
            ", ".join(result.securities_tested)
            if result.securities_tested
            else "No securities tested.",
            "",
            "## Best Idea If Any",
            result.best_idea_if_any,
            "",
            "## Ideas Rejected",
            *_bullets(_idea_batch_rejected_lines(result)),
            "",
            "## Ideas Needing More Examples",
            *_bullets(result.ideas_needing_more_examples or ["None"]),
            "",
            "## Ideas With Mixed Results / No Clear Answer",
            *_bullets(result.ideas_mixed_results or ["None"]),
            "",
            "## Next Action",
            result.next_action,
            "",
            "## Real-Money Status",
            f"- {result.real_money_status}",
            "",
            "## Evidence Details",
            f"- Ideas submitted: {result.ideas_submitted}",
            f"- Ideas tested: {result.ideas_tested}",
            "- Local historical research only.",
            "- No AI call was made.",
        ]
    )


def variant_study_to_markdown_card(result: VariantStudyResult) -> str:
    """Render a controlled variant study as plain-English Markdown."""

    return "\n".join(
        [
            "# Controlled Variant Study",
            "",
            "## Bottom line",
            result.bottom_line,
            "",
            "## What EdgeLab tested",
            result.what_edgelab_tested,
            "",
            "## What looked different",
            result.what_looked_different,
            "",
            "## Which version, if any, deserves more testing",
            result.which_version_deserves_more_testing,
            "",
            "## Why this might be misleading",
            result.why_this_might_be_misleading,
            "",
            "## What EdgeLab should test next",
            result.what_edgelab_should_test_next,
            "",
            "## Real-money status: Not allowed",
            f"- {result.real_money_status}",
            "- This is local historical research only. It is not live and not guidance for action.",
            "",
            "## Evidence details",
            *_bullets(_variant_study_evidence_lines(result)),
        ]
    )


def out_of_sample_gate_to_markdown_card(result: OutOfSampleGateResult) -> str:
    """Render an out-of-sample gate as plain-English Markdown."""

    return "\n".join(
        [
            "# Out-of-Sample Check",
            "",
            "## Bottom line",
            result.bottom_line,
            "",
            "## What EdgeLab checked",
            result.what_edgelab_checked,
            "",
            "## What changed on later data",
            result.what_changed_on_later_data,
            "",
            "## What this means",
            result.what_this_means,
            "",
            "## What EdgeLab should test next",
            result.what_edgelab_should_test_next,
            "",
            "## Why this might be misleading",
            result.why_this_might_be_misleading,
            "",
            "## Real-money status: Not allowed",
            f"- {result.real_money_status}",
            "- This is local historical research only. It is not live and not a recommendation.",
            "",
            "## Evidence details",
            *_bullets(_out_of_sample_evidence_lines(result)),
        ]
    )


def discovery_sprint_to_markdown_card(result: DiscoverySprintResult) -> str:
    """Render a discovery sprint as plain-English Markdown."""

    mixed = _discovery_strategy_names(
        result,
        {
            DiscoverySprintClassification.NO_CLEAR_PATTERN,
            DiscoverySprintClassification.DID_NOT_HOLD_UP_LATER,
        },
    )
    needs_examples = _discovery_strategy_names(
        result,
        {DiscoverySprintClassification.NOT_ENOUGH_EXAMPLES},
    )
    rejected = _discovery_strategy_names(
        result,
        {DiscoverySprintClassification.REJECT_FOR_NOW},
    )
    best = _discovery_strategy_names(
        result,
        {
            DiscoverySprintClassification.WORTH_MORE_TESTING,
            DiscoverySprintClassification.HELD_UP_ON_LATER_CHECK,
        },
    )
    return "\n".join(
        [
            "# Intraday Strategy Discovery Sprint",
            "",
            "## Headline",
            (
                f"EdgeLab tested {result.strategy_count} intraday ideas across "
                f"{len(result.symbols_tested)} local symbols. {result.current_conclusion}"
            ),
            "",
            "## Securities tested",
            ", ".join(result.symbols_tested),
            "",
            "## Strategies tested",
            ", ".join(result.strategy_ideas_tested),
            "",
            "## Main result",
            result.bottom_line,
            "",
            "## Best candidates",
            best or result.best_candidate_if_any,
            "",
            "## Ideas to reject for now",
            rejected or "None from this pass.",
            "",
            "## Ideas needing more examples",
            needs_examples or "None from this pass.",
            "",
            "## Mixed results / no clear answer",
            mixed or "None from this pass.",
            "",
            "## Next research action",
            (
                "Try structured local ideas against this free universe, or add more free symbols "
                "before considering paid data."
            ),
            "",
            "## Real-money status: Not allowed",
            f"- {result.real_money_status}",
            "- This is local historical research only. It is not live and not guidance for action.",
            "",
            "## Evidence details",
            "- Full evidence remains in the JSON endpoint at /intraday/discovery-sprint.",
        ]
    )


def _setup_lines(setups: list[IntradaySetupCandidate]) -> list[str]:
    return [f"- {setup.plain_english_summary}" for setup in setups] or ["- No setup was selected."]


def _sit_out_result_lines(result: IntradaySimulationResult) -> list[str]:
    lines: list[str] = []
    for setup in result.setup_candidates:
        lines.extend(_sit_out_lines(setup))
    return [f"- {line}" for line in lines] or ["- No sit-out reason was triggered in this fixture."]


def _sit_out_lines(setup: IntradaySetupCandidate) -> list[str]:
    lines = [reason.message for reason in setup.no_trade_reasons]
    if setup.setup_type != IntradaySetupType.NO_TRADE:
        lines.extend(setup.why_edgelab_might_sit_out)
    return lines or ["No sit-out reason was triggered in this fixture."]


def _trade_lines(result: IntradaySimulationResult) -> list[str]:
    if not result.hypothetical_trades:
        return ["- No hypothetical result was calculated."]
    return [
        f"- {trade.symbol}: {trade.result_label} ${trade.net_pnl:,.2f} net over the fixture hold."
        for trade in result.hypothetical_trades
    ]


def _quality_lines(result: IntradaySimulationResult) -> list[str]:
    return [issue.message for issue in result.quality_issues] or [
        "No additional fixture quality issues were reported."
    ]


def _practice_mode_lines(result: HistoricalReplayResult) -> list[str]:
    if result.status.value in {"incomplete", "blocked_by_data_quality", "unsupported"}:
        choice = "Not enough data."
    elif result.setup_candidates and result.setup_candidates[0].setup_type.value == "no_trade":
        choice = "Sit out."
    elif result.setup_candidates:
        choice = "Practice setup found."
    else:
        choice = "Keep watching."

    lines = [choice]
    if result.decisions:
        lines.append(result.decisions[-1].plain_english_summary)
    return lines


def _pretend_result_lines(result: HistoricalReplayResult) -> list[str]:
    if not result.hypothetical_trades:
        return ["No pretend start or finish was calculated."]

    pretend = result.hypothetical_trades[0]
    return [
        f"Pretend start: {pretend.entry_price:.2f}.",
        f"Pretend finish: {pretend.exit_price:.2f}.",
        f"Pretend result: {pretend.result_label}.",
    ]


def _replay_evidence_lines(result: HistoricalReplayResult) -> list[str]:
    issue_lines = [issue.message for issue in result.quality_issues]
    details = [
        f"Internal replay status: {result.status.value.replace('_', ' ')}.",
        f"Session readiness: {result.session_readiness.value.replace('_', ' ')}.",
        f"Steps recorded: {len(result.steps)}.",
        f"Decisions recorded: {len(result.decisions)}.",
    ]
    if result.hypothetical_trades:
        details.append(f"Hypothetical result label: {result.hypothetical_trades[0].result_label}.")
    return [*details, *issue_lines]


def _multi_session_evidence_lines(summary: MultiSessionReplaySummary) -> list[str]:
    lines = [
        f"Local mornings found: {summary.sessions_found}.",
        f"Mornings tested: {summary.sessions_tested}.",
        f"Mornings clean enough to replay: {summary.usable_sessions}.",
        f"Mornings EdgeLab could not trust: {summary.skipped_due_to_data}.",
        f"Possible practice setups found: {summary.setup_count}.",
        f"Sit-out mornings: {summary.sit_out_count}.",
        f"Finished pretend results: {summary.completed_pretend_result_count}.",
        f"Later move looked helpful: {summary.favorable_count}.",
        f"Later move went the wrong way: {summary.failed_count}.",
        f"Later move looked flat: {summary.flat_count}.",
        f"Overall research label: {summary.classification.value.replace('_', ' ')}.",
    ]
    if summary.average_pretend_result is not None:
        lines.append(f"Average pretend result: {summary.average_pretend_result:.2f}.")
    if summary.worst_pretend_result is not None:
        lines.append(f"Weakest pretend result: {summary.worst_pretend_result:.2f}.")
    if summary.best_pretend_result is not None:
        lines.append(f"Strongest pretend result: {summary.best_pretend_result:.2f}.")
    lines.extend(summary.quality_issues)
    return lines


def _comparative_evidence_lines(result: ComparativeStudyResult) -> list[str]:
    lines = [
        f"Technical research label: {result.classification.value.replace('_', ' ')}.",
        "Technical setup name: Opening Range Failure.",
        f"Comparison available: {_yes_no(result.comparison_available)}.",
        f"Cache status: {result.cache_metadata.get('cache_status', 'unknown')}.",
        (
            "Moved as expected means the market moved in the direction EdgeLab was testing "
            "after the practice setup appeared. It does not mean the setup is proven."
        ),
    ]
    for summary in result.setup_family_comparison.symbol_summaries:
        freshness = summary.saved_run_freshness.value.replace("_", " ")
        lines.extend(
            [
                f"{summary.symbol}: saved run freshness {freshness}.",
                f"{summary.symbol}: {summary.sessions_tested} mornings tested.",
                f"{summary.symbol}: {summary.usable_sessions} mornings usable.",
                (
                    f"{summary.symbol}: {summary.possible_setup_count} possible "
                    "early-failed-move examples."
                ),
                f"{summary.symbol}: {summary.sit_out_count} sit-out mornings.",
                (f"{summary.symbol}: moved as expected {summary.helpful_afterward_count} time(s)."),
                (
                    f"{summary.symbol}: moved against the test "
                    f"{summary.wrong_way_afterward_count} time(s)."
                ),
                (
                    f"{summary.symbol}: did not move enough to matter "
                    f"{summary.flat_afterward_count} time(s)."
                ),
            ]
        )
    lines.extend(issue.message for issue in result.quality_issues)
    return lines


def _variant_study_evidence_lines(result: VariantStudyResult) -> list[str]:
    lines = [
        f"Technical research label: {result.classification.value.replace('_', ' ')}.",
        "Technical setup name: Opening Range Failure.",
        f"Study available: {_yes_no(result.study_available)}.",
        f"Cache status: {result.cache_metadata.get('cache_status', 'unknown')}.",
        (
            "Moved as expected means the later local move matched the direction EdgeLab was "
            "testing. It does not mean the setup is proven."
        ),
    ]
    for summary in result.variant_summaries:
        lines.extend(
            [
                f"{summary.plain_english_label}: {summary.examples_found} possible examples.",
                f"{summary.plain_english_label}: {summary.examples_completed} finished examples.",
                (
                    f"{summary.plain_english_label}: moved as expected "
                    f"{summary.moved_as_expected_count} time(s)."
                ),
                (
                    f"{summary.plain_english_label}: moved against the test "
                    f"{summary.moved_against_test_count} time(s)."
                ),
                (
                    f"{summary.plain_english_label}: did not move enough to matter "
                    f"{summary.did_not_move_enough_count} time(s)."
                ),
                (
                    f"{summary.plain_english_label}: internal label "
                    f"{summary.conservative_classification.value.replace('_', ' ')}."
                ),
            ]
        )
    lines.extend(issue.message for issue in result.quality_issues)
    return lines


def _out_of_sample_evidence_lines(result: OutOfSampleGateResult) -> list[str]:
    lines = [
        f"Gate conclusion: {result.gate_conclusion.value.replace('_', ' ')}.",
        f"Split strategy: {result.split_strategy.value.replace('_', ' ')}.",
        f"Proof limitation: {result.proof_limitations}",
    ]
    if result.discovery_period is not None:
        lines.append(
            "Discovery period: "
            f"{result.discovery_period.start_date} through {result.discovery_period.end_date}."
        )
    if result.holdout_period is not None:
        lines.append(
            f"Holdout period: {result.holdout_period.start_date} "
            f"through {result.holdout_period.end_date}."
        )
    for comparison in result.variant_comparisons:
        lines.append(f"{comparison.plain_english_label}: {comparison.gate_conclusion_translation}")
    lines.extend(warning.message for warning in result.data_quality_warnings)
    return lines


def _discovery_sprint_evidence_lines(result: DiscoverySprintResult) -> list[str]:
    lines = [
        f"Symbols tested: {', '.join(result.symbols_tested)}.",
        f"Strategy ideas tested: {', '.join(result.strategy_ideas_tested)}.",
        f"Date range: {result.date_range}.",
        f"Later-year check: {result.later_check_range}.",
        f"Strategy count: {result.strategy_count}.",
        f"AI idea intake: {result.ai_idea_intake_summary}",
    ]
    for item in result.evidence_details.get("data_quality_by_symbol", []):
        lines.append(
            f"{item['symbol']} data: {item['first_hour_completeness_summary']} "
            f"Quality issues: {item['quality_issues']}."
        )
    for strategy_result in result.strategy_results:
        lines.append(
            f"{strategy_result.strategy_name}: {strategy_result.status}; "
            f"{strategy_result.current_conclusion}"
        )
    return lines


def _discovery_strategy_names(
    result: DiscoverySprintResult,
    classifications: set[DiscoverySprintClassification],
) -> str:
    names = [
        strategy.strategy_name
        for strategy in result.strategy_results
        if strategy.classification in classifications
    ]
    return ", ".join(names)


def _idea_batch_rejected_lines(result: IdeaBatchResult) -> list[str]:
    return [
        (
            f"{item.plain_english_name}: {item.classification_label}"
            + (f" ({item.rejection_reason})" if item.rejection_reason else "")
        )
        for item in result.rejected_ideas
    ]


def _bullets(items: Iterable[str]) -> list[str]:
    return [f"- {item}" for item in items] or ["- None."]


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"
