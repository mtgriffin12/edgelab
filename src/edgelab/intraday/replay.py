"""Historical intraday replay engine."""

from __future__ import annotations

from datetime import datetime, timedelta

from edgelab.intraday.benchmarks import calculate_opening_benchmarks
from edgelab.intraday.historical_provider import (
    HistoricalIntradayDataProvider,
    LocalCSVHistoricalIntradayProvider,
)
from edgelab.intraday.historical_schema import (
    HistoricalIntradayBar,
    HistoricalIntradayImportResult,
    HistoricalIntradayQualityIssue,
    HistoricalIntradayReadiness,
)
from edgelab.intraday.replay_schema import (
    HistoricalReplayDecision,
    HistoricalReplayDecisionType,
    HistoricalReplayQualityIssue,
    HistoricalReplayRequest,
    HistoricalReplayResult,
    HistoricalReplayStatus,
    HistoricalReplayStep,
    HistoricalReplayStepType,
)
from edgelab.intraday.schema import (
    IntradayBar,
    IntradayHypotheticalTrade,
    IntradaySessionType,
    IntradaySetupCandidate,
    IntradaySetupDirection,
    IntradaySetupType,
)
from edgelab.intraday.setups import IntradaySetupDetector

OPENING_RANGE_BAR_COUNT = 5


