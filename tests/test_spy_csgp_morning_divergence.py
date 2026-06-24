from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from edgelab.app import main
from edgelab.intraday.spy_csgp_morning_divergence import (
    SpyCsgpMorningDivergenceStudyService,
)

client = TestClient(main.app)
NEW_YORK = ZoneInfo("America/New_York")


def test_study_reads_normalized_csv_and_detects_overlapping_dates(tmp_path: Path) -> None:
    service = _study_service(tmp_path)

    study = service.run()

    assert study.files_used[0].symbol == "SPY"
    assert study.files_used[0].row_count == 24
    assert study.files_used[1].symbol == "CSGP"
    assert study.overlapping_start_date == date(2026, 6, 1)
    assert study.overlapping_end_date == date(2026, 6, 4)
    assert study.trading_dates_analyzed == 4
    assert study.spy_file_range.first_date == date(2026, 6, 1)
    assert study.csgp_file_range.last_date == date(2026, 6, 4)
    assert study.overlap_range_analyzed.trading_dates == 4
    assert study.analyzed_sample_description == "Short local sample"
    assert study.real_money_status == "Not allowed"
    assert study.no_external_calls is True


def test_study_reports_missing_spy_and_csgp(tmp_path: Path) -> None:
    spy_path = tmp_path / "SPY_recent_1min.csv"
    csgp_path = tmp_path / "CSGP_recent_1min.csv"
    service = SpyCsgpMorningDivergenceStudyService(spy_path=spy_path, csgp_path=csgp_path)

    study = service.run()

    assert study.files_used[0].exists is False
    assert study.files_used[1].exists is False
    assert "missing locally" in study.data_readiness_summary
    assert study.trading_dates_analyzed == 0


def test_study_detects_non_overlapping_files(tmp_path: Path) -> None:
    spy_path = tmp_path / "SPY_recent_1min.csv"
    csgp_path = tmp_path / "CSGP_recent_1min.csv"
    _write_symbol_file(
        spy_path,
        [
            {
                "date": "2026-06-01",
                "open": 100.0,
                "m945": 99.0,
                "m1000": 98.8,
                "m1030": 99.0,
                "m1100": 99.5,
                "m1559": 100.0,
            }
        ],
    )
    _write_symbol_file(
        csgp_path,
        [
            {
                "date": "2026-06-02",
                "open": 50.0,
                "m945": 51.0,
                "m1000": 52.0,
                "m1030": 52.5,
                "m1100": 53.0,
                "m1559": 52.0,
            }
        ],
    )
    service = SpyCsgpMorningDivergenceStudyService(spy_path=spy_path, csgp_path=csgp_path)

    study = service.run()

    assert study.trading_dates_analyzed == 0
    assert "do not overlap" in study.data_readiness_summary


def test_study_computes_morning_returns_and_weak_spy_counts(tmp_path: Path) -> None:
    study = _study_service(tmp_path).run()
    open_to_15 = next(
        row for row in study.window_summaries if row.window_id == "open_to_15_minutes"
    )
    open_to_30_threshold = next(
        row
        for row in study.threshold_summaries
        if row.window_id == "open_to_30_minutes" and row.threshold_pct == 0.5
    )

    assert open_to_15.average_spy_move == 0.05
    assert open_to_15.average_csgp_move == 0.05
    assert open_to_15.spy_down_csgp_up_count == 1
    assert open_to_15.same_direction_count == 2
    assert open_to_15.opposite_direction_count == 2
    assert open_to_30_threshold.matching_mornings == 2
    assert open_to_30_threshold.csgp_positive_while_spy_negative_count == 1
    assert open_to_30_threshold.csgp_also_fell_count == 1
    assert open_to_30_threshold.same_direction_count == 1
    assert open_to_30_threshold.opposite_direction_count == 1
    assert open_to_30_threshold.average_spy_move == -0.9
    assert open_to_30_threshold.average_csgp_move == 0.6


def test_study_computes_spy_up_csgp_weaker_side(tmp_path: Path) -> None:
    study = _study_service(tmp_path).run()
    strength = next(
        row
        for row in study.strength_threshold_summaries
        if row.window_id == "open_to_30_minutes" and row.threshold_pct == 0.5
    )

    assert strength.matching_mornings == 2
    assert strength.csgp_negative_while_spy_positive_count == 1
    assert strength.csgp_lagged_spy_by_1pt_count == 1
    assert strength.csgp_lagged_spy_by_2pt_count == 1
    assert strength.csgp_also_rose_count == 1
    assert strength.same_direction_count == 1
    assert strength.opposite_direction_count == 1
    assert strength.average_spy_move == 1.0
    assert strength.average_csgp_move == -0.4
    assert "Interesting clue" in strength.plain_english_summary


