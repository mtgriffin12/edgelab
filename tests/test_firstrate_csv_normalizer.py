from __future__ import annotations

import subprocess
from pathlib import Path

from edgelab.intraday.csv_normalizers import (
    FirstRateHistoricalCSVNormalizer,
    FirstRateLocalCSVHistoricalProvider,
)
from edgelab.intraday.historical_schema import (
    HistoricalIntradayAdjustmentMode,
    HistoricalIntradayReadiness,
)
from edgelab.intraday.schema import IntradaySessionType


def test_firstrate_header_detection_and_symbol_inference(tmp_path: Path) -> None:
    path = tmp_path / "SPY_1min_firstratedata.csv"
    _write_firstrate_file(path, [_row("2024-01-02 09:30:00")])
    normalizer = FirstRateHistoricalCSVNormalizer()

    assert normalizer.can_normalize(path) is True
    assert normalizer.infer_symbol_from_path(path) == "SPY"


def test_firstrate_normalizer_parses_timestamp_and_session_metadata(tmp_path: Path) -> None:
    path = tmp_path / "QQQ_1min_firstratedata.csv"
    _write_firstrate_file(
        path,
        [
            _row("2024-01-02 08:00:00"),
            _row("2024-01-02 09:30:00"),
            _row("2024-01-02 09:31:00"),
            _row("2024-01-02 10:30:00"),
            _row("2024-01-02 16:01:00"),
        ],
    )
    normalizer = FirstRateHistoricalCSVNormalizer(
        adjustment_mode=HistoricalIntradayAdjustmentMode.UNADJUSTED
    )

    result = normalizer.normalize_file(path, include_bars=True)

    assert result.symbol == "QQQ"
    assert result.row_count == 5
    assert result.bars[0].timestamp_utc.isoformat() == "2024-01-02T13:00:00+00:00"
    assert result.bars[0].session_id == "QQQ-2024-01-02"
    assert result.bars[0].session_type == IntradaySessionType.PREMARKET
    assert result.bars[1].session_type == IntradaySessionType.REGULAR_FIRST_HOUR
    assert result.bars[3].session_type == IntradaySessionType.REGULAR_SESSION
    assert result.bars[-1].session_type == IntradaySessionType.AFTER_HOURS
    assert result.sessions[0].has_after_hours is True


def test_firstrate_normalizer_reports_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "SPY_1min_firstratedata.csv"
    path.write_text("timestamp,open,high,low,close\n2024-01-02 09:30:00,1,2,1,2\n")

    result = FirstRateHistoricalCSVNormalizer().normalize_file(path)

    assert any(issue.code == "missing_required_columns" for issue in result.issues)
    assert result.sessions == []


def test_firstrate_normalizer_reports_bad_rows(tmp_path: Path) -> None:
    path = tmp_path / "SPY_1min_firstratedata.csv"
    _write_firstrate_file(
        path,
        [
            _row("2024-01-02 09:30:00", open_price="10", high="9", low="8", close="9"),
            _row("2024-01-02 09:31:00", volume="-1"),
            _row("not-a-time"),
            _row("2024-01-02 20:01:00"),
        ],
    )

    result = FirstRateHistoricalCSVNormalizer().normalize_file(path)
    codes = {issue.code for issue in result.issues}

    assert "invalid_ohlc" in codes
    assert "invalid_volume" in codes
    assert "invalid_timestamp" in codes
    assert "unsupported_session_time" in codes


def test_firstrate_after_hours_rows_do_not_create_quality_issues(tmp_path: Path) -> None:
    path = tmp_path / "SPY_1min_firstratedata.csv"
    _write_firstrate_file(path, _clean_full_session_rows())

    result = FirstRateHistoricalCSVNormalizer().normalize_file(path, include_bars=True)
    codes = {issue.code for issue in result.issues}

    assert "unsupported_session_time" not in codes
    assert "adjustment_mode_unknown" not in codes
    assert result.issues == []
    assert result.sessions[0].readiness == HistoricalIntradayReadiness.READY_FOR_REPLAY
    assert result.sessions[0].has_after_hours is True
    assert IntradaySessionType.AFTER_HOURS in {bar.session_type for bar in result.bars}


def test_firstrate_missing_first_hour_prevents_replay(tmp_path: Path) -> None:
    path = tmp_path / "SPY_1min_firstratedata.csv"
    _write_firstrate_file(
        path,
        [
            _row("2024-01-02 08:00:00"),
            _row("2024-01-02 10:30:00"),
            _row("2024-01-02 16:01:00"),
        ],
    )

    result = FirstRateHistoricalCSVNormalizer().normalize_file(path, include_bars=True)

    assert result.issues == []
    assert result.sessions[0].readiness == HistoricalIntradayReadiness.INCOMPLETE
    assert result.sessions[0].has_after_hours is True