class HistoricalIntradayReplayEngine:
    """Replay one imported historical intraday session bar by bar."""

    def __init__(
        self,
        provider: HistoricalIntradayDataProvider | None = None,
        setup_detector: IntradaySetupDetector | None = None,
    ) -> None:
        self.provider = provider or LocalCSVHistoricalIntradayProvider()
        self.setup_detector = setup_detector or IntradaySetupDetector()

    def replay(self, request: HistoricalReplayRequest) -> HistoricalReplayResult:
        """Replay one local historical session without using future bars."""

        import_result = self.provider.load_session(request.symbol, request.session_id)
        if not import_result.sessions:
            return _unsupported_result(request)

        session = import_result.sessions[0]
        bars = [_historical_bar_to_intraday_bar(bar) for bar in import_result.bars]
        bars = sorted(bars, key=lambda bar: bar.timestamp)
        base_issues = [
            _replay_issue_from_historical(issue) for issue in import_result.quality_issues
        ]

        if not bars:
            return _unsupported_result(
                request,
                extra_issues=[
                    HistoricalReplayQualityIssue(
                        code="missing_replay_bars",
                        message="No local historical bars were available for this replay.",
                        symbol=request.symbol,
                        session_id=request.session_id,
                    )
                ],
            )

        if session.readiness in {
            HistoricalIntradayReadiness.UNUSABLE,
            HistoricalIntradayReadiness.NEEDS_REVIEW,
        }:
            return _non_replayable_result(
                request=request,
                bars=bars,
                status=HistoricalReplayStatus.BLOCKED_BY_DATA_QUALITY,
                session_readiness=session.readiness,
                quality_issues=[
                    *base_issues,
                    HistoricalReplayQualityIssue(
                        code="session_not_clean_enough_for_replay",
                        message="This sample has data issues that block the practice test.",
                        symbol=request.symbol,
                        session_id=request.session_id,
                    ),
                ],
                bottom_line=(
                    "EdgeLab could not trust this morning because the data needs cleanup first."
                ),
                decision_type=HistoricalReplayDecisionType.BLOCKED_BY_QUALITY,
                decision_summary="EdgeLab stopped instead of trusting weak data.",
            )

        if session.readiness == HistoricalIntradayReadiness.INCOMPLETE:
            return _non_replayable_result(
                request=request,
                bars=bars,
                status=HistoricalReplayStatus.INCOMPLETE,
                session_readiness=session.readiness,
                quality_issues=[
                    *base_issues,
                    HistoricalReplayQualityIssue(
                        code="insufficient_first_hour_data",
                        message="The practice test needs at least five clean first-hour minutes.",
                        symbol=request.symbol,
                        session_id=request.session_id,
                    ),
                ],
                bottom_line=(
                    "EdgeLab could not trust this morning because the sample has too few minutes."
                ),
                decision_type=HistoricalReplayDecisionType.INSUFFICIENT_DATA,
                decision_summary="EdgeLab marked this as not enough data.",
            )

        return self._replay_ready_session(request, import_result, bars, base_issues)

    def _replay_ready_session(
        self,
        request: HistoricalReplayRequest,
        import_result: HistoricalIntradayImportResult,
        bars: list[IntradayBar],
        base_issues: list[HistoricalReplayQualityIssue],
    ) -> HistoricalReplayResult:
        steps: list[HistoricalReplayStep] = [
            _session_loaded_step(request, bars[0], len(import_result.bars))
        ]
        decisions: list[HistoricalReplayDecision] = []
        quality_issues = list(base_issues)
        setup_candidates: list[IntradaySetupCandidate] = []
        hypothetical_trades: list[IntradayHypotheticalTrade] = []
        detected_setup: IntradaySetupCandidate | None = None
        no_trade_marked = False
        entry_marked = False
        status = HistoricalReplayStatus.COMPLETED

        for index, current_bar in enumerate(bars):
            visible_bars = bars[: index + 1]
            step = _visibility_step(request, current_bar, visible_bars)
            steps.append(step)

            if current_bar.session_type != IntradaySessionType.REGULAR_FIRST_HOUR:
                continue

            regular_count = _regular_first_hour_count(visible_bars)
            if regular_count == 1:
                decisions.append(_keep_watching_decision(request, current_bar))
            if regular_count < OPENING_RANGE_BAR_COUNT:
                continue

            benchmarks = calculate_opening_benchmarks(visible_bars)
            events = self.setup_detector.detect_events(visible_bars, benchmarks)
            for event in events:
                if event.timestamp == current_bar.timestamp and not _step_exists(
                    steps, HistoricalReplayStepType.EVENT_DETECTED, event.timestamp
                ):
                    steps.append(_event_step(request, visible_bars, event.plain_english_summary))

            if detected_setup is None and not no_trade_marked:
                candidates = self.setup_detector.detect_setups(
                    visible_bars,
                    benchmarks,
                    max_one_setup_per_day=request.max_one_setup_per_day,
                )
                selected = _select_replay_candidate(
                    candidates,
                    is_final_bar=index == len(bars) - 1,
                )
                if selected is not None:
                    setup_candidates = [selected]
                    if selected.setup_type == IntradaySetupType.NO_TRADE:
                        no_trade_marked = True
                        steps.append(_no_trade_step(request, visible_bars, selected))
                        decisions.append(_sit_out_decision(request, selected))
                    else:
                        detected_setup = selected
                        steps.append(_setup_step(request, visible_bars, selected))
                        decisions.append(_setup_decision(request, selected))

            if detected_setup is None:
                continue

            entry_bar = _next_bar_after_signal(visible_bars, detected_setup.signal_bar_timestamp)
            if entry_bar is None:
                if index == len(bars) - 1:
                    quality_issues.append(
                        HistoricalReplayQualityIssue(
                            code="insufficient_entry_data",
                            message=(
                                "A setup appeared, but no later bar was visible for the "
                                "hypothetical entry check."
                            ),
                            symbol=request.symbol,
                            session_id=request.session_id,
                            replay_time_utc=current_bar.timestamp,
                        )
                    )
                    decisions.append(_insufficient_data_decision(request, current_bar))
                    status = HistoricalReplayStatus.INCOMPLETE
                continue

            if not entry_marked:
                steps.append(_entry_step(request, visible_bars, detected_setup, entry_bar))
                entry_marked = True

            trade = _simulate_visible_hypothetical_result(
                visible_bars,
                detected_setup,
                request,
                point_value=_point_value(import_result),
                tick_size=_tick_size(import_result),
            )
            if trade is not None and not hypothetical_trades:
                hypothetical_trades.append(trade)
                steps.append(_exit_step(request, visible_bars, trade))
                decisions.append(_result_decision(request, trade))
            elif index == len(bars) - 1 and not hypothetical_trades:
                quality_issues.append(
                    HistoricalReplayQualityIssue(
                        code="insufficient_exit_data",
                        message=(
                            "A setup and later entry check appeared, but no exit bar was "
                            "visible for the requested hold time."
                        ),
                        symbol=request.symbol,
                        session_id=request.session_id,
                        replay_time_utc=current_bar.timestamp,
                    )
                )
                decisions.append(_insufficient_data_decision(request, current_bar))
                status = HistoricalReplayStatus.INCOMPLETE

        if not setup_candidates:
            final_bar = bars[-1]
            decisions.append(_final_sit_out_decision(request, final_bar))
            steps.append(_final_no_trade_step(request, bars))

        steps.append(_completed_step(request, bars, status))
        return HistoricalReplayResult(
            replay_id=_replay_id(request.symbol, request.session_id),
            symbol=request.symbol,
            session_id=request.session_id,
            status=status,
            session_readiness=HistoricalIntradayReadiness.READY_FOR_REPLAY,
            steps=steps,
            decisions=decisions,
            setup_candidates=setup_candidates,
            hypothetical_trades=hypothetical_trades,
            quality_issues=quality_issues,
            bottom_line=_bottom_line(status, setup_candidates, hypothetical_trades),
            what_edgelab_tested=(
                "EdgeLab replayed one past morning one minute at a time to see whether it "
                "would have noticed something useful without peeking ahead."
            ),
            what_happened=_what_happened(setup_candidates, hypothetical_trades, quality_issues),
            why_it_might_be_misleading=(
                "This is one sample morning using local sample data. One example does not "
                "prove a pattern, real costs may differ, and real money is not allowed."
            ),
            next_review_item=_next_review_item(status, setup_candidates, hypothetical_trades),
            evidence_details=_result_evidence_details(request, bars, steps)
            if request.include_evidence_details
            else {},
        )