def test_study_combines_both_inverse_sides_conservatively(tmp_path: Path) -> None:
    study = _study_service(tmp_path).run()
    combined = next(
        row
        for row in study.combined_inverse_summaries
        if row.window_id == "open_to_30_minutes" and row.threshold_pct == 0.5
    )

    assert combined.total_meaningful_spy_move_mornings == 4
    assert combined.inverse_mornings_count == 2
    assert combined.inverse_mornings_percent == 50.0
    assert combined.same_direction_mornings_count == 2
    assert combined.same_direction_mornings_percent == 50.0
    assert combined.clearer_side == "Too few examples on both sides"
    assert combined.sample_readiness == "Too few examples"
    assert "interesting clue" in study.plain_english_bottom_line.lower()
    assert "too few examples" in study.plain_english_bottom_line.lower()


def test_study_identifies_strongest_weakest_and_follow_through(tmp_path: Path) -> None:
    study = _study_service(tmp_path).run()

    assert study.strongest_divergence_days[0].date == date(2026, 6, 1)
    assert study.strongest_divergence_days[0].window_label == "9:30-10:30"
    assert study.weakest_divergence_days[0].date == date(2026, 6, 3)
    assert study.follow_through_summary.matching_mornings == 2
    assert study.follow_through_summary.csgp_continued_higher_count == 1
    assert study.follow_through_summary.csgp_gave_back_count == 0
    assert "After 10:00" in study.follow_through_summary.plain_english_summary


def test_study_uses_file_driven_overlap_for_longer_replacement_files(tmp_path: Path) -> None:
    spy_path = tmp_path / "SPY_recent_1min.csv"
    csgp_path = tmp_path / "CSGP_recent_1min.csv"
    replacement_days = [
        _generated_day(date(2026, 1, 1) + timedelta(days=index)) for index in range(65)
    ]
    _write_symbol_file(spy_path, replacement_days)
    _write_symbol_file(csgp_path, replacement_days)

    study = SpyCsgpMorningDivergenceStudyService(spy_path=spy_path, csgp_path=csgp_path).run()

    assert study.trading_dates_analyzed == 65
    assert study.overlap_range_analyzed.first_date == date(2026, 1, 1)
    assert study.overlap_range_analyzed.last_date == date(2026, 3, 6)
    assert study.analyzed_sample_description == "Recent local sample"


def test_study_handles_missing_window_bars(tmp_path: Path) -> None:
    spy_path = tmp_path / "SPY_recent_1min.csv"
    csgp_path = tmp_path / "CSGP_recent_1min.csv"
    _write_custom_file(
        spy_path,
        [
            ("2026-06-01", "09:30", 100.0, 100.0),
            ("2026-06-01", "09:45", 99.0, 99.0),
        ],
    )
    _write_custom_file(
        csgp_path,
        [
            ("2026-06-01", "09:30", 50.0, 50.0),
            ("2026-06-01", "09:45", 51.0, 51.0),
        ],
    )
    study = SpyCsgpMorningDivergenceStudyService(spy_path=spy_path, csgp_path=csgp_path).run()

    open_to_60 = next(
        row for row in study.window_summaries if row.window_id == "open_to_60_minutes"
    )
    assert open_to_60.missing_dates == 0
    follow = next(
        row for row in study.window_summaries if row.window_id == "follow_through_after_10"
    )
    assert follow.dates_analyzed == 0
    assert follow.missing_dates == 1


def test_spy_csgp_morning_divergence_api_and_ui_routes(monkeypatch, tmp_path: Path) -> None:
    service = _study_service(tmp_path)
    monkeypatch.setattr(main, "spy_csgp_morning_divergence_service", service)

    api_response = client.get("/intraday/research/spy-csgp/morning-divergence")
    ui_response = client.get("/ui/intraday-lab/research/spy-csgp/morning-divergence")

    assert api_response.status_code == 200
    api_data = api_response.json()
    assert api_data["trading_dates_analyzed"] == 4
    assert api_data["real_money_status"] == "Not allowed"
    assert api_data["no_external_calls"] is True
    assert api_data["spy_file_range"]["first_date"] == "2026-06-01"
    assert api_data["csgp_file_range"]["last_date"] == "2026-06-04"
    assert api_data["overlap_range_analyzed"]["trading_dates"] == 4
    assert api_data["analyzed_sample_description"] == "Short local sample"
    assert "spy_up_csgp_weaker_summary" in api_data
    assert "combined_inverse_summary" in api_data

    assert ui_response.status_code == 200
    for phrase in [
        "Bottom line",
        "Data window",
        "Overlapping date range analyzed",
        "Trading days analyzed",
        "SPY down / CSGP stronger",
        "SPY up / CSGP weaker",
        "Combined inverse relationship",
        "Strongest inverse mornings",
        "Weakest inverse mornings",
        "Follow-through after 10:00",
        "What to study next",
        "Real-money status:",
        "Not allowed",
    ]:
        assert phrase in ui_response.text
    for forbidden in [
        "Trade button",
        "place order",
        "paper ready",
        "live ready",
        "real-money ready",
        "validated",
        "profitable",
    ]:
        assert forbidden.lower() not in ui_response.text.lower()


