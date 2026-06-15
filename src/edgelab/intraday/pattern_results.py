"""Multi-session historical replay aggregation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Protocol

from edgelab.intraday.historical_provider import (
    HistoricalIntradayDataProvider,
    LocalCSVHistoricalIntradayProvider,
)
from edgelab.intraday.historical_schema import (
    HistoricalIntradayReadiness,
    HistoricalIntradaySession,
)
from edgelab.intraday.pattern_results_schema import (
    MultiSessionReplayRequest,
    MultiSessionReplaySummary,
    NoTradeReasonSummary,
    NoTradeUsefulnessLabel,
    PatternResultClassification,
    ReplayResultBucket,
    ReplaySessionOutcome,
    SetupTypeSummary,
)
from edgelab.intraday.replay import HistoricalIntradayReplayEngine
from edgelab.intraday.replay_schema import (
    HistoricalReplayDecisionType,
    HistoricalReplayRequest,
    HistoricalReplayResult,
    HistoricalReplayStatus,
    HistoricalReplayStepType,
)
from edgelab.intraday.schema import (
    IntradayHypotheticalTrade,
    IntradaySetupCandidate,
    IntradaySetupType,
)


class ReplayEngineProtocol(Protocol):
    """Small protocol for replay engines used by the multi-session runner."""

    def replay(self, request: HistoricalReplayRequest) -> HistoricalReplayResult:
        """Replay one historical session."""
        ...


NO_TRADE_REASON_LABELS = {
    "choppy_open": "messy open",
    "low_range": "too little movement",
    "conflicting_signals": "mixed signals",
    "poor_data_quality": "poor data quality",
    "incomplete_session": "not enough data",
    "missing_benchmark_context": "missing opening context",
    "unclear_setup": "unclear setup",
    "wide_opening_range": "wide opening range",
    "unsupported_setup": "unclear setup",
    "insufficient_data": "not enough data",
}


class MultiSessionPatternRunner:
    """Run many one-session replays and summarize repeated behavior."""

    def __init__(
        self,
        provider: HistoricalIntradayDataProvider | None = None,
        replay_engine: ReplayEngineProtocol | None = None,
    ) -> None:
        self.provider = provider or LocalCSVHistoricalIntradayProvider()
        self.replay_engine: ReplayEngineProtocol
        if replay_engine is None:
            self.replay_engine = HistoricalIntradayReplayEngine()
        else:
            self.replay_engine = replay_engine

    def run(self, request: MultiSessionReplayRequest | None = None) -> MultiSessionReplaySummary:
        """Run a read-only local multi-session replay summary."""

        request = request or MultiSessionReplayRequest()
        sessions = self.provider.list_sessions(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        outcomes: list[ReplaySessionOutcome] = []
        replay_quality_messages: list[str] = []
        for session in sessions:
            replay_result = self.replay_engine.replay(
                HistoricalReplayRequest(
                    symbol=session.symbol,
                    session_id=session.session_id,
                    hold_minutes=request.hold_minutes,
                    slippage_ticks=request.slippage_ticks,
                    commission_per_contract=request.commission_per_contract,
                    max_one_setup_per_day=request.max_one_setup_per_day,
                    include_evidence_details=request.include_evidence_details,
                )
            )
            outcomes.append(_outcome_from_replay(replay_result, session))
            replay_quality_messages.extend(issue.message for issue in replay_result.quality_issues)

        return _summary_from_outcomes(request, sessions, outcomes, replay_quality_messages)


def classify_overall_result(
    *,
    sessions_tested: int,
    usable_sessions: int,
    skipped_due_to_data: int,
    minimum_useful_sessions: int,
) -> PatternResultClassification:
    """Classify the whole multi-session sample conservatively."""

    if sessions_tested == 0:
        return PatternResultClassification.NOT_ENOUGH_EXAMPLES
    if skipped_due_to_data / sessions_tested > 0.30:
        return PatternResultClassification.BLOCKED_BY_DATA_QUALITY
    if usable_sessions < minimum_useful_sessions:
        return PatternResultClassification.NOT_ENOUGH_EXAMPLES
    return PatternResultClassification.WEAK_OR_INCONSISTENT


def classify_setup_examples(
    *,
    usable_sessions: int,
    completed_examples: int,
    favorable_count: int,
    failed_count: int,
    flat_count: int,
    average_pretend_result: float | None,
    minimum_useful_sessions: int,
    minimum_setup_examples: int,
    minimum_worth_more_testing_examples: int,
    dominant_data_quality_warning: bool = False,
) -> PatternResultClassification:
    """Classify one setup family without implying readiness."""

    if usable_sessions < minimum_useful_sessions or completed_examples < minimum_setup_examples:
        return PatternResultClassification.NOT_ENOUGH_EXAMPLES
    if average_pretend_result is None:
        return PatternResultClassification.WEAK_OR_INCONSISTENT

    favorable_share = favorable_count / completed_examples if completed_examples else 0
    failed_or_flat = failed_count + flat_count
    if (
        completed_examples >= minimum_worth_more_testing_examples
        and favorable_share >= 0.60
        and average_pretend_result > 0
        and not dominant_data_quality_warning
    ):
        return PatternResultClassification.WORTH_MORE_TESTING
    if favorable_count > failed_or_flat and average_pretend_result > 0:
        return PatternResultClassification.INTERESTING_BUT_UNPROVEN
    return PatternResultClassification.WEAK_OR_INCONSISTENT


def classify_sit_out_rules(
    *,
    sit_out_count: int,
    missed_looking_count: int,
    minimum_examples: int,
) -> NoTradeUsefulnessLabel:
    """Classify sit-out reasons with plain, conservative labels."""

    if sit_out_count < minimum_examples:
        return NoTradeUsefulnessLabel.NEEDS_MORE_EXAMPLES
    missed_share = missed_looking_count / sit_out_count if sit_out_count else 0
    if missed_share > 0.30:
        return NoTradeUsefulnessLabel.HARMFUL
    if missed_looking_count == 0:
        return NoTradeUsefulnessLabel.USEFUL
    return NoTradeUsefulnessLabel.INCONCLUSIVE


def _outcome_from_replay(
    result: HistoricalReplayResult, session: HistoricalIntradaySession
) -> ReplaySessionOutcome:
    setup = result.setup_candidates[0] if result.setup_candidates else None
    trade = result.hypothetical_trades[0] if result.hypothetical_trades else None
    data_skipped = (
        result.status
        in {
            HistoricalReplayStatus.INCOMPLETE,
            HistoricalReplayStatus.BLOCKED_BY_DATA_QUALITY,
            HistoricalReplayStatus.UNSUPPORTED,
        }
        or result.session_readiness != HistoricalIntradayReadiness.READY_FOR_REPLAY
    )
    setup_found = setup is not None and setup.setup_type != IntradaySetupType.NO_TRADE
    sat_out = _sat_out(result, setup, setup_found, data_skipped)
    no_trade_reasons = _no_trade_reasons(result, setup, data_skipped, sat_out)
    bucket = _result_bucket(trade, sat_out, data_skipped)
    return ReplaySessionOutcome(
        symbol=result.symbol,
        session_id=result.session_id,
        session_date=session.session_date,
        replay_status=result.status,
        session_readiness=result.session_readiness,
        setup_type=setup.setup_type if setup else None,
        setup_direction=setup.direction if setup else None,
        signal_bar_timestamp=setup.signal_bar_timestamp if setup else None,
        regular_open_timestamp=_regular_open_timestamp(result),
        setup_found=setup_found,
        sat_out=sat_out,
        data_skipped=data_skipped,
        completed_pretend_result=trade is not None,
        result_bucket=bucket,
        result_label=trade.result_label if trade else None,
        pretend_net_result=trade.net_pnl if trade else None,
        pretend_gross_result=trade.gross_pnl if trade else None,
        cost_changed_conclusion=_cost_changed_conclusion(trade),
        no_trade_reasons=no_trade_reasons,
        missed_looking_afterward=_missed_looking_afterward(setup, sat_out),
        opening_gap_bucket=_opening_gap_bucket(setup),
        opening_range_width_bucket=_opening_range_width_bucket(setup),
        quality_issue_count=len(result.quality_issues),
        plain_english_summary=_outcome_summary(result, setup, trade, sat_out, data_skipped),
    )


def _regular_open_timestamp(result: HistoricalReplayResult) -> object | None:
    return next(
        (
            step.replay_time_utc
            for step in result.steps
            if step.step_type == HistoricalReplayStepType.REGULAR_OPEN
        ),
        None,
    )


def _summary_from_outcomes(
    request: MultiSessionReplayRequest,
    sessions: list[HistoricalIntradaySession],
    outcomes: list[ReplaySessionOutcome],
    quality_messages: list[str],
) -> MultiSessionReplaySummary:
    sessions_found = len(sessions)
    sessions_tested = len(outcomes)
    usable_sessions = sum(1 for outcome in outcomes if not outcome.data_skipped)
    skipped_due_to_data = sum(1 for outcome in outcomes if outcome.data_skipped)
    setup_outcomes = [outcome for outcome in outcomes if outcome.setup_found]
    sit_out_outcomes = [outcome for outcome in outcomes if outcome.sat_out]
    completed = [outcome for outcome in outcomes if outcome.completed_pretend_result]
    net_results = [
        outcome.pretend_net_result
        for outcome in completed
        if outcome.pretend_net_result is not None
    ]
    overall_classification = classify_overall_result(
        sessions_tested=sessions_tested,
        usable_sessions=usable_sessions,
        skipped_due_to_data=skipped_due_to_data,
        minimum_useful_sessions=request.minimum_useful_sessions,
    )
    setup_type_summaries = _setup_type_summaries(
        request=request,
        outcomes=setup_outcomes,
        usable_sessions=usable_sessions,
        dominant_data_quality_warning=(
            sessions_tested > 0 and skipped_due_to_data / sessions_tested > 0.30
        ),
    )
    no_trade_summaries = _no_trade_reason_summaries(
        outcomes=sit_out_outcomes,
        minimum_examples=request.minimum_setup_examples,
    )
    classification = _promote_overall_classification(
        overall_classification,
        setup_type_summaries,
        no_trade_summaries,
        usable_sessions,
        request.minimum_useful_sessions,
    )
    return MultiSessionReplaySummary(
        summary_id=_summary_id(request),
        symbol=request.symbol,
        request=request,
        sessions_found=sessions_found,
        sessions_tested=sessions_tested,
        usable_sessions=usable_sessions,
        skipped_due_to_data=skipped_due_to_data,
        setup_count=len(setup_outcomes),
        sit_out_count=len(sit_out_outcomes),
        completed_pretend_result_count=len(completed),
        favorable_count=sum(
            1 for outcome in completed if outcome.result_bucket == ReplayResultBucket.FAVORABLE
        ),
        failed_count=sum(
            1 for outcome in completed if outcome.result_bucket == ReplayResultBucket.FAILED
        ),
        flat_count=sum(
            1 for outcome in completed if outcome.result_bucket == ReplayResultBucket.FLAT
        ),
        cost_changed_conclusion_count=sum(
            1 for outcome in completed if outcome.cost_changed_conclusion
        ),
        average_pretend_result=_average(net_results),
        worst_pretend_result=min(net_results) if net_results else None,
        best_pretend_result=max(net_results) if net_results else None,
        classification=classification,
        session_outcomes=outcomes,
        setup_type_summaries=setup_type_summaries,
        no_trade_reason_summaries=no_trade_summaries,
        quality_issues=_summary_quality_issues(quality_messages, skipped_due_to_data),
        bottom_line=_bottom_line(classification, sessions_tested, usable_sessions),
        what_edgelab_tested=_what_edgelab_tested(request, sessions_tested),
        what_usually_happened=_what_usually_happened(
            len(setup_outcomes), len(sit_out_outcomes), len(completed)
        ),
        anything_worth_more_testing=_anything_worth_more_testing(setup_type_summaries),
        when_edgelab_sat_out=_when_edgelab_sat_out(no_trade_summaries, len(sit_out_outcomes)),
        whether_sitting_out_helped=_whether_sitting_out_helped(no_trade_summaries),
        why_this_might_be_misleading=_why_this_might_be_misleading(usable_sessions, request),
        what_edgelab_should_test_next=_what_to_test_next(classification),
        evidence_details=(
            _evidence_details(request, outcomes) if request.include_evidence_details else {}
        ),
    )


def _setup_type_summaries(
    *,
    request: MultiSessionReplayRequest,
    outcomes: list[ReplaySessionOutcome],
    usable_sessions: int,
    dominant_data_quality_warning: bool,
) -> list[SetupTypeSummary]:
    grouped: dict[IntradaySetupType, list[ReplaySessionOutcome]] = defaultdict(list)
    for outcome in outcomes:
        if outcome.setup_type is not None:
            grouped[outcome.setup_type].append(outcome)

    summaries: list[SetupTypeSummary] = []
    for setup_type in sorted(grouped, key=lambda item: item.value):
        setup_outcomes = grouped[setup_type]
        completed = [outcome for outcome in setup_outcomes if outcome.completed_pretend_result]
        net_results = [
            outcome.pretend_net_result
            for outcome in completed
            if outcome.pretend_net_result is not None
        ]
        favorable = sum(
            1 for outcome in completed if outcome.result_bucket == ReplayResultBucket.FAVORABLE
        )
        failed = sum(
            1 for outcome in completed if outcome.result_bucket == ReplayResultBucket.FAILED
        )
        flat = sum(1 for outcome in completed if outcome.result_bucket == ReplayResultBucket.FLAT)
        classification = classify_setup_examples(
            usable_sessions=usable_sessions,
            completed_examples=len(completed),
            favorable_count=favorable,
            failed_count=failed,
            flat_count=flat,
            average_pretend_result=_average(net_results),
            minimum_useful_sessions=request.minimum_useful_sessions,
            minimum_setup_examples=request.minimum_setup_examples,
            minimum_worth_more_testing_examples=request.minimum_worth_more_testing_examples,
            dominant_data_quality_warning=dominant_data_quality_warning,
        )
        summaries.append(
            SetupTypeSummary(
                setup_type=setup_type,
                examples_found=len(setup_outcomes),
                completed_pretend_results=len(completed),
                favorable_count=favorable,
                failed_count=failed,
                flat_count=flat,
                not_completed_count=len(setup_outcomes) - len(completed),
                average_pretend_result=_average(net_results),
                worst_pretend_result=min(net_results) if net_results else None,
                best_pretend_result=max(net_results) if net_results else None,
                cost_changed_conclusion_count=sum(
                    1 for outcome in completed if outcome.cost_changed_conclusion
                ),
                classification=classification,
                plain_english_summary=_setup_summary_text(setup_type, classification),
                what_usually_happened=_setup_what_happened(len(completed), favorable, failed, flat),
                why_this_might_be_misleading=(
                    "This setup family needs many more clean local mornings before the pattern "
                    "can be trusted."
                ),
                evidence_details={
                    "setup_type": setup_type.value,
                    "examples_found": len(setup_outcomes),
                    "completed_pretend_results": len(completed),
                    "average_pretend_result": _average(net_results),
                },
            )
        )
    return summaries


def _no_trade_reason_summaries(
    *,
    outcomes: list[ReplaySessionOutcome],
    minimum_examples: int,
) -> list[NoTradeReasonSummary]:
    grouped: dict[str, list[ReplaySessionOutcome]] = {
        reason: [] for reason in NO_TRADE_REASON_LABELS
    }
    for outcome in outcomes:
        for reason in outcome.no_trade_reasons:
            grouped.setdefault(reason, []).append(outcome)

    summaries: list[NoTradeReasonSummary] = []
    for reason, reason_outcomes in grouped.items():
        missed = sum(1 for outcome in reason_outcomes if outcome.missed_looking_afterward)
        usefulness = classify_sit_out_rules(
            sit_out_count=len(reason_outcomes),
            missed_looking_count=missed,
            minimum_examples=minimum_examples,
        )
        summaries.append(
            NoTradeReasonSummary(
                reason_type=reason,
                display_reason=NO_TRADE_REASON_LABELS.get(reason, reason.replace("_", " ")),
                appeared_count=len(reason_outcomes),
                what_edgelab_avoided=_avoided_text(reason, len(reason_outcomes)),
                what_edgelab_might_have_missed=_missed_text(missed),
                usefulness_label=usefulness,
                what_needs_more_data=(
                    "Replay more clean local mornings before judging this sit-out rule."
                ),
                evidence_details={
                    "reason_type": reason,
                    "appeared_count": len(reason_outcomes),
                    "missed_looking_afterward_count": missed,
                },
            )
        )
    return summaries


def _sat_out(
    result: HistoricalReplayResult,
    setup: IntradaySetupCandidate | None,
    setup_found: bool,
    data_skipped: bool,
) -> bool:
    if data_skipped:
        return False
    if setup is not None and setup.setup_type == IntradaySetupType.NO_TRADE:
        return True
    if setup_found:
        return False
    return any(
        decision.decision_type == HistoricalReplayDecisionType.SIT_OUT
        for decision in result.decisions
    )


def _no_trade_reasons(
    result: HistoricalReplayResult,
    setup: IntradaySetupCandidate | None,
    data_skipped: bool,
    sat_out: bool,
) -> list[str]:
    reasons: list[str] = []
    if setup is not None and setup.setup_type == IntradaySetupType.NO_TRADE:
        reasons.extend(reason.reason_type.value for reason in setup.no_trade_reasons)
    if sat_out and not reasons:
        reasons.append("unclear_setup")
    if data_skipped:
        if result.status == HistoricalReplayStatus.INCOMPLETE:
            reasons.append("incomplete_session")
        elif result.status == HistoricalReplayStatus.BLOCKED_BY_DATA_QUALITY:
            reasons.append("poor_data_quality")
        else:
            reasons.append("missing_benchmark_context")
    if sat_out and _opening_range_width_bucket(setup) == "wide":
        reasons.append("wide_opening_range")
    return sorted(set(reasons))


def _result_bucket(
    trade: IntradayHypotheticalTrade | None,
    sat_out: bool,
    data_skipped: bool,
) -> ReplayResultBucket:
    if data_skipped:
        return ReplayResultBucket.SKIPPED_DUE_TO_DATA
    if trade is None:
        return ReplayResultBucket.SAT_OUT if sat_out else ReplayResultBucket.NOT_COMPLETED
    if trade.result_label == "positive":
        return ReplayResultBucket.FAVORABLE
    if trade.result_label == "negative":
        return ReplayResultBucket.FAILED
    return ReplayResultBucket.FLAT


def _cost_changed_conclusion(trade: IntradayHypotheticalTrade | None) -> bool:
    if trade is None:
        return False
    return _result_sign(trade.gross_pnl) != _result_sign(trade.net_pnl)


def _missed_looking_afterward(setup: IntradaySetupCandidate | None, sat_out: bool) -> bool:
    if not sat_out or setup is None:
        return False
    context = setup.benchmark_context
    if (
        context.regular_open is None
        or context.first_hour_high is None
        or context.first_hour_low is None
    ):
        return False
    move_pct = (
        max(
            abs(context.first_hour_high - context.regular_open),
            abs(context.first_hour_low - context.regular_open),
        )
        / context.regular_open
        * 100
    )
    return move_pct >= 0.75


def _opening_gap_bucket(setup: IntradaySetupCandidate | None) -> str | None:
    if setup is None or setup.benchmark_context.opening_gap_pct is None:
        return None
    gap = setup.benchmark_context.opening_gap_pct
    if gap >= 0.25:
        return "gap_up"
    if gap <= -0.25:
        return "gap_down"
    return "small_or_flat_gap"


def _opening_range_width_bucket(setup: IntradaySetupCandidate | None) -> str | None:
    if setup is None:
        return None
    context = setup.benchmark_context
    if (
        context.opening_range_high is None
        or context.opening_range_low is None
        or context.regular_open is None
    ):
        return None
    width_pct = (
        (context.opening_range_high - context.opening_range_low) / context.regular_open * 100
    )
    if width_pct < 0.15:
        return "narrow"
    if width_pct >= 1:
        return "wide"
    return "normal"


def _outcome_summary(
    result: HistoricalReplayResult,
    setup: IntradaySetupCandidate | None,
    trade: IntradayHypotheticalTrade | None,
    sat_out: bool,
    data_skipped: bool,
) -> str:
    if data_skipped:
        return "EdgeLab could not trust this local morning enough to compare it."
    if trade is not None:
        return "EdgeLab found a practice setup and later recorded a pretend result."
    if sat_out:
        return "EdgeLab sat out because the local morning did not look clean enough."
    if setup is not None:
        return "EdgeLab found a practice setup, but the pretend result did not finish."
    return "EdgeLab did not find a useful practice setup in this local morning."


def _promote_overall_classification(
    classification: PatternResultClassification,
    setup_summaries: list[SetupTypeSummary],
    no_trade_summaries: list[NoTradeReasonSummary],
    usable_sessions: int,
    minimum_useful_sessions: int,
) -> PatternResultClassification:
    if classification in {
        PatternResultClassification.BLOCKED_BY_DATA_QUALITY,
        PatternResultClassification.NOT_ENOUGH_EXAMPLES,
    }:
        return classification
    if any(
        summary.usefulness_label == NoTradeUsefulnessLabel.HARMFUL for summary in no_trade_summaries
    ):
        return PatternResultClassification.SIT_OUT_RULES_NEED_REVIEW
    if any(
        summary.classification == PatternResultClassification.WORTH_MORE_TESTING
        for summary in setup_summaries
    ):
        return PatternResultClassification.WORTH_MORE_TESTING
    if any(
        summary.classification == PatternResultClassification.INTERESTING_BUT_UNPROVEN
        for summary in setup_summaries
    ):
        return PatternResultClassification.INTERESTING_BUT_UNPROVEN
    if usable_sessions < minimum_useful_sessions:
        return PatternResultClassification.NOT_ENOUGH_EXAMPLES
    return PatternResultClassification.WEAK_OR_INCONSISTENT


def _summary_quality_issues(messages: list[str], skipped_due_to_data: int) -> list[str]:
    issues: list[str] = []
    if skipped_due_to_data:
        issues.append(
            "Some local mornings could not be trusted because their sample data was incomplete "
            "or needed review."
        )
    unique_messages = []
    for message in messages:
        if message not in unique_messages:
            unique_messages.append(message)
    return [*issues, *unique_messages[:5]]


def _bottom_line(
    classification: PatternResultClassification,
    sessions_tested: int,
    usable_sessions: int,
) -> str:
    if sessions_tested == 0:
        return "Not enough examples yet. EdgeLab did not find local mornings to test."
    if usable_sessions < 30:
        return (
            f"Not enough examples yet. EdgeLab replayed {sessions_tested} local morning(s), "
            f"but only {usable_sessions} were clean enough to compare."
        )
    if classification == PatternResultClassification.BLOCKED_BY_DATA_QUALITY:
        return "Too many local mornings had data limits, so EdgeLab cannot compare patterns yet."
    if classification == PatternResultClassification.WORTH_MORE_TESTING:
        return "One repeated practice pattern is worth more testing, but it is still research-only."
    if classification == PatternResultClassification.INTERESTING_BUT_UNPROVEN:
        return "One repeated practice pattern is interesting, but still too thin to trust."
    if classification == PatternResultClassification.SIT_OUT_RULES_NEED_REVIEW:
        return "The sit-out rules need more review before EdgeLab trusts them."
    return "The repeated practice patterns look weak or mixed in the local mornings tested."


def _what_edgelab_tested(request: MultiSessionReplayRequest, sessions_tested: int) -> str:
    scope = f" for {request.symbol}" if request.symbol else ""
    return (
        f"EdgeLab replayed {sessions_tested} local historical morning(s){scope} using the same "
        "one-morning practice test without changing the rules."
    )


def _what_usually_happened(setup_count: int, sit_out_count: int, completed_count: int) -> str:
    return (
        f"EdgeLab found possible practice setups {setup_count} time(s), sat out "
        f"{sit_out_count} time(s), and finished pretend results {completed_count} time(s)."
    )


def _anything_worth_more_testing(setup_summaries: list[SetupTypeSummary]) -> str:
    worth = [
        summary
        for summary in setup_summaries
        if summary.classification == PatternResultClassification.WORTH_MORE_TESTING
    ]
    if worth:
        names = ", ".join(summary.setup_type.value.replace("_", " ") for summary in worth)
        return f"{names} is worth more testing, but it is not a recommendation."
    interesting = [
        summary
        for summary in setup_summaries
        if summary.classification == PatternResultClassification.INTERESTING_BUT_UNPROVEN
    ]
    if interesting:
        return "One practice pattern is interesting, but still needs many more clean mornings."
    return "Nothing earns stronger language yet. Every pattern needs more clean examples."


def _when_edgelab_sat_out(
    no_trade_summaries: list[NoTradeReasonSummary], sit_out_count: int
) -> str:
    if sit_out_count == 0:
        return "EdgeLab did not record a sit-out in these local mornings."
    active = [summary.display_reason for summary in no_trade_summaries if summary.appeared_count]
    if not active:
        return f"EdgeLab sat out {sit_out_count} time(s), mostly because no clean setup appeared."
    return f"EdgeLab sat out {sit_out_count} time(s), often because of {', '.join(active[:3])}."


def _whether_sitting_out_helped(no_trade_summaries: list[NoTradeReasonSummary]) -> str:
    active = [summary for summary in no_trade_summaries if summary.appeared_count]
    if not active:
        return "There are not enough sit-out examples to judge whether restraint helped."
    if any(summary.usefulness_label == NoTradeUsefulnessLabel.HARMFUL for summary in active):
        return "Some skipped mornings looked better afterward, so the sit-out rules need review."
    if all(summary.usefulness_label == NoTradeUsefulnessLabel.USEFUL for summary in active):
        return "The sit-out rules avoided messy mornings in this local sample."
    return "The sit-out rules need more examples before EdgeLab can judge them."


def _why_this_might_be_misleading(usable_sessions: int, request: MultiSessionReplayRequest) -> str:
    if usable_sessions < request.minimum_useful_sessions:
        return (
            "The committed fixtures are tiny workflow tests only. More clean local CSV mornings "
            "are needed before trust increases."
        )
    return (
        "This still uses local replay assumptions and fixed rules. More data and later "
        "out-of-sample checks are needed."
    )


def _what_to_test_next(classification: PatternResultClassification) -> str:
    if classification == PatternResultClassification.BLOCKED_BY_DATA_QUALITY:
        return "Clean or replace weak local CSV mornings, then rerun the same comparison."
    if classification == PatternResultClassification.SIT_OUT_RULES_NEED_REVIEW:
        return "Review more sit-out mornings before changing any rules."
    return (
        "Add more clean local historical mornings, then rerun the same rules without tuning them."
    )


def _setup_summary_text(
    setup_type: IntradaySetupType, classification: PatternResultClassification
) -> str:
    name = setup_type.value.replace("_", " ")
    if classification == PatternResultClassification.NOT_ENOUGH_EXAMPLES:
        return f"{name} does not have enough examples yet."
    if classification == PatternResultClassification.WORTH_MORE_TESTING:
        return f"{name} is worth more testing, but still research-only."
    if classification == PatternResultClassification.INTERESTING_BUT_UNPROVEN:
        return f"{name} is interesting, but still needs more clean mornings."
    return f"{name} looked weak or mixed in the local mornings tested."


def _setup_what_happened(
    completed_count: int, favorable_count: int, failed_count: int, flat_count: int
) -> str:
    if completed_count == 0:
        return "No pretend result finished for this setup family."
    return (
        f"The later move looked helpful {favorable_count} time(s), went the wrong way "
        f"{failed_count} time(s), and looked flat {flat_count} time(s)."
    )


def _avoided_text(reason: str, count: int) -> str:
    label = NO_TRADE_REASON_LABELS.get(reason, reason.replace("_", " "))
    if count == 0:
        return f"EdgeLab has not used the {label} sit-out reason in this local sample."
    return f"EdgeLab avoided {count} local morning(s) because of {label}."


def _missed_text(missed_count: int) -> str:
    if missed_count == 0:
        return "EdgeLab has not seen a clear missed-looking example for this reason yet."
    return f"{missed_count} skipped local morning(s) looked better after the fact."


def _evidence_details(
    request: MultiSessionReplayRequest, outcomes: list[ReplaySessionOutcome]
) -> dict[str, object]:
    return {
        "minimum_useful_sessions": request.minimum_useful_sessions,
        "minimum_setup_examples": request.minimum_setup_examples,
        "minimum_worth_more_testing_examples": request.minimum_worth_more_testing_examples,
        "hold_minutes": request.hold_minutes,
        "slippage_ticks": request.slippage_ticks,
        "commission_per_contract": request.commission_per_contract,
        "result_by_context": _count_by(
            outcome.setup_direction.value
            for outcome in outcomes
            if outcome.setup_direction is not None
        ),
        "opening_gap_bucket": _count_by(
            outcome.opening_gap_bucket
            for outcome in outcomes
            if outcome.opening_gap_bucket is not None
        ),
        "opening_range_width_bucket": _count_by(
            outcome.opening_range_width_bucket
            for outcome in outcomes
            if outcome.opening_range_width_bucket is not None
        ),
        "session_outcome_count": len(outcomes),
    }


def _summary_id(request: MultiSessionReplayRequest) -> str:
    if request.symbol:
        return f"{request.symbol.lower()}-many-morning-practice-test"
    return "all-symbols-many-morning-practice-test"


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _result_sign(value: float) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "flat"


def _count_by(values: Iterable[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return counts