def _historical_bar_to_intraday_bar(bar: HistoricalIntradayBar) -> IntradayBar:
    return IntradayBar(
        symbol=bar.symbol,
        timestamp=bar.timestamp_utc,
        interval=bar.interval,
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=bar.volume,
        session_type=bar.session_type,
        session_id=bar.session_id,
        source=f"historical-{bar.provider}",
        ingested_at=bar.ingested_at,
    )


def _replay_issue_from_historical(
    issue: HistoricalIntradayQualityIssue,
) -> HistoricalReplayQualityIssue:
    return HistoricalReplayQualityIssue(
        code=f"historical_{issue.code}",
        message=issue.message,
        severity=issue.severity,
        symbol=issue.symbol,
        session_id=issue.session_id,
        replay_time_utc=issue.timestamp_utc,
    )


def _unsupported_result(
    request: HistoricalReplayRequest,
    extra_issues: list[HistoricalReplayQualityIssue] | None = None,
) -> HistoricalReplayResult:
    issues = extra_issues or [
        HistoricalReplayQualityIssue(
            code="historical_session_not_found",
            message="No matching local historical sample was found for the practice test.",
            symbol=request.symbol,
            session_id=request.session_id,
        )
    ]
    return HistoricalReplayResult(
        replay_id=_replay_id(request.symbol, request.session_id),
        symbol=request.symbol,
        session_id=request.session_id,
        status=HistoricalReplayStatus.UNSUPPORTED,
        session_readiness=HistoricalIntradayReadiness.UNUSABLE,
        quality_issues=issues,
        bottom_line="EdgeLab could not test this morning because the local sample was missing.",
        what_edgelab_tested="EdgeLab tried to open one past morning for a practice test.",
        what_happened="No practice test ran because the requested local sample was not available.",
        why_it_might_be_misleading=(
            "A missing local file says nothing about whether a setup has value."
        ),
        next_review_item="Check that the local CSV sample exists and has the expected morning ID.",
    )


def _non_replayable_result(
    *,
    request: HistoricalReplayRequest,
    bars: list[IntradayBar],
    status: HistoricalReplayStatus,
    session_readiness: HistoricalIntradayReadiness,
    quality_issues: list[HistoricalReplayQualityIssue],
    bottom_line: str,
    decision_type: HistoricalReplayDecisionType,
    decision_summary: str,
) -> HistoricalReplayResult:
    steps = [_session_loaded_step(request, bars[0], len(bars))]
    steps.extend(
        _visibility_step(request, bar, bars[: index + 1]) for index, bar in enumerate(bars)
    )
    final_bar = bars[-1]
    decisions = [
        HistoricalReplayDecision(
            decision_id=f"{_replay_id(request.symbol, request.session_id)}-{decision_type.value}",
            symbol=request.symbol,
            session_id=request.session_id,
            replay_time_utc=final_bar.timestamp,
            decision_type=decision_type,
            plain_english_summary=decision_summary,
            why="The local data was not clean or complete enough for a practice decision.",
            what_would_change_our_mind=(
                "A clean local CSV sample with enough first-hour minutes would allow testing."
            ),
            what_to_check_next="Review the CSV reasons to be careful before adding more samples.",
        )
    ]
    return HistoricalReplayResult(
        replay_id=_replay_id(request.symbol, request.session_id),
        symbol=request.symbol,
        session_id=request.session_id,
        status=status,
        session_readiness=session_readiness,
        steps=[*steps, _completed_step(request, bars, status)],
        decisions=decisions,
        quality_issues=quality_issues,
        bottom_line=bottom_line,
        what_edgelab_tested=(
            "EdgeLab tried to replay one past morning without peeking at later minutes."
        ),
        what_happened="The practice test stopped because the sample did not pass data checks.",
        why_it_might_be_misleading=(
            "Weak data can make a session look clearer or more useful than it really is."
        ),
        next_review_item="Fix or replace the local CSV sample before testing this morning again.",
        evidence_details=_result_evidence_details(request, bars, steps)
        if request.include_evidence_details
        else {},
    )


