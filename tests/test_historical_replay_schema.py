from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from edgelab.intraday.historical_schema import HistoricalIntradayReadiness
from edgelab.intraday.replay_schema import (
    HistoricalReplayDecision,
    HistoricalReplayDecisionType,
    HistoricalReplayRequest,
    HistoricalReplayResult,
    HistoricalReplayStatus,
    HistoricalReplayStep,
    HistoricalReplayStepType,
)


def test_replay_request_validation_and_defaults() -> None:
    request = HistoricalReplayRequest(symbol=" spy ", session_id=" session-1 ")

    assert request.symbol == "SPY"
    assert request.session_id == "session-1"
    assert request.hold_minutes == 5
    assert request.slippage_ticks == 1
    assert request.commission_per_contract == 0
    assert request.max_one_setup_per_day is True


def test_replay_request_rejects_invalid_assumptions() -> None:
    with pytest.raises(ValidationError):
        HistoricalReplayRequest(symbol="SPY", session_id="session-1", hold_minutes=0)

    with pytest.raises(ValidationError):
        HistoricalReplayRequest(symbol="SPY", session_id="session-1", slippage_ticks=-1)

    with pytest.raises(ValidationError):
        HistoricalReplayRequest(symbol="SPY", session_id="session-1", commission_per_contract=-1)


def test_replay_result_defaults_to_research_only_and_not_allowed() -> None:
    result = HistoricalReplayResult(
        replay_id="spy-session-replay",
        symbol="SPY",
        session_id="session-1",
        status=HistoricalReplayStatus.COMPLETED,
        session_readiness=HistoricalIntradayReadiness.READY_FOR_REPLAY,
        bottom_line="EdgeLab replayed the morning and did not find a supported setup.",
        what_edgelab_tested="One local historical morning was replayed bar by bar.",
        what_happened="No supported setup appeared from the visible bars.",
        why_it_might_be_misleading="One replay is only one example.",
        next_review_item="Replay more local sessions before building pattern statistics.",
    )

    assert result.symbol == "SPY"
    assert result.research_only_status == "Research only"
    assert result.real_money_status == "Not allowed"


def test_replay_models_reject_action_instructions() -> None:
    with pytest.raises(ValidationError, match="action instructions"):
        HistoricalReplayResult(
            replay_id="spy-session-replay",
            symbol="SPY",
            session_id="session-1",
            status=HistoricalReplayStatus.COMPLETED,
            session_readiness=HistoricalIntradayReadiness.READY_FOR_REPLAY,
            bottom_line="buy now",
            what_edgelab_tested="One local historical morning was replayed bar by bar.",
            what_happened="No supported setup appeared from the visible bars.",
            why_it_might_be_misleading="One replay is only one example.",
            next_review_item="Replay more local sessions before building pattern statistics.",
        )

    with pytest.raises(ValidationError, match="action instructions"):
        HistoricalReplayDecision(
            decision_id="bad-decision",
            symbol="SPY",
            session_id="session-1",
            replay_time_utc=datetime(2024, 1, 2, 14, 30, tzinfo=UTC),
            decision_type=HistoricalReplayDecisionType.SETUP_MARKED_FOR_RESEARCH,
            plain_english_summary="go short",
            why="Bad copy.",
            what_would_change_our_mind="Better copy.",
            what_to_check_next="Review copy.",
        )


def test_neutral_long_and_short_context_language_is_allowed() -> None:
    step = HistoricalReplayStep(
        step_id="short-context-step",
        symbol="SPY",
        session_id="session-1",
        replay_time_utc=datetime(2024, 1, 2, 14, 30, tzinfo=UTC),
        step_type=HistoricalReplayStepType.SETUP_DETECTED,
        bars_visible_count=1,
        latest_visible_bar_utc=datetime(2024, 1, 2, 14, 30, tzinfo=UTC),
        plain_english_summary="A short-context pattern was marked for research.",
        what_edgelab_knew="A long-context label would also be descriptive only.",
        what_changed="No action instruction was produced.",
    )

    assert step.real_money_status == "Not allowed"
