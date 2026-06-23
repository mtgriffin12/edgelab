from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from edgelab.intraday.marketdata_app_downloader import (
    MARKETDATA_APP_TOKEN_ENV,
    build_download_plan,
    normalize_marketdata_response,
    read_marketdata_token,
    token_is_present,
    validate_normalized_csv,
    validate_pair,
    write_normalized_csv,
)


def test_builds_planned_requests_without_token_or_network(tmp_path: Path) -> None:
    plan = build_download_plan(
        symbols=["SPY", "CSGP"],
        months=12,
        output_dir=tmp_path,
        today=date(2026, 6, 23),
    )

    assert [request.symbol for request in plan.requests] == ["SPY", "CSGP"]
    assert plan.total_estimated_candles > 0
    assert plan.total_estimated_credits > 0
    assert plan.requests[0].url.endswith("/v1/stocks/candles/1/SPY/")
    assert plan.requests[0].params == {
        "from": "2025-06-23",
        "to": "2026-06-23",
        "extended": "false",
        "adjustsplits": "false",
    }
    assert plan.requests[0].output_path == tmp_path / "SPY_recent_1min.csv"


def test_missing_token_is_reported_without_printing_token() -> None:
    assert token_is_present({}) is False
    assert token_is_present({MARKETDATA_APP_TOKEN_ENV: "dummy-present-value"}) is True
    with pytest.raises(ValueError, match=MARKETDATA_APP_TOKEN_ENV):
        read_marketdata_token({})


def test_maps_provider_array_response_to_sorted_normalized_rows() -> None:
    payload = {
        "s": "ok",
        "t": [1_672_756_800, 1_672_756_740],
        "o": [102.0, 100.0],
        "h": [103.0, 101.0],
        "l": [101.0, 99.0],
        "c": [102.5, 100.5],
        "v": [2000, 1000],
    }

    result = normalize_marketdata_response(payload, regular_hours_only=False)

    assert result.warnings == []
    assert [row.open for row in result.rows] == [100.0, 102.0]
    assert result.rows[0].timestamp == datetime(2023, 1, 3, 14, 39, tzinfo=UTC)


def test_maps_provider_object_response_and_skips_bad_values() -> None:
    payload = {
        "s": "ok",
        "candles": [
            {
                "timestamp": "2023-01-03T14:30:00Z",
                "open": "100",
                "high": "101",
                "low": "99",
                "close": "100.5",
                "volume": "1000",
            },
            {
                "timestamp": "2023-01-03T14:31:00Z",
                "open": "",
                "high": "101",
                "low": "99",
                "close": "100.5",
                "volume": "1000",
            },
        ],
    }

    result = normalize_marketdata_response(payload)

    assert len(result.rows) == 1
    assert "missing open" in result.warnings[0]


def test_duplicate_timestamps_are_skipped_with_warning() -> None:
    payload = {
        "s": "ok",
        "t": [1_672_756_800, 1_672_756_800],
        "o": [100.0, 101.0],
        "h": [101.0, 102.0],
        "l": [99.0, 100.0],
        "c": [100.5, 101.5],
        "v": [1000, 1100],
    }

    result = normalize_marketdata_response(payload, regular_hours_only=False)

    assert len(result.rows) == 1
    assert "Duplicate timestamp" in result.warnings[0]


def test_writes_normalized_csv_and_refuses_overwrite(tmp_path: Path) -> None:
    payload = {
        "s": "ok",
        "t": [1_672_756_800],
        "o": [100.0],
        "h": [101.0],
        "l": [99.0],
        "c": [100.5],
        "v": [1000],
    }
    rows = normalize_marketdata_response(payload, regular_hours_only=False).rows
    path = tmp_path / "SPY_recent_1min.csv"

    summary = write_normalized_csv(path, rows)

    assert summary.row_count == 1
    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        assert reader.fieldnames == ["timestamp", "open", "high", "low", "close", "volume"]
    with pytest.raises(FileExistsError):
        write_normalized_csv(path, rows)


def test_pair_validation_detects_overlap_missing_and_mismatched_dates(tmp_path: Path) -> None:
    spy_path = tmp_path / "SPY_recent_1min.csv"
    csgp_path = tmp_path / "CSGP_recent_1min.csv"

    missing_result = validate_pair(spy_path, csgp_path)
    assert missing_result.suitable_for_morning_divergence_study is False
    assert "Neither recent SPY nor recent CSGP" in missing_result.plain_english_summary

    _write_normalized_file(spy_path, ["2023-01-03T14:30:00Z", "2023-01-04T14:30:00Z"])
    _write_normalized_file(csgp_path, ["2023-01-04T14:30:00Z", "2023-01-05T14:30:00Z"])
    overlap_result = validate_pair(spy_path, csgp_path)
    assert overlap_result.suitable_for_morning_divergence_study is True
    assert overlap_result.common_trading_dates == 1
    assert overlap_result.spy_only_dates == 1
    assert overlap_result.csgp_only_dates == 1

    _write_normalized_file(csgp_path, ["2023-02-01T14:30:00Z"])
    mismatch_result = validate_pair(spy_path, csgp_path)
    assert mismatch_result.suitable_for_morning_divergence_study is False
    assert "do not overlap cleanly" in mismatch_result.plain_english_summary


def test_normalized_csv_validation_reports_bad_shape(tmp_path: Path) -> None:
    path = tmp_path / "SPY_recent_1min.csv"
    path.write_text("timestamp,open,high,low,close\n2023-01-03T14:30:00Z,1,2,0,1\n")

    summary = validate_normalized_csv(path)

    assert summary.row_count == 0
    assert any("volume" in warning for warning in summary.warnings)


def _write_normalized_file(path: Path, timestamps: list[str]) -> None:
    rows = [f"{timestamp},100,101,99,100.5,1000" for timestamp in timestamps]
    path.write_text("timestamp,open,high,low,close,volume\n" + "\n".join(rows) + "\n")