def _session_loaded_step(
    request: HistoricalReplayRequest, first_bar: IntradayBar, total_bars: int
) -> HistoricalReplayStep:
    return HistoricalReplayStep(
        step_id=f"{_replay_id(request.symbol, request.session_id)}-session-loaded",
        symbol=request.symbol,
        session_id=request.session_id,
        replay_time_utc=first_bar.timestamp,
        step_type=HistoricalReplayStepType.SESSION_LOADED,
        bars_visible_count=0,
        latest_visible_bar_utc=None,
        plain_english_summary="EdgeLab loaded the local historical session for replay.",
        what_edgelab_knew="No bars have been revealed to the replay clock yet.",
        what_changed=f"{total_bars} local historical bar(s) are queued for point-in-time replay.",
        evidence_details={"total_bars_in_local_file": total_bars},
    )


def _visibility_step(
    request: HistoricalReplayRequest,
    current_bar: IntradayBar,
    visible_bars: list[IntradayBar],
) -> HistoricalReplayStep:
    step_type = _step_type_for(current_bar, visible_bars)
    return HistoricalReplayStep(
        step_id=(
            f"{_replay_id(request.symbol, request.session_id)}-"
            f"{len(visible_bars):03d}-{step_type.value}"
        ),
        symbol=request.symbol,
        session_id=request.session_id,
        replay_time_utc=current_bar.timestamp,
        step_type=step_type,
        bars_visible_count=len(visible_bars),
        latest_visible_bar_utc=current_bar.timestamp,
        plain_english_summary=_step_summary(step_type),
        what_edgelab_knew=_knowledge_text(visible_bars),
        what_changed=_changed_text(current_bar, visible_bars),
        evidence_details=_step_evidence_details(visible_bars),
    )


def _event_step(
    request: HistoricalReplayRequest,
    visible_bars: list[IntradayBar],
    event_summary: str,
) -> HistoricalReplayStep:
    current_bar = visible_bars[-1]
    return HistoricalReplayStep(
        step_id=f"{_replay_id(request.symbol, request.session_id)}-{len(visible_bars):03d}-event",
        symbol=request.symbol,
        session_id=request.session_id,
        replay_time_utc=current_bar.timestamp,
        step_type=HistoricalReplayStepType.EVENT_DETECTED,
        bars_visible_count=len(visible_bars),
        latest_visible_bar_utc=current_bar.timestamp,
        plain_english_summary="EdgeLab noticed a measurable replay event.",
        what_edgelab_knew=_knowledge_text(visible_bars),
        what_changed=event_summary,
        evidence_details=_step_evidence_details(visible_bars),
    )


def _setup_step(
    request: HistoricalReplayRequest,
    visible_bars: list[IntradayBar],
    setup: IntradaySetupCandidate,
) -> HistoricalReplayStep:
    current_bar = visible_bars[-1]
    return HistoricalReplayStep(
        step_id=f"{setup.setup_id}-replay-setup-detected",
        symbol=request.symbol,
        session_id=request.session_id,
        replay_time_utc=current_bar.timestamp,
        step_type=HistoricalReplayStepType.SETUP_DETECTED,
        bars_visible_count=len(visible_bars),
        latest_visible_bar_utc=current_bar.timestamp,
        plain_english_summary="EdgeLab marked one setup for research review.",
        what_edgelab_knew=_knowledge_text(visible_bars),
        what_changed=setup.plain_english_summary,
        evidence_details={
            **_step_evidence_details(visible_bars),
            "setup_id": setup.setup_id,
            "signal_bar_timestamp": setup.signal_bar_timestamp,
        },
    )


def _no_trade_step(
    request: HistoricalReplayRequest,
    visible_bars: list[IntradayBar],
    setup: IntradaySetupCandidate,
) -> HistoricalReplayStep:
    current_bar = visible_bars[-1]
    return HistoricalReplayStep(
        step_id=f"{setup.setup_id}-replay-sit-out",
        symbol=request.symbol,
        session_id=request.session_id,
        replay_time_utc=current_bar.timestamp,
        step_type=HistoricalReplayStepType.NO_TRADE_MARKED,
        bars_visible_count=len(visible_bars),
        latest_visible_bar_utc=current_bar.timestamp,
        plain_english_summary="EdgeLab marked this replay as a sit-out study.",
        what_edgelab_knew=_knowledge_text(visible_bars),
        what_changed=setup.plain_english_summary,
        evidence_details=_step_evidence_details(visible_bars),
    )