def test_spy_csgp_morning_divergence_api_reports_missing_csgp(monkeypatch, tmp_path: Path) -> None:
    spy_path = tmp_path / "SPY_recent_1min.csv"
    _write_symbol_file(
        spy_path,
        [
            {
                "date": "2026-06-01",
                "open": 100.0,
                "m945": 99.0,
                "m1000": 98.8,
                "m1030": 99.0,
                "m1100": 99.5,
                "m1559": 100.0,
            }
        ],
    )
    service = SpyCsgpMorningDivergenceStudyService(
        spy_path=spy_path,
        csgp_path=tmp_path / "CSGP_recent_1min.csv",
    )
    monkeypatch.setattr(main, "spy_csgp_morning_divergence_service", service)

    response = client.get("/intraday/research/spy-csgp/morning-divergence")

    assert response.status_code == 200
    data = response.json()
    assert data["files_used"][1]["exists"] is False
    assert "CSGP file is missing" in data["data_readiness_summary"]


def _study_service(tmp_path: Path) -> SpyCsgpMorningDivergenceStudyService:
    spy_path = tmp_path / "SPY_recent_1min.csv"
    csgp_path = tmp_path / "CSGP_recent_1min.csv"
    _write_symbol_file(
        spy_path,
        [
            {
                "date": "2026-06-01",
                "open": 100.0,
                "m945": 99.0,
                "m1000": 98.8,
                "m1030": 99.0,
                "m1100": 99.5,
                "m1559": 100.0,
            },
            {
                "date": "2026-06-02",
                "open": 100.0,
                "m945": 99.4,
                "m1000": 99.4,
                "m1030": 99.2,
                "m1100": 99.1,
                "m1559": 99.0,
            },
            {
                "date": "2026-06-03",
                "open": 100.0,
                "m945": 101.0,
                "m1000": 101.2,
                "m1030": 101.0,
                "m1100": 100.8,
                "m1559": 100.5,
            },
            {
                "date": "2026-06-04",
                "open": 100.0,
                "m945": 100.8,
                "m1000": 100.8,
                "m1030": 100.9,
                "m1100": 101.0,
                "m1559": 101.2,
            },
        ],
    )
    _write_symbol_file(
        csgp_path,
        [
            {
                "date": "2026-06-01",
                "open": 50.0,
                "m945": 51.0,
                "m1000": 52.0,
                "m1030": 52.5,
                "m1100": 53.0,
                "m1559": 52.0,
            },
            {
                "date": "2026-06-02",
                "open": 50.0,
                "m945": 49.0,
                "m1000": 48.6,
                "m1030": 48.5,
                "m1100": 48.4,
                "m1559": 48.0,
            },
            {
                "date": "2026-06-03",
                "open": 50.0,
                "m945": 49.5,
                "m1000": 49.0,
                "m1030": 49.2,
                "m1100": 49.4,
                "m1559": 49.5,
            },
            {
                "date": "2026-06-04",
                "open": 50.0,
                "m945": 50.6,
                "m1000": 50.6,
                "m1030": 50.7,
                "m1100": 50.8,
                "m1559": 51.0,
            },
        ],
    )
    return SpyCsgpMorningDivergenceStudyService(spy_path=spy_path, csgp_path=csgp_path)


def _generated_day(session_date: date) -> dict[str, float | str]:
    return {
        "date": session_date.isoformat(),
        "open": 100.0,
        "m945": 100.2,
        "m1000": 100.4,
        "m1030": 100.1,
        "m1100": 100.3,
        "m1559": 100.5,
    }


def _write_symbol_file(path: Path, days: list[dict[str, float | str]]) -> None:
    rows: list[tuple[str, str, float, float]] = []
    for day in days:
        session_date = str(day["date"])
        rows.extend(
            [
                (session_date, "09:30", float(day["open"]), float(day["open"])),
                (session_date, "09:45", float(day["m945"]), float(day["m945"])),
                (session_date, "10:00", float(day["m1000"]), float(day["m1000"])),
                (session_date, "10:30", float(day["m1030"]), float(day["m1030"])),
                (session_date, "11:00", float(day["m1100"]), float(day["m1100"])),
                (session_date, "15:59", float(day["m1559"]), float(day["m1559"])),
            ]
        )
    _write_custom_file(path, rows)


def _write_custom_file(path: Path, rows: list[tuple[str, str, float, float]]) -> None:
    lines = ["timestamp,open,high,low,close,volume"]
    for session_date, local_time, open_price, close_price in rows:
        timestamp = datetime.fromisoformat(f"{session_date}T{local_time}:00").replace(
            tzinfo=NEW_YORK
        )
        utc_timestamp = timestamp.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")
        high = max(open_price, close_price)
        low = min(open_price, close_price)
        lines.append(f"{utc_timestamp},{open_price},{high},{low},{close_price},1000")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
