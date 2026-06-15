from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from edgelab.intraday.csv_normalizers import FirstRateLocalCSVHistoricalProvider
from edgelab.intraday.out_of_sample_gate import OutOfSampleGateService
from edgelab.intraday.out_of_sample_gate_schema import (
    OutOfSampleGateConclusion,
    OutOfSampleGateRequest,
    OutOfSampleSplitStrategy,
)
from edgelab.research_runs.schema import ResearchRunCreateRequest
from edgelab.research_runs.service import FirstRateResearchRunService
from edgelab.research_runs.store import SQLiteResearchRunStore


def test_out_of_sample_schema_rejects_unsafe_copy() -> None:
    with pytest.raises(ValueError):
        OutOfSampleGateRequest(instrument="SPY", paired_instrument="SPY")


def test_out_of_sample_gate_requires_saved_runs_without_creating_them(tmp_path: Path) -> None:
    provider = _provider_with_split_sessions(tmp_path)
    saved_run_service = FirstRateResearchRunService(
        store=SQLiteResearchRunStore(tmp_path / "runs.db"),
        provider=provider,
    )
    service = OutOfSampleGateService(
        research_run_service=saved_run_service,
        provider=provider,
    )

    result = service.run()

    assert result.gate_conclusion == OutOfSampleGateConclusion.BLOCKED_BY_DATA_QUALITY
    assert result.real_money_status == "Not allowed"
    assert saved_run_service.list_runs() == []
    assert not (tmp_path / "runs.db").exists()


def test_out_of_sample_gate_uses_fixed_quarter_split_and_cache(tmp_path: Path) -> None:
    provider = _provider_with_split_sessions(tmp_path)
    saved_run_service = FirstRateResearchRunService(
        store=SQLiteResearchRunStore(tmp_path / "runs.db"),
        provider=provider,
    )
    saved_run_service.run_firstrate_many_morning(ResearchRunCreateRequest(symbol="SPY"))
    saved_run_service.run_firstrate_many_morning(ResearchRunCreateRequest(symbol="QQQ"))
    service = OutOfSampleGateService(
        research_run_service=saved_run_service,
        provider=provider,
    )

    first = service.run()
    second = service.run()

    assert first.real_money_status == "Not allowed"
    assert first.split_strategy == OutOfSampleSplitStrategy.CALENDAR_QUARTER_HOLDOUT
    assert first.discovery_period is not None
    assert first.holdout_period is not None
    assert first.discovery_period.start_date == date(2022, 9, 30)
    assert first.discovery_period.end_date < date(2023, 1, 1)
    assert first.holdout_period.start_date == date(2023, 1, 3)
    assert first.holdout_period.end_date >= date(2023, 1, 14)
    assert first.cache_metadata["cache_status"] == "fresh"
    assert second.cache_metadata["cache_status"] == "cached"
    by_id = {comparison.variant_id: comparison for comparison in first.variant_comparisons}
    assert set(by_id) == set(OutOfSampleGateRequest().variant_ids)
    assert by_id["failed_push_from_above"].discovery_result.examples_completed >= 10
    assert by_id["failed_push_from_above"].holdout_result.examples_completed >= 10
    assert "not proof" in first.proof_limitations.lower()
    assert "pure untouched-data" in first.proof_limitations
    assert "ready" not in first.bottom_line.lower()


def _provider_with_split_sessions(tmp_path: Path) -> FirstRateLocalCSVHistoricalProvider:
    spy_rows = []
    qqq_rows = []
    for index in range(12):
        session_date = date(2022, 9, 30) + timedelta(days=index)
        spy_rows.append(_failed_push_session_rows(session_date))
        qqq_rows.append(_stable_session_rows(session_date))
    for index in range(12):
        session_date = date(2023, 1, 3) + timedelta(days=index)
        spy_rows.append(_failed_push_session_rows(session_date))
        qqq_rows.append(_stable_session_rows(session_date))
    _write_firstrate_file(tmp_path / "SPY_1min_firstratedata.csv", "".join(spy_rows))
    _write_firstrate_file(tmp_path / "QQQ_1min_firstratedata.csv", "".join(qqq_rows))
    return FirstRateLocalCSVHistoricalProvider(tmp_path)


def _write_firstrate_file(path: Path, rows: str) -> None:
    path.write_text("timestamp,open,high,low,close,volume\n" + rows, encoding="utf-8")


def _failed_push_session_rows(session_date: date) -> str:
    rows = []
    for minute_index in range(61):
        timestamp = _timestamp(session_date, minute_index)
        open_price = 100.0
        high = 100.4
        low = 99.6
        close = 100.0
        if minute_index == 6:
            high = 101.2
            close = 100.45
        elif minute_index == 7:
            high = 100.4
            low = 99.7
            close = 99.8
        elif minute_index > 7:
            high = 100.0
            low = 98.8
            close = 99.0
        rows.append(_row(timestamp, open_price, high, low, close))
    return "".join(rows)


def _stable_session_rows(session_date: date) -> str:
    rows = []
    for minute_index in range(61):
        rows.append(_row(_timestamp(session_date, minute_index), 100.0, 100.2, 99.8, 100.0))
    return "".join(rows)


def _timestamp(session_date: date, minute_index: int) -> str:
    parsed = datetime.combine(session_date, datetime.min.time()).replace(
        hour=9,
        minute=30,
    ) + timedelta(minutes=minute_index)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _row(timestamp: str, open_price: float, high: float, low: float, close: float) -> str:
    return f"{timestamp},{open_price:.2f},{high:.2f},{low:.2f},{close:.2f},1000\n"