def _entry_step(
    request: HistoricalReplayRequest,
    visible_bars: list[IntradayBar],
    setup: IntradaySetupCandidate,
    entry_bar: IntradayBar,
) -> HistoricalReplayStep:
    return HistoricalReplayStep(
        step_id=f"{setup.setup_id}-replay-hypothetical-entry",
        symbol=request.symbol,
        session_id=request.session_id,
        replay_time_utc=entry_bar.timestamp,
        step_type=HistoricalReplayStepType.HYPOTHETICAL_ENTRY_MARKED,
        bars_visible_count=len(visible_bars),
        latest_visible_bar_utc=visible_bars[-1].timestamp,
        plain_english_summary="The next visible bar after the signal became available.",
        what_edgelab_knew=_knowledge_text(visible_bars),
        what_changed=("EdgeLab could now mark the hypothetical starting price for research math."),
        evidence_details={
            **_step_evidence_details(visible_bars),
            "setup_id": setup.setup_id,
            "signal_bar_timestamp": setup.signal_bar_timestamp,
            "entry_bar_timestamp": entry_bar.timestamp,
            "entry_bar_open": entry_bar.open,
        },
    )


def _exit_step(
    request: HistoricalReplayRequest,
    visible_bars: list[IntradayBar],
    trade: IntradayHypotheticalTrade,
) -> HistoricalReplayStep:
    return HistoricalReplayStep(
        step_id=f"{trade.trade_id}-replay-exit",
        symbol=request.symbol,
        session_id=request.session_id,
        replay_time_utc=trade.exit_time,
        step_type=HistoricalReplayStepType.HYPOTHETICAL_EXIT_MARKED,
        bars_visible_count=len(visible_bars),
        latest_visible_bar_utc=visible_bars[-1].timestamp,
        plain_english_summary="The replay clock reached the hypothetical result check.",
        what_edgelab_knew=_knowledge_text(visible_bars),
        what_changed=(
            f"The research-only result was {trade.result_label} after the local hold window."
        ),
        evidence_details={
            **_step_evidence_details(visible_bars),
            "trade_id": trade.trade_id,
            "entry_time": trade.entry_time,
            "exit_time": trade.exit_time,
            "net_pnl": trade.net_pnl,
        },
    )


def _final_no_trade_step(
    request: HistoricalReplayRequest, bars: list[IntradayBar]
) -> HistoricalReplayStep:
    return HistoricalReplayStep(
        step_id=f"{_replay_id(request.symbol, request.session_id)}-final-sit-out",
        symbol=request.symbol,
        session_id=request.session_id,
        replay_time_utc=bars[-1].timestamp,
        step_type=HistoricalReplayStepType.NO_TRADE_MARKED,
        bars_visible_count=len(bars),
        latest_visible_bar_utc=bars[-1].timestamp,
        plain_english_summary="EdgeLab finished the replay without marking a setup.",
        what_edgelab_knew=_knowledge_text(bars),
        what_changed="The full local replay did not produce a supported setup.",
        evidence_details=_step_evidence_details(bars),
    )


def _completed_step(
    request: HistoricalReplayRequest,
    bars: list[IntradayBar],
    status: HistoricalReplayStatus,
) -> HistoricalReplayStep:
    return HistoricalReplayStep(
        step_id=f"{_replay_id(request.symbol, request.session_id)}-completed",
        symbol=request.symbol,
        session_id=request.session_id,
        replay_time_utc=bars[-1].timestamp,
        step_type=HistoricalReplayStepType.REPLAY_COMPLETED,
        bars_visible_count=len(bars),
        latest_visible_bar_utc=bars[-1].timestamp,
        plain_english_summary="The local historical replay reached the end of available bars.",
        what_edgelab_knew=_knowledge_text(bars),
        what_changed=f"Replay status is {status.value.replace('_', ' ')}.",
        evidence_details=_step_evidence_details(bars),
    )


def _step_type_for(
    current_bar: IntradayBar, visible_bars: list[IntradayBar]
) -> HistoricalReplayStepType:
    if current_bar.session_type in {IntradaySessionType.OVERNIGHT, IntradaySessionType.PREMARKET}:
        return HistoricalReplayStepType.PREMARKET_CONTEXT
    regular_count = _regular_first_hour_count(visible_bars)
    if regular_count == 1:
        return HistoricalReplayStepType.REGULAR_OPEN
    if 1 < regular_count < OPENING_RANGE_BAR_COUNT:
        return HistoricalReplayStepType.OPENING_RANGE_BUILDING
    if regular_count == OPENING_RANGE_BAR_COUNT:
        return HistoricalReplayStepType.OPENING_RANGE_READY
    return HistoricalReplayStepType.OPENING_RANGE_BUILDING


def _step_summary(step_type: HistoricalReplayStepType) -> str:
    summaries = {
        HistoricalReplayStepType.PREMARKET_CONTEXT: (
            "Pre-open context became visible to the replay clock."
        ),
        HistoricalReplayStepType.REGULAR_OPEN: "The regular open became visible.",
        HistoricalReplayStepType.OPENING_RANGE_BUILDING: ("The opening range was still forming."),
        HistoricalReplayStepType.OPENING_RANGE_READY: (
            "The first five regular-session bars were visible."
        ),
    }
    return summaries.get(step_type, "A new replay bar became visible.")