def test_firstrate_after_hours_do_not_inflate_dry_run_issues(tmp_path: Path) -> None:
    _write_firstrate_file(tmp_path / "SPY_1min_firstratedata.csv", _clean_full_session_rows())
    provider = FirstRateLocalCSVHistoricalProvider(data_dir=tmp_path)

    dry_run = provider.dry_run()

    assert dry_run.files_found == 1
    assert dry_run.session_count == 1
    assert dry_run.quality_issue_count == 0
    assert dry_run.readiness_counts["ready_for_replay"] == 1
    assert dry_run.readiness_counts["needs_review"] == 0


def test_firstrate_normalizer_reports_duplicate_and_unsorted_rows(tmp_path: Path) -> None:
    path = tmp_path / "SPY_1min_firstratedata.csv"
    _write_firstrate_file(
        path,
        [
            _row("2024-01-02 09:31:00"),
            _row("2024-01-02 09:31:00"),
            _row("2024-01-02 09:30:00"),
            _row("2024-01-02 09:32:00"),
            _row("2024-01-02 09:33:00"),
            _row("2024-01-02 09:34:00"),
        ],
    )

    result = FirstRateHistoricalCSVNormalizer(
        adjustment_mode=HistoricalIntradayAdjustmentMode.UNADJUSTED
    ).normalize_file(path)
    codes = {issue.code for issue in result.issues}

    assert "duplicate_bar" in codes
    assert "unsorted_bars" in codes
    assert result.sessions[0].readiness == HistoricalIntradayReadiness.NEEDS_REVIEW


def test_firstrate_provider_lists_symbols_sessions_and_dry_run(tmp_path: Path) -> None:
    _write_firstrate_file(
        tmp_path / "SPY_1min_firstratedata.csv",
        [_row(f"2024-01-02 09:3{minute}:00") for minute in range(5)],
    )
    _write_firstrate_file(
        tmp_path / "QQQ_1min_firstratedata.csv",
        [_row(f"2024-01-03 09:3{minute}:00") for minute in range(5)],
    )
    provider = FirstRateLocalCSVHistoricalProvider(
        data_dir=tmp_path,
        normalizer=FirstRateHistoricalCSVNormalizer(
            adjustment_mode=HistoricalIntradayAdjustmentMode.UNADJUSTED
        ),
    )

    assert provider.list_symbols() == ["QQQ", "SPY"]
    spy_sessions = provider.list_sessions("SPY")
    assert [session.session_id for session in spy_sessions] == ["SPY-2024-01-02"]
    assert spy_sessions[0].readiness == HistoricalIntradayReadiness.READY_FOR_REPLAY

    dry_run = provider.dry_run()
    assert dry_run.files_found == 2
    assert dry_run.symbols_detected == ["QQQ", "SPY"]
    assert dry_run.row_count == 10
    assert dry_run.session_count == 2
    assert dry_run.readiness_counts["ready_for_replay"] == 2
    assert dry_run.research_only_status == "Research only"
    assert dry_run.real_money_status == "Not allowed"


def test_firstrate_provider_handles_zero_files(tmp_path: Path) -> None:
    provider = FirstRateLocalCSVHistoricalProvider(data_dir=tmp_path)

    dry_run = provider.dry_run()

    assert provider.detected_files() == []
    assert dry_run.files_found == 0
    assert dry_run.row_count == 0
    assert dry_run.real_money_status == "Not allowed"
    assert "No ignored local FirstRate CSV files" in dry_run.plain_english_summary


def test_real_firstrate_data_paths_remain_ignored_and_untracked() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    raw_path = "data/raw/historical_intraday/firstratedata/SPY_1min_firstratedata.csv"
    processed_path = "data/processed/historical_intraday/firstratedata/SPY.csv"

    ignored = subprocess.run(
        ["git", "check-ignore", raw_path, processed_path],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    tracked = subprocess.run(
        ["git", "ls-files", "data/raw", "data/processed"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert ignored.returncode == 0
    assert raw_path in ignored.stdout
    assert processed_path in ignored.stdout
    assert tracked.stdout == ""


def _write_firstrate_file(path: Path, rows: list[dict[str, str]]) -> None:
    header = "timestamp,open,high,low,close,volume\n"
    lines = [
        f"{row['timestamp']},{row['open']},{row['high']},{row['low']},{row['close']},{row['volume']}"
        for row in rows
    ]
    path.write_text(header + "\n".join(lines) + "\n")


def _clean_full_session_rows() -> list[dict[str, str]]:
    return [
        _row("2024-01-02 04:00:00"),
        _row("2024-01-02 08:00:00"),
        _row("2024-01-02 09:30:00"),
        _row("2024-01-02 09:31:00"),
        _row("2024-01-02 09:32:00"),
        _row("2024-01-02 09:33:00"),
        _row("2024-01-02 09:34:00"),
        _row("2024-01-02 10:30:00"),
        _row("2024-01-02 16:00:00"),
        _row("2024-01-02 16:01:00"),
        _row("2024-01-02 20:00:00"),
    ]


def _row(
    timestamp: str,
    *,
    open_price: str = "100.00",
    high: str = "100.50",
    low: str = "99.90",
    close: str = "100.25",
    volume: str = "1000",
) -> dict[str, str]:
    return {
        "timestamp": timestamp,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }
