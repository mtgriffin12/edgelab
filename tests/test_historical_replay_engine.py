from datetime import timedelta

from edgelab.intraday.replay import HistoricalIntradayReplayEngine
from edgelab.intraday.replay_schema import (
    HistoricalReplayDecisionType,
    HistoricalReplayRequest,
    HistoricalReplayStatus,
    HistoricalReplayStepType,
)
from edgelab.intraday.schema import IntradaySetupType


def replay(symbol: str, session_id: str, **kwargs):
    request = HistoricalReplayRequest(symbol=symbol, session_id=session_id, **kwargs)
    return HistoricalIntradayReplayEngine().replay(request)


def test_replay_loads_historical_session_and_preserves_research_only_status() -> None:
    result = replay("RPLAY", "replay-breakout-complete")

    assert result.status == HistoricalReplayStatus.COMPLETED
    assert result.research_only_status == "Research only"
    assert result.real_money_status == "Not allowed"
    assert result.setup_candidates
    assert result.hypothetical_trades


def test_replay_blocks_or_marks_incomplete_sessions_by_readiness() -> None:
    blocked = replay("BADOHLC", "bad-invalid-ohlc")
    incomplete = replay("INCOMPLETE", "incomplete-first-hour")

    assert blocked.status == HistoricalReplayStatus.BLOCKED_BY_DATA_QUALITY
    assert blocked.decisions[0].decision_type == HistoricalReplayDecisionType.BLOCKED_BY_QUALITY
    assert incomplete.status == HistoricalReplayStatus.INCOMPLETE
    assert incomplete.decisions[0].decision_type == HistoricalReplayDecisionType.INSUFFICIENT_DATA


def test_replay_steps_are_time_ordered_and_do_not_see_future_bars() -> None:
    result = replay("RPLAY", "replay-breakout-complete")
    replay_times = [step.replay_time_utc for step in result.steps]

    assert replay_times == sorted(replay_times)
    for step in result.steps:
        if step.latest_visible_bar_utc is not None:
            assert step.latest_visible_bar_utc <= step.replay_time_utc
        visible_timestamps = step.evidence_details.get("visible_bar_timestamps_utc", [])
        assert all(timestamp <= step.replay_time_utc for timestamp in visible_timestamps)


def test_setup_detection_waits_until_signal_bar_is_visible() -> None:
    result = replay("RPLAY", "replay-breakout-complete")
    setup_step = next(
        step for step in result.steps if step.step_type == HistoricalReplayStepType.SETUP_DETECTED
    )
    setup = result.setup_candidates[0]

    assert setup_step.bars_visible_count == 6
    assert setup.signal_bar_timestamp <= setup_step.replay_time_utc
    assert setup.setup_type == IntradaySetupType.OPENING_RANGE_BREAKOUT


def test_no_same_bar_entry_and_exit_waits_for_visible_exit_bar() -> None:
    result = replay("RPLAY", "replay-breakout-complete")
    setup = result.setup_candidates[0]
    trade = result.hypothetical_trades[0]
    exit_step = next(
        step
        for step in result.steps
        if step.step_type == HistoricalReplayStepType.HYPOTHETICAL_EXIT_MARKED
    )

    assert trade.entry_time > setup.signal_bar_timestamp
    assert trade.entry_time == setup.signal_bar_timestamp + timedelta(minutes=1)
    assert exit_step.replay_time_utc == trade.exit_time
    assert exit_step.latest_visible_bar_utc == trade.exit_time


def test_no_trade_replay_produces_sit_out_decision() -> None:
    result = replay("SPY", "spy-2024-01-02-historical")

    assert result.status == HistoricalReplayStatus.COMPLETED
    assert result.setup_candidates[0].setup_type == IntradaySetupType.NO_TRADE
    assert any(
        decision.decision_type == HistoricalReplayDecisionType.SIT_OUT
        for decision in result.decisions
    )
    assert result.hypothetical_trades == []


def test_missing_next_entry_bar_returns_quality_issue() -> None:
    result = replay("RPLAYX", "replay-breakout-missing-entry")

    assert result.status == HistoricalReplayStatus.INCOMPLETE
    assert any(issue.code == "insufficient_entry_data" for issue in result.quality_issues)
    assert result.hypothetical_trades == []


def test_insufficient_exit_data_returns_quality_issue() -> None:
    result = replay("RPLAY", "replay-breakout-complete", hold_minutes=60)

    assert result.status == HistoricalReplayStatus.INCOMPLETE
    assert any(issue.code == "insufficient_exit_data" for issue in result.quality_issues)
    assert result.hypothetical_trades == []


def test_benchmark_knowledge_is_revealed_in_order() -> None:
    result = replay("RPLAY", "replay-breakout-complete")
    building_steps = [
        step
        for step in result.steps
        if step.step_type == HistoricalReplayStepType.OPENING_RANGE_BUILDING
    ]
    ready_step = next(
        step
        for step in result.steps
        if step.step_type == HistoricalReplayStepType.OPENING_RANGE_READY
    )

    assert building_steps
    assert all(
        step.evidence_details.get("opening_range_available") is False for step in building_steps[:3]
    )
    assert ready_step.evidence_details["opening_range_available"] is True
    assert "opening_range_high" in ready_step.evidence_details


def test_premarket_context_is_available_before_open_when_present() -> None:
    result = replay("QQQ", "qqq-2024-01-02-historical")

    assert any(
        step.step_type == HistoricalReplayStepType.PREMARKET_CONTEXT for step in result.steps
    )
    assert "Premarket high and low so far are known" in " ".join(
        step.what_edgelab_knew for step in result.steps
    )