def _knowledge_text(visible_bars: list[IntradayBar]) -> str:
    regular_bars = _regular_first_hour_bars(visible_bars)
    premarket_bars = [
        bar for bar in visible_bars if bar.session_type == IntradaySessionType.PREMARKET
    ]
    overnight_bars = [
        bar for bar in visible_bars if bar.session_type == IntradaySessionType.OVERNIGHT
    ]
    parts = [f"{len(visible_bars)} bar(s) are visible to the replay clock."]
    if overnight_bars:
        parts.append("Overnight high and low so far are known.")
    if premarket_bars:
        parts.append("Premarket high and low so far are known.")
    if regular_bars:
        parts.append(f"The regular open is known at {regular_bars[0].open:.2f}.")
    if len(regular_bars) >= OPENING_RANGE_BAR_COUNT:
        parts.append("The opening range is now known from the first five visible bars.")
    else:
        parts.append("The opening range is not ready yet.")
    if regular_bars:
        parts.append(
            f"First-hour high and low so far are {max(bar.high for bar in regular_bars):.2f} "
            f"and {min(bar.low for bar in regular_bars):.2f}."
        )
    return " ".join(parts)


def _changed_text(current_bar: IntradayBar, visible_bars: list[IntradayBar]) -> str:
    if current_bar.session_type == IntradaySessionType.REGULAR_FIRST_HOUR:
        regular_count = _regular_first_hour_count(visible_bars)
        return (
            f"A regular-session first-hour bar became visible. "
            f"{regular_count} first-hour bar(s) are now visible."
        )
    return f"A {current_bar.session_type.value.replace('_', ' ')} bar became visible."


def _step_evidence_details(visible_bars: list[IntradayBar]) -> dict[str, object]:
    regular_bars = _regular_first_hour_bars(visible_bars)
    details: dict[str, object] = {
        "visible_bar_timestamps_utc": [bar.timestamp for bar in visible_bars],
        "regular_first_hour_bars_visible": len(regular_bars),
        "opening_range_available": len(regular_bars) >= OPENING_RANGE_BAR_COUNT,
    }
    if regular_bars:
        details["regular_open"] = regular_bars[0].open
        details["first_hour_high_so_far"] = max(bar.high for bar in regular_bars)
        details["first_hour_low_so_far"] = min(bar.low for bar in regular_bars)
    if len(regular_bars) >= OPENING_RANGE_BAR_COUNT:
        opening_bars = regular_bars[:OPENING_RANGE_BAR_COUNT]
        details["opening_range_high"] = max(bar.high for bar in opening_bars)
        details["opening_range_low"] = min(bar.low for bar in opening_bars)
    return details


def _regular_first_hour_bars(bars: list[IntradayBar]) -> list[IntradayBar]:
    return [bar for bar in bars if bar.session_type == IntradaySessionType.REGULAR_FIRST_HOUR]


def _regular_first_hour_count(bars: list[IntradayBar]) -> int:
    return len(_regular_first_hour_bars(bars))


def _select_replay_candidate(
    candidates: list[IntradaySetupCandidate], *, is_final_bar: bool
) -> IntradaySetupCandidate | None:
    if not candidates:
        return None
    candidate = candidates[0]
    if candidate.setup_type != IntradaySetupType.NO_TRADE:
        return candidate
    explicit_sit_out = [
        reason
        for reason in candidate.no_trade_reasons
        if reason.reason_type.value != "unsupported_setup"
    ]
    if explicit_sit_out or is_final_bar:
        return candidate
    return None


def _next_bar_after_signal(
    bars: list[IntradayBar], signal_bar_timestamp: datetime
) -> IntradayBar | None:
    return next((bar for bar in bars if bar.timestamp > signal_bar_timestamp), None)


