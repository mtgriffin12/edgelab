from edgelab.intraday.historical_provider import (
    FuturePaidHistoricalProvider,
    LocalCSVHistoricalIntradayProvider,
)
from edgelab.intraday.historical_schema import HistoricalIntradayReadiness
from edgelab.intraday.schema import IntradayBarInterval


def test_local_csv_provider_reports_safe_capabilities() -> None:
    capabilities = LocalCSVHistoricalIntradayProvider().provider_capabilities()

    assert capabilities.supports_local_files is True
    assert capabilities.supports_external_calls is False
    assert capabilities.requires_credentials is False
    assert capabilities.supported_intervals == [IntradayBarInterval.ONE_MINUTE]
    assert capabilities.real_money_status == "Not allowed"


def test_future_paid_provider_placeholder_does_not_load_or_call_out() -> None:
    provider = FuturePaidHistoricalProvider()
    capabilities = provider.provider_capabilities()

    assert capabilities.supports_external_calls is False
    assert capabilities.requires_credentials is True
    assert provider.list_symbols() == []
    assert provider.list_sessions() == []


def test_local_csv_provider_lists_symbols_and_sessions_dynamically() -> None:
    provider = LocalCSVHistoricalIntradayProvider()

    assert {"SPY", "QQQ", "GEN_HIST"}.issubset(set(provider.list_symbols()))
    session_ids = {session.session_id for session in provider.list_sessions("SPY")}
    assert "spy-2024-01-02-historical" in session_ids


def test_local_csv_provider_loads_ready_session_with_utc_bars() -> None:
    provider = LocalCSVHistoricalIntradayProvider()
    result = provider.load_session("spy", "spy-2024-01-02-historical")

    assert result.real_money_status == "Not allowed"
    assert result.bars_loaded == 5
    assert result.sessions[0].readiness == HistoricalIntradayReadiness.READY_FOR_REPLAY
    assert result.sessions[0].has_regular_first_hour is True
    assert all(bar.timestamp_utc.tzinfo is not None for bar in result.bars)
    assert all(bar.raw_timestamp for bar in result.bars)


def test_local_csv_provider_loads_generic_symbol() -> None:
    provider = LocalCSVHistoricalIntradayProvider()
    result = provider.load_session("GEN_HIST", "generic-2024-01-02-historical")

    assert result.sessions[0].symbol == "GEN_HIST"
    assert result.sessions[0].readiness == HistoricalIntradayReadiness.READY_FOR_REPLAY


def test_missing_required_columns_produce_quality_issue() -> None:
    result = LocalCSVHistoricalIntradayProvider().load_all_sessions()

    assert any(issue.code == "missing_required_columns" for issue in result.quality_issues)


def test_invalid_ohlc_makes_session_unusable() -> None:
    result = LocalCSVHistoricalIntradayProvider().load_session("BADOHLC", "bad-invalid-ohlc")

    assert any(issue.code == "invalid_ohlc" for issue in result.quality_issues)
    assert result.sessions[0].readiness == HistoricalIntradayReadiness.UNUSABLE


def test_duplicate_and_unsorted_bars_need_review() -> None:
    result = LocalCSVHistoricalIntradayProvider().load_session("BADDUPE", "bad-duplicate-unsorted")
    codes = {issue.code for issue in result.quality_issues}

    assert "duplicate_bar" in codes
    assert "unsorted_bars" in codes
    assert result.sessions[0].readiness == HistoricalIntradayReadiness.NEEDS_REVIEW


def test_incomplete_first_hour_classification() -> None:
    result = LocalCSVHistoricalIntradayProvider().load_session(
        "INCOMPLETE", "incomplete-first-hour"
    )

    assert result.sessions[0].readiness == HistoricalIntradayReadiness.INCOMPLETE
    assert "not enough first-hour coverage" in result.sessions[0].plain_english_summary
