"""Deterministic intraday event and setup detection."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, time

from edgelab.intraday.benchmarks import calculate_opening_benchmarks
from edgelab.intraday.candles import (
    candle_direction,
    is_indecision_candle,
    is_reversal_like_candle,
    is_strong_down_candle,
    is_strong_up_candle,
)
from edgelab.intraday.schema import (
    CandleDirection,
    IntradayBar,
    IntradayEvent,
    IntradayEventType,
    IntradayQualityIssue,
    IntradaySetupCandidate,
    IntradaySetupDirection,
    IntradaySetupStatus,
    IntradaySetupType,
    NoTradeReason,
    NoTradeReasonType,
    OpeningBenchmarks,
)

LOW_RANGE_THRESHOLD_PCT = 0.15


class IntradaySetupDetector:
    """Detect research-only intraday setup candidates from fixture bars."""

    def detect_events(
        self,
        bars: list[IntradayBar],
        benchmarks: OpeningBenchmarks | None = None,
        paired_bars: list[IntradayBar] | None = None,
    ) -> list[IntradayEvent]:
        """Detect measurable events for one symbol/session."""

        if not bars:
            return []
        sorted_bars = sorted(bars, key=lambda bar: bar.timestamp)
        context = benchmarks or calculate_opening_benchmarks(sorted_bars)
        regular_bars = _regular_first_hour_bars(sorted_bars)
        events: list[IntradayEvent] = []

        events.extend(_gap_events(context, regular_bars))
        events.extend(_level_sweep_events(context, regular_bars))
        events.extend(_opening_range_events(context, regular_bars))
        events.extend(_momentum_events(context, regular_bars))
        events.extend(_no_trade_events(context, regular_bars, events))
        events.extend(_paired_symbol_events(context, paired_bars))
        return sorted(events, key=lambda event: event.timestamp)

    def detect_setups(
        self,
        bars: list[IntradayBar],
        benchmarks: OpeningBenchmarks | None = None,
        *,
        max_one_setup_per_day: bool = True,
        paired_bars: list[IntradayBar] | None = None,
    ) -> list[IntradaySetupCandidate]:
        """Generate setup candidates or a no-trade candidate."""

        if not bars:
            return []
        sorted_bars = sorted(bars, key=lambda bar: bar.timestamp)
        context = benchmarks or calculate_opening_benchmarks(sorted_bars)
        events = self.detect_events(sorted_bars, context, paired_bars=paired_bars)
        regular_bars = _regular_first_hour_bars(sorted_bars)
        signal_bar = _signal_bar(regular_bars)
        if signal_bar is None:
            return [
                _no_trade_candidate(
                    context,
                    events,
                    [
                        NoTradeReason(
                            reason_type=NoTradeReasonType.INSUFFICIENT_DATA,
                            message=(
                                "EdgeLab cannot evaluate the first hour without "
                                "regular-session bars."
                            ),
                        )
                    ],
                    "No setup was selected because the synthetic fixture lacks first-hour bars.",
                )
            ]

        no_trade_reasons = _no_trade_reasons(events)
        if no_trade_reasons:
            return [
                _no_trade_candidate(
                    context,
                    events,
                    no_trade_reasons,
                    (
                        "EdgeLab selected a sit-out result because the synthetic first "
                        "hour is unclear."
                    ),
                )
            ]

        candidates: list[IntradaySetupCandidate] = []
        candidate_specs = [
            (
                IntradayEventType.FAILED_OPENING_PUSH,
                IntradaySetupType.FAILED_OPENING_PUSH,
                IntradaySetupDirection.SHORT_CONTEXT,
                "A failed opening push appeared in the synthetic first hour.",
            ),
            (
                IntradayEventType.FAILED_OPENING_SELLOFF,
                IntradaySetupType.FAILED_OPENING_SELLOFF,
                IntradaySetupDirection.LONG_CONTEXT,
                "A failed opening selloff appeared in the synthetic first hour.",
            ),
            (
                IntradayEventType.OPENING_RANGE_FAILURE,
                IntradaySetupType.OPENING_RANGE_FAILURE,
                None,
                "An opening range failure appeared in the synthetic first hour.",
            ),
            (
                IntradayEventType.OPENING_GAP_UP,
                IntradaySetupType.GAP_FADE,
                IntradaySetupDirection.SHORT_CONTEXT,
                "A gap fade study appeared after the synthetic open moved back toward references.",
            ),
            (
                IntradayEventType.OPENING_RANGE_BREAKOUT,
                IntradaySetupType.OPENING_RANGE_BREAKOUT,
                None,
                "An opening range breakout appeared in the synthetic first hour.",
            ),
        ]
        for event_type, setup_type, default_direction, summary in candidate_specs:
            gap_fade_event = _gap_fade_signal(context, regular_bars)
            if setup_type == IntradaySetupType.GAP_FADE and gap_fade_event is not None:
                candidates.append(
                    _setup_candidate(
                        context,
                        gap_fade_event,
                        events,
                        setup_type,
                        gap_fade_event.direction or IntradaySetupDirection.NO_TRADE_CONTEXT,
                        "A gap fade study appeared in the synthetic first hour.",
                    )
                )
                if max_one_setup_per_day:
                    break
                continue
            matching_event = _first_event(events, event_type)
            if matching_event is None:
                continue
            if setup_type == IntradaySetupType.GAP_FADE and not _has_gap_fade_confirmation(events):
                continue
            direction = default_direction or matching_event.direction
            if direction is None:
                direction = IntradaySetupDirection.NO_TRADE_CONTEXT
            candidates.append(
                _setup_candidate(context, matching_event, events, setup_type, direction, summary)
            )
            if max_one_setup_per_day:
                break

        if candidates:
            return candidates
        return [
            _no_trade_candidate(
                context,
                events,
                [
                    NoTradeReason(
                        reason_type=NoTradeReasonType.UNSUPPORTED_SETUP,
                        message=(
                            "EdgeLab found measurable events, but none met the simple Phase 7X "
                            "setup rules."
                        ),
                    )
                ],
                "EdgeLab did not force a setup from this synthetic first hour.",
            )
        ]


def compare_paired_symbol_context(
    primary_bars: list[IntradayBar], reference_bars: list[IntradayBar] | None
) -> tuple[list[IntradayEvent], list[IntradayQualityIssue]]:
    """Optionally compare one fixture symbol against another."""

    if not primary_bars:
        return [], [
            IntradayQualityIssue(
                code="missing_primary_pair_data",
                message="Paired comparison needs primary intraday bars.",
            )
        ]
    if not reference_bars:
        return [], [
            IntradayQualityIssue(
                code="paired_symbol_data_unavailable",
                message="No paired symbol fixture was provided, so comparison was skipped.",
                symbol=primary_bars[0].symbol,
                session_id=primary_bars[0].session_id,
            )
        ]
    primary_context = calculate_opening_benchmarks(primary_bars)
    return _paired_symbol_events(primary_context, reference_bars), []


def _gap_events(context: OpeningBenchmarks, regular_bars: list[IntradayBar]) -> list[IntradayEvent]:
    if context.opening_gap_pct is None or not regular_bars:
        return []
    if context.opening_gap_pct >= 0.25:
        return [
            _event(
                IntradayEventType.OPENING_GAP_UP,
                context,
                regular_bars[0],
                None,
                context.regular_open,
                "regular open",
                "The synthetic session opened above the prior reference level.",
            )
        ]
    if context.opening_gap_pct <= -0.25:
        return [
            _event(
                IntradayEventType.OPENING_GAP_DOWN,
                context,
                regular_bars[0],
                None,
                context.regular_open,
                "regular open",
                "The synthetic session opened below the prior reference level.",
            )
        ]
    return []


def _level_sweep_events(
    context: OpeningBenchmarks, regular_bars: list[IntradayBar]
) -> list[IntradayEvent]:
    events: list[IntradayEvent] = []
    for bar in regular_bars:
        if context.overnight_high is not None and bar.high > context.overnight_high > bar.close:
            events.append(
                _event(
                    IntradayEventType.OVERNIGHT_HIGH_SWEEP,
                    context,
                    bar,
                    IntradaySetupDirection.SHORT_CONTEXT,
                    context.overnight_high,
                    "overnight high",
                    "Price moved above the synthetic overnight high but did not hold above it.",
                )
            )
            break
    for bar in regular_bars:
        if context.overnight_low is not None and bar.low < context.overnight_low < bar.close:
            events.append(
                _event(
                    IntradayEventType.OVERNIGHT_LOW_SWEEP,
                    context,
                    bar,
                    IntradaySetupDirection.LONG_CONTEXT,
                    context.overnight_low,
                    "overnight low",
                    "Price moved below the synthetic overnight low but did not hold below it.",
                )
            )
            break
    return events


def _opening_range_events(
    context: OpeningBenchmarks, regular_bars: list[IntradayBar]
) -> list[IntradayEvent]:
    if context.opening_range_high is None or context.opening_range_low is None:
        return []
    opening_bars = regular_bars[:5]
    post_range_bars = regular_bars[5:]
    events: list[IntradayEvent] = []

    failed_push_bar = _first_failed_push_bar(context, post_range_bars or opening_bars)
    if failed_push_bar is not None:
        events.append(
            _event(
                IntradayEventType.FAILED_OPENING_PUSH,
                context,
                failed_push_bar,
                IntradaySetupDirection.SHORT_CONTEXT,
                context.opening_range_high,
                "opening range high",
                "The synthetic opening push moved above a reference level but faded back.",
            )
        )

    failed_selloff_bar = _first_failed_selloff_bar(context, post_range_bars or opening_bars)
    if failed_selloff_bar is not None:
        events.append(
            _event(
                IntradayEventType.FAILED_OPENING_SELLOFF,
                context,
                failed_selloff_bar,
                IntradaySetupDirection.LONG_CONTEXT,
                context.opening_range_low,
                "opening range low",
                "The synthetic opening selloff moved below a reference level but recovered.",
            )
        )

    breakout_events = _breakout_events(context, post_range_bars)
    events.extend(breakout_events)
    failure_event = _opening_range_failure_event(context, post_range_bars)
    if failure_event is not None:
        events.append(failure_event)
    return events


def _momentum_events(
    context: OpeningBenchmarks, regular_bars: list[IntradayBar]
) -> list[IntradayEvent]:
    events: list[IntradayEvent] = []
    post_range_bars = regular_bars[5:]
    for previous, current in zip(post_range_bars, post_range_bars[1:], strict=False):
        if is_strong_up_candle(previous) and is_strong_up_candle(current):
            events.append(
                _event(
                    IntradayEventType.MOMENTUM_CONTINUATION,
                    context,
                    current,
                    IntradaySetupDirection.LONG_CONTEXT,
                    current.close,
                    "two strong up candles",
                    "Two strong same-direction synthetic candles appeared after the opening range.",
                )
            )
            break
        if is_strong_down_candle(previous) and is_strong_down_candle(current):
            events.append(
                _event(
                    IntradayEventType.MOMENTUM_CONTINUATION,
                    context,
                    current,
                    IntradaySetupDirection.SHORT_CONTEXT,
                    current.close,
                    "two strong down candles",
                    "Two strong same-direction synthetic candles appeared after the opening range.",
                )
            )
            break

    for previous, current in zip(post_range_bars, post_range_bars[1:], strict=False):
        near_high = context.first_hour_high is not None and previous.high >= context.first_hour_high
        near_low = context.first_hour_low is not None and previous.low <= context.first_hour_low
        if (is_strong_up_candle(previous) and near_high) and (
            is_reversal_like_candle(current) or is_indecision_candle(current)
        ):
            events.append(
                _event(
                    IntradayEventType.MOMENTUM_EXHAUSTION,
                    context,
                    current,
                    IntradaySetupDirection.SHORT_CONTEXT,
                    current.close,
                    "first-hour high",
                    "Momentum paused near a synthetic first-hour extreme.",
                )
            )
            break
        if (is_strong_down_candle(previous) and near_low) and (
            is_reversal_like_candle(current) or is_indecision_candle(current)
        ):
            events.append(
                _event(
                    IntradayEventType.MOMENTUM_EXHAUSTION,
                    context,
                    current,
                    IntradaySetupDirection.LONG_CONTEXT,
                    current.close,
                    "first-hour low",
                    "Momentum paused near a synthetic first-hour extreme.",
                )
            )
            break
    return events


def _no_trade_events(
    context: OpeningBenchmarks,
    regular_bars: list[IntradayBar],
    detected_events: Sequence[IntradayEvent],
) -> list[IntradayEvent]:
    events: list[IntradayEvent] = []
    if _is_choppy_open(context, regular_bars):
        events.append(
            _event(
                IntradayEventType.NO_TRADE_CHOPPY_OPEN,
                context,
                regular_bars[min(14, len(regular_bars) - 1)],
                IntradaySetupDirection.NO_TRADE_CONTEXT,
                None,
                "choppy first 15 minutes",
                "The synthetic first hour changed direction repeatedly without a clean break.",
            )
        )
    if _is_low_range_open(context):
        bar = regular_bars[4] if len(regular_bars) >= 5 else regular_bars[-1]
        events.append(
            _event(
                IntradayEventType.NO_TRADE_LOW_RANGE,
                context,
                bar,
                IntradaySetupDirection.NO_TRADE_CONTEXT,
                None,
                "small opening range",
                "The synthetic opening range was too narrow for this simple rule set.",
            )
        )
    directions = {event.direction for event in detected_events if event.direction is not None}
    if {
        IntradaySetupDirection.LONG_CONTEXT,
        IntradaySetupDirection.SHORT_CONTEXT,
    }.issubset(directions):
        bar = regular_bars[min(5, len(regular_bars) - 1)]
        events.append(
            _event(
                IntradayEventType.NO_TRADE_CONFLICTING_SIGNALS,
                context,
                bar,
                IntradaySetupDirection.NO_TRADE_CONTEXT,
                None,
                "conflicting contexts",
                "The synthetic first hour showed both long-context and short-context events.",
            )
        )
    return events


def _paired_symbol_events(
    context: OpeningBenchmarks, paired_bars: list[IntradayBar] | None
) -> list[IntradayEvent]:
    if not paired_bars:
        return []
    paired_context = calculate_opening_benchmarks(paired_bars)
    primary_return = _minutes_return(context)
    paired_return = _minutes_return(paired_context)
    if primary_return is None or paired_return is None:
        return []
    regular_bars = _regular_first_hour_bars(paired_bars)
    timestamp_bar = regular_bars[0] if regular_bars else paired_bars[0]
    difference = primary_return - paired_return
    if abs(difference) < 0.15:
        return []
    if difference > 0:
        event_type = IntradayEventType.PAIRED_SYMBOL_STRONGER_THAN_REFERENCE
        summary = "The primary synthetic symbol was stronger than the paired reference."
        direction = IntradaySetupDirection.LONG_CONTEXT
    else:
        event_type = IntradayEventType.PAIRED_SYMBOL_WEAKER_THAN_REFERENCE
        summary = "The primary synthetic symbol was weaker than the paired reference."
        direction = IntradaySetupDirection.SHORT_CONTEXT
    return [
        IntradayEvent(
            event_type=event_type,
            symbol=context.symbol,
            session_id=context.session_id,
            timestamp=timestamp_bar.timestamp,
            direction=direction,
            related_price=abs(difference),
            related_level_name="paired first-window return difference",
            plain_english_summary=summary,
        )
    ]


def _first_failed_push_bar(
    context: OpeningBenchmarks, bars: list[IntradayBar]
) -> IntradayBar | None:
    if context.opening_range_high is None:
        return None
    reference = max(
        level for level in [context.opening_range_high, context.premarket_high] if level is not None
    )
    for bar in bars:
        if bar.high > reference and bar.close < context.opening_range_high:
            return bar
    return None


def _first_failed_selloff_bar(
    context: OpeningBenchmarks, bars: list[IntradayBar]
) -> IntradayBar | None:
    if context.opening_range_low is None:
        return None
    reference = min(level for level in [context.opening_range_low, context.premarket_low] if level)
    for bar in bars:
        if bar.low < reference and bar.close > context.opening_range_low:
            return bar
    return None


def _breakout_events(
    context: OpeningBenchmarks, post_range_bars: list[IntradayBar]
) -> list[IntradayEvent]:
    if context.opening_range_high is None or context.opening_range_low is None:
        return []
    for bar in post_range_bars:
        if bar.close > context.opening_range_high and is_strong_up_candle(bar):
            return [
                _event(
                    IntradayEventType.OPENING_RANGE_BREAKOUT,
                    context,
                    bar,
                    IntradaySetupDirection.LONG_CONTEXT,
                    context.opening_range_high,
                    "opening range high",
                    "The synthetic close moved beyond the opening range on a strong candle.",
                )
            ]
        if bar.close < context.opening_range_low and is_strong_down_candle(bar):
            return [
                _event(
                    IntradayEventType.OPENING_RANGE_BREAKOUT,
                    context,
                    bar,
                    IntradaySetupDirection.SHORT_CONTEXT,
                    context.opening_range_low,
                    "opening range low",
                    "The synthetic close moved beyond the opening range on a strong candle.",
                )
            ]
    return []


def _opening_range_failure_event(
    context: OpeningBenchmarks, post_range_bars: list[IntradayBar]
) -> IntradayEvent | None:
    if context.opening_range_high is None or context.opening_range_low is None:
        return None
    for index, bar in enumerate(post_range_bars):
        if bar.high > context.opening_range_high:
            for followup in post_range_bars[index + 1 : index + 4]:
                if followup.close < context.opening_range_high:
                    return _event(
                        IntradayEventType.OPENING_RANGE_FAILURE,
                        context,
                        followup,
                        IntradaySetupDirection.SHORT_CONTEXT,
                        context.opening_range_high,
                        "opening range high",
                        "A synthetic move beyond the opening range did not hold.",
                    )
        if bar.low < context.opening_range_low:
            for followup in post_range_bars[index + 1 : index + 4]:
                if followup.close > context.opening_range_low:
                    return _event(
                        IntradayEventType.OPENING_RANGE_FAILURE,
                        context,
                        followup,
                        IntradaySetupDirection.LONG_CONTEXT,
                        context.opening_range_low,
                        "opening range low",
                        "A synthetic move beyond the opening range did not hold.",
                    )
    return None


def _is_choppy_open(context: OpeningBenchmarks, regular_bars: list[IntradayBar]) -> bool:
    if context.opening_range_high is None or context.opening_range_low is None:
        return False
    first_15 = regular_bars[:15]
    directions = [
        candle_direction(bar) for bar in first_15 if candle_direction(bar) != CandleDirection.FLAT
    ]
    direction_changes = sum(
        1
        for previous, current in zip(directions, directions[1:], strict=False)
        if previous != current
    )
    sustained_break = any(
        bar.close > context.opening_range_high or bar.close < context.opening_range_low
        for bar in regular_bars[5:15]
    )
    return len(first_15) >= 15 and direction_changes >= 5 and not sustained_break


def _is_low_range_open(context: OpeningBenchmarks) -> bool:
    if (
        context.opening_range_high is None
        or context.opening_range_low is None
        or context.regular_open is None
    ):
        return False
    width_pct = (
        (context.opening_range_high - context.opening_range_low) / context.regular_open * 100
    )
    return width_pct < LOW_RANGE_THRESHOLD_PCT


def _no_trade_reasons(events: list[IntradayEvent]) -> list[NoTradeReason]:
    reasons: list[NoTradeReason] = []
    for event in events:
        if event.event_type == IntradayEventType.NO_TRADE_CHOPPY_OPEN:
            reasons.append(
                NoTradeReason(
                    reason_type=NoTradeReasonType.CHOPPY_OPEN,
                    message="The synthetic open was choppy, so EdgeLab would sit out.",
                )
            )
        elif event.event_type == IntradayEventType.NO_TRADE_LOW_RANGE:
            reasons.append(
                NoTradeReason(
                    reason_type=NoTradeReasonType.LOW_RANGE,
                    message="The synthetic opening range was too small for this rule set.",
                )
            )
        elif event.event_type == IntradayEventType.NO_TRADE_CONFLICTING_SIGNALS:
            reasons.append(
                NoTradeReason(
                    reason_type=NoTradeReasonType.CONFLICTING_SIGNALS,
                    message="The synthetic first hour had conflicting context signals.",
                )
            )
    return reasons


def _setup_candidate(
    context: OpeningBenchmarks,
    signal_event: IntradayEvent,
    events: list[IntradayEvent],
    setup_type: IntradaySetupType,
    direction: IntradaySetupDirection,
    summary: str,
) -> IntradaySetupCandidate:
    label = direction.value.replace("_", "-")
    return IntradaySetupCandidate(
        setup_id=f"{context.symbol.lower()}-{context.session_id}-{setup_type.value}",
        symbol=context.symbol,
        session_id=context.session_id,
        session_date=context.session_date,
        setup_type=setup_type,
        direction=direction,
        status=IntradaySetupStatus.DETECTED,
        detected_at=signal_event.timestamp,
        signal_bar_timestamp=signal_event.timestamp,
        benchmark_context=context,
        supporting_events=events,
        plain_english_summary=f"{summary} This is a {label} pattern for research only.",
        why_it_appeared=[signal_event.plain_english_summary],
        what_would_invalidate_it=[
            (
                "The pattern would weaken if the next bars stop respecting the measured "
                "reference levels."
            )
        ],
        what_is_missing=[
            (
                "Real historical one-minute data, broader samples, and out-of-sample "
                "replay are missing."
            )
        ],
        why_edgelab_might_sit_out=[
            "Synthetic fixture behavior is not enough to trust the pattern beyond workflow testing."
        ],
    )


def _no_trade_candidate(
    context: OpeningBenchmarks,
    events: list[IntradayEvent],
    reasons: list[NoTradeReason],
    summary: str,
) -> IntradaySetupCandidate:
    timestamp = events[0].timestamp if events else _fallback_timestamp(context)
    return IntradaySetupCandidate(
        setup_id=f"{context.symbol.lower()}-{context.session_id}-no-trade",
        symbol=context.symbol,
        session_id=context.session_id,
        session_date=context.session_date,
        setup_type=IntradaySetupType.NO_TRADE,
        direction=IntradaySetupDirection.NO_TRADE_CONTEXT,
        status=IntradaySetupStatus.SKIPPED,
        detected_at=timestamp,
        signal_bar_timestamp=timestamp,
        benchmark_context=context,
        supporting_events=events,
        no_trade_reasons=reasons,
        plain_english_summary=summary,
        why_it_appeared=[reason.message for reason in reasons],
        what_would_invalidate_it=[
            (
                "A cleaner fixture with directional follow-through and fewer conflicts "
                "would change this."
            )
        ],
        what_is_missing=[
            "A real historical sample is missing, so this sit-out is a workflow result only."
        ],
        why_edgelab_might_sit_out=[
            "Doing nothing is valid when measured conditions are unclear or unsupported."
        ],
    )


def _event(
    event_type: IntradayEventType,
    context: OpeningBenchmarks,
    bar: IntradayBar,
    direction: IntradaySetupDirection | None,
    related_price: float | None,
    related_level_name: str,
    summary: str,
) -> IntradayEvent:
    return IntradayEvent(
        event_type=event_type,
        symbol=context.symbol,
        session_id=context.session_id,
        timestamp=bar.timestamp,
        direction=direction,
        related_price=related_price,
        related_level_name=related_level_name,
        plain_english_summary=summary,
    )


def _regular_first_hour_bars(bars: list[IntradayBar]) -> list[IntradayBar]:
    return [bar for bar in bars if bar.session_type.value == "regular_first_hour"]


def _signal_bar(bars: list[IntradayBar]) -> IntradayBar | None:
    return bars[0] if bars else None


def _first_event(
    events: list[IntradayEvent], event_type: IntradayEventType
) -> IntradayEvent | None:
    return next((event for event in events if event.event_type == event_type), None)


def _has_gap_fade_confirmation(events: list[IntradayEvent]) -> bool:
    event_types = {event.event_type for event in events}
    return bool(
        {
            IntradayEventType.FAILED_OPENING_PUSH,
            IntradayEventType.OPENING_RANGE_FAILURE,
            IntradayEventType.MOMENTUM_EXHAUSTION,
        }
        & event_types
    )


def _gap_fade_signal(
    context: OpeningBenchmarks, regular_bars: list[IntradayBar]
) -> IntradayEvent | None:
    if context.opening_gap_pct is None or context.regular_open is None:
        return None
    if context.opening_gap_pct >= 0.25:
        for bar in regular_bars[5:]:
            if bar.close < context.regular_open:
                return _event(
                    IntradayEventType.OPENING_GAP_UP,
                    context,
                    bar,
                    IntradaySetupDirection.SHORT_CONTEXT,
                    context.regular_open,
                    "regular open",
                    "The synthetic gap up moved back below the opening reference.",
                )
    if context.opening_gap_pct <= -0.25:
        for bar in regular_bars[5:]:
            if bar.close > context.regular_open:
                return _event(
                    IntradayEventType.OPENING_GAP_DOWN,
                    context,
                    bar,
                    IntradaySetupDirection.LONG_CONTEXT,
                    context.regular_open,
                    "regular open",
                    "The synthetic gap down moved back above the opening reference.",
                )
    return None


def _fallback_timestamp(context: OpeningBenchmarks) -> datetime:
    if context.quality_issues and context.quality_issues[0].timestamp is not None:
        return context.quality_issues[0].timestamp
    return datetime.combine(context.session_date, time(0, 0))


def _minutes_return(context: OpeningBenchmarks) -> float | None:
    if (
        context.regular_open is None
        or context.first_hour_high is None
        or context.first_hour_low is None
    ):
        return None
    midpoint = (context.first_hour_high + context.first_hour_low) / 2
    return (midpoint - context.regular_open) / context.regular_open * 100