def _simulate_visible_hypothetical_result(
    bars: list[IntradayBar],
    setup: IntradaySetupCandidate,
    request: HistoricalReplayRequest,
    *,
    point_value: float,
    tick_size: float,
) -> IntradayHypotheticalTrade | None:
    entry_bar = _next_bar_after_signal(bars, setup.signal_bar_timestamp)
    if entry_bar is None:
        return None
    exit_time = entry_bar.timestamp + timedelta(minutes=request.hold_minutes)
    exit_bar = next((bar for bar in bars if bar.timestamp >= exit_time), None)
    if exit_bar is None:
        return None

    slippage = request.slippage_ticks * tick_size
    if setup.direction == IntradaySetupDirection.LONG_CONTEXT:
        entry_price = entry_bar.open + slippage
        exit_price = exit_bar.open - slippage
        gross_points = exit_price - entry_price
    elif setup.direction == IntradaySetupDirection.SHORT_CONTEXT:
        entry_price = entry_bar.open - slippage
        exit_price = exit_bar.open + slippage
        gross_points = entry_price - exit_price
    else:
        return None

    gross_pnl = gross_points * point_value
    estimated_costs = request.commission_per_contract * 2
    net_pnl = gross_pnl - estimated_costs
    result_label = "positive" if net_pnl > 0 else "negative" if net_pnl < 0 else "flat"
    context_label = setup.direction.value.replace("_", "-")

    return IntradayHypotheticalTrade(
        trade_id=f"{setup.setup_id}-historical-replay-hypothetical",
        setup_id=setup.setup_id,
        symbol=setup.symbol,
        direction=setup.direction,
        signal_time=setup.signal_bar_timestamp,
        entry_time=entry_bar.timestamp,
        entry_price=round(entry_price, 4),
        exit_time=exit_bar.timestamp,
        exit_price=round(exit_price, 4),
        contract_count=1,
        gross_points=round(gross_points, 4),
        gross_pnl=round(gross_pnl, 2),
        estimated_costs=round(estimated_costs, 2),
        net_pnl=round(net_pnl, 2),
        result_label=result_label,
        plain_english_reason=(
            f"The {context_label} pattern was checked from the next visible bar open "
            f"for {request.hold_minutes} minutes."
        ),
    )


def _keep_watching_decision(
    request: HistoricalReplayRequest, bar: IntradayBar
) -> HistoricalReplayDecision:
    return HistoricalReplayDecision(
        decision_id=f"{_replay_id(request.symbol, request.session_id)}-keep-watching",
        symbol=request.symbol,
        session_id=request.session_id,
        replay_time_utc=bar.timestamp,
        decision_type=HistoricalReplayDecisionType.KEEP_WATCHING,
        plain_english_summary="EdgeLab kept watching because the morning had just started.",
        why="The opening range was not ready yet.",
        what_would_change_our_mind="Five clean first-hour bars plus a measurable event.",
        what_to_check_next="Wait for the opening range to form.",
    )


def _setup_decision(
    request: HistoricalReplayRequest, setup: IntradaySetupCandidate
) -> HistoricalReplayDecision:
    return HistoricalReplayDecision(
        decision_id=f"{setup.setup_id}-replay-decision",
        symbol=request.symbol,
        session_id=request.session_id,
        replay_time_utc=setup.detected_at,
        decision_type=HistoricalReplayDecisionType.SETUP_MARKED_FOR_RESEARCH,
        plain_english_summary="EdgeLab marked one setup for research review.",
        why=setup.plain_english_summary,
        what_would_change_our_mind=setup.what_would_invalidate_it[0],
        what_to_check_next="Check only later visible bars for the hypothetical result.",
        linked_setup_id=setup.setup_id,
    )


def _sit_out_decision(
    request: HistoricalReplayRequest, setup: IntradaySetupCandidate
) -> HistoricalReplayDecision:
    return HistoricalReplayDecision(
        decision_id=f"{setup.setup_id}-replay-sit-out-decision",
        symbol=request.symbol,
        session_id=request.session_id,
        replay_time_utc=setup.detected_at,
        decision_type=HistoricalReplayDecisionType.SIT_OUT,
        plain_english_summary="EdgeLab marked a sit-out result for this replay.",
        why=setup.plain_english_summary,
        what_would_change_our_mind=setup.what_would_invalidate_it[0],
        what_to_check_next="Review more clean sessions before trusting this behavior.",
        linked_setup_id=setup.setup_id,
    )


def _result_decision(
    request: HistoricalReplayRequest, trade: IntradayHypotheticalTrade
) -> HistoricalReplayDecision:
    return HistoricalReplayDecision(
        decision_id=f"{trade.trade_id}-replay-result-decision",
        symbol=request.symbol,
        session_id=request.session_id,
        replay_time_utc=trade.exit_time,
        decision_type=HistoricalReplayDecisionType.HYPOTHETICAL_RESULT_RECORDED,
        plain_english_summary="EdgeLab recorded the research-only hypothetical result.",
        why=trade.plain_english_reason,
        what_would_change_our_mind=(
            "More sessions with clean replay timing would be needed before trust increases."
        ),
        what_to_check_next="Replay more sessions before building pattern statistics.",
        linked_setup_id=trade.setup_id,
        linked_trade_id=trade.trade_id,
    )


