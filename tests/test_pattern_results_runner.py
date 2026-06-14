from pathlib import Path

from edgelab.intraday.historical_provider import LocalCSVHistoricalIntradayProvider
from edgelab.intraday.pattern_results import MultiSessionPatternRunner
from edgelab.intraday.pattern_results_schema import (
    MultiSessionReplayRequest,
    PatternResultClassification,
)
from edgelab.intraday.replay import HistoricalIntradayReplayEngine
from edgelab.intraday.replay_schema import HistoricalReplayRequest, HistoricalReplayResult


class CountingReplayEngine:
    def __init__(self) -> None:
        self.inner = HistoricalIntradayReplayEngine()
        self.requests: list[HistoricalReplayRequest] = []

    def replay(self, request: HistoricalReplayRequest) -> HistoricalReplayResult:
        self.requests.append(request)
        return self.inner.replay(request)


def test_multi_session_runner_reuses_single_session_replay_engine() -> None:
    replay_engine = CountingReplayEngine()
    runner = MultiSessionPatternRunner(replay_engine=replay_engine)

    summary = runner.run()

    assert summary.sessions_found > 0
    assert summary.sessions_tested == len(replay_engine.requests)
    assert all(isinstance(request, HistoricalReplayRequest) for request in replay_engine.requests)


def test_multi_session_runner_aggregates_local_sessions_and_tiny_fixture_warning() -> None:
    summary = MultiSessionPatternRunner().run()

    assert summary.research_only_status == "Research only"
    assert summary.real_money_status == "Not allowed"
    assert summary.sessions_found == summary.sessions_tested
    assert summary.usable_sessions < summary.request.minimum_useful_sessions
    assert "Not enough examples yet" in summary.bottom_line
    assert summary.classification in {
        PatternResultClassification.NOT_ENOUGH_EXAMPLES,
        PatternResultClassification.BLOCKED_BY_DATA_QUALITY,
    }
    assert summary.evidence_details["minimum_useful_sessions"] == 30
    assert summary.session_outcomes


def test_multi_session_runner_supports_symbol_filter() -> None:
    summary = MultiSessionPatternRunner().run(MultiSessionReplayRequest(symbol="RPLAY"))

    assert summary.symbol == "RPLAY"
    assert summary.sessions_found > 0
    assert all(outcome.symbol == "RPLAY" for outcome in summary.session_outcomes)


def test_multi_session_runner_handles_zero_sessions(tmp_path: Path) -> None:
    provider = LocalCSVHistoricalIntradayProvider(data_dir=tmp_path)
    runner = MultiSessionPatternRunner(provider=provider)

    summary = runner.run()

    assert summary.sessions_found == 0
    assert summary.sessions_tested == 0
    assert summary.classification == PatternResultClassification.NOT_ENOUGH_EXAMPLES
    assert "Not enough examples yet" in summary.bottom_line


def test_multi_session_runner_summarizes_data_skips_and_no_trade_reasons() -> None:
    summary = MultiSessionPatternRunner().run()
    reason_types = {reason.reason_type for reason in summary.no_trade_reason_summaries}

    assert summary.skipped_due_to_data >= 0
    assert {
        "choppy_open",
        "low_range",
        "conflicting_signals",
        "poor_data_quality",
        "incomplete_session",
        "missing_benchmark_context",
        "unclear_setup",
        "wide_opening_range",
    }.issubset(reason_types)
    assert all(reason.what_edgelab_avoided for reason in summary.no_trade_reason_summaries)
    assert all(
        reason.what_edgelab_might_have_missed for reason in summary.no_trade_reason_summaries
    )