def _insufficient_data_decision(
    request: HistoricalReplayRequest, bar: IntradayBar
) -> HistoricalReplayDecision:
    return HistoricalReplayDecision(
        decision_id=f"{_replay_id(request.symbol, request.session_id)}-insufficient-data",
        symbol=request.symbol,
        session_id=request.session_id,
        replay_time_utc=bar.timestamp,
        decision_type=HistoricalReplayDecisionType.INSUFFICIENT_DATA,
        plain_english_summary="EdgeLab stopped because the replay ran out of later bars.",
        why="The setup could not be followed through the requested hold window.",
        what_would_change_our_mind="More clean bars after the setup would allow completion.",
        what_to_check_next="Add or choose a local session with enough later bars.",
    )


def _final_sit_out_decision(
    request: HistoricalReplayRequest, bar: IntradayBar
) -> HistoricalReplayDecision:
    return HistoricalReplayDecision(
        decision_id=f"{_replay_id(request.symbol, request.session_id)}-final-sit-out-decision",
        symbol=request.symbol,
        session_id=request.session_id,
        replay_time_utc=bar.timestamp,
        decision_type=HistoricalReplayDecisionType.SIT_OUT,
        plain_english_summary="EdgeLab sat out because no supported setup appeared.",
        why="The visible bars never met the simple replay setup rules.",
        what_would_change_our_mind="A cleaner event after the opening range would change this.",
        what_to_check_next="Replay more local sessions and compare sit-out reasons.",
    )


def _step_exists(
    steps: list[HistoricalReplayStep],
    step_type: HistoricalReplayStepType,
    replay_time: datetime,
) -> bool:
    return any(
        step.step_type == step_type and step.replay_time_utc == replay_time for step in steps
    )


def _bottom_line(
    status: HistoricalReplayStatus,
    setups: list[IntradaySetupCandidate],
    trades: list[IntradayHypotheticalTrade],
) -> str:
    if status == HistoricalReplayStatus.INCOMPLETE:
        return "EdgeLab could not trust this morning because the data was incomplete."
    if setups and setups[0].setup_type == IntradaySetupType.NO_TRADE:
        return "EdgeLab would have sat out this morning."
    if trades:
        return "EdgeLab found a practice setup in this past morning."
    if setups:
        return "EdgeLab found a practice setup, but the pretend result could not be finished."
    return "EdgeLab did not see a useful practice setup in this past morning."


def _what_happened(
    setups: list[IntradaySetupCandidate],
    trades: list[IntradayHypotheticalTrade],
    issues: list[HistoricalReplayQualityIssue],
) -> str:
    if issues:
        return "A data limit made the result less trustworthy, so EdgeLab stayed cautious."
    if trades:
        return "A possible practice setup appeared, then later minutes showed the pretend result."
    if setups and setups[0].setup_type == IntradaySetupType.NO_TRADE:
        return "The morning did not look clean enough, so EdgeLab sat out."
    if setups:
        return "A possible practice setup appeared, but the sample ended too soon."
    return "No useful practice setup appeared from the minutes EdgeLab had seen."


def _next_review_item(
    status: HistoricalReplayStatus,
    setups: list[IntradaySetupCandidate],
    trades: list[IntradayHypotheticalTrade],
) -> str:
    if status == HistoricalReplayStatus.INCOMPLETE:
        return "Find a local sample with enough later minutes to finish the pretend result."
    if trades:
        return "Test more past mornings before counting this as a pattern."
    if setups:
        return "Check whether the same practice setup appears in other clean mornings."
    return "Review more mornings to learn whether sitting out is common or sample-specific."


def _result_evidence_details(
    request: HistoricalReplayRequest,
    bars: list[IntradayBar],
    steps: list[HistoricalReplayStep],
) -> dict[str, object]:
    return {
        "no_look_ahead_rule": "Each replay step uses only bars with timestamp <= replay time.",
        "hold_minutes": request.hold_minutes,
        "slippage_ticks": request.slippage_ticks,
        "commission_per_contract": request.commission_per_contract,
        "bar_count": len(bars),
        "step_visibility": [
            {
                "step_id": step.step_id,
                "replay_time_utc": step.replay_time_utc,
                "bars_visible_count": step.bars_visible_count,
                "latest_visible_bar_utc": step.latest_visible_bar_utc,
            }
            for step in steps
        ],
        "benchmark_knowledge": [
            "Prior, overnight, and premarket context can only use bars visible before the open.",
            "The regular open is known after the first regular-session bar is visible.",
            "The opening range is known only after five first-hour bars are visible.",
            "The final hypothetical result is known only after the exit bar is visible.",
        ],
    }


def _point_value(import_result: HistoricalIntradayImportResult) -> float:
    if import_result.instruments:
        return import_result.instruments[0].point_value
    return 1


def _tick_size(import_result: HistoricalIntradayImportResult) -> float:
    if import_result.instruments:
        return import_result.instruments[0].tick_size
    return 0.01


def _replay_id(symbol: str, session_id: str) -> str:
    return f"{symbol.lower()}-{session_id}-historical-replay"
