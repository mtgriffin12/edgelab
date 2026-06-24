from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from edgelab.app import main
from edgelab.intraday.pair_morning_trigger_exit import (
    PairMorningTriggerExitConfig,
    PairMorningTriggerExitStudyService,
)

client = TestClient(main.app)
NEW_YORK = ZoneInfo("America/New_York")


def test_pair_engine_reads_files_and_uses_file_driven_overlap(tmp_path: Path) -> None:
    service = _pair_service(tmp_path)

    study = service.run()

    assert study.primary_symbol == "SPY"
    assert study.comparison_symbol == "CSGP"
    assert study.primary_file_range.first_date == date(2026, 6, 1)
    assert study.comparison_file_range.last_date == date(2026, 6, 9)
    assert study.overlap_range_analyzed.trading_dates == 9
    assert study.trading_days_analyzed == 9
    assert study.sample_description == "Short local sample"
    assert study.real_money_status == "Not allowed"
    assert study.no_external_calls is True
    assert study.no_live_data is True


def test_pair_engine_reports_missing_files(tmp_path: Path) -> None:
    service = PairMorningTriggerExitStudyService(
        PairMorningTriggerExitConfig(
            study_name="AAA / BBB Study",
            primary_symbol="AAA",
            comparison_symbol="BBB",
            primary_file_path=tmp_path / "AAA.csv",
            comparison_file_path=tmp_path / "BBB.csv",
            relationship_name="Fixture relationship",
            primary_down_label="AAA down",
            primary_up_label="AAA up",
            comparison_stronger_label="BBB stronger",
            comparison_weaker_label="BBB weaker",
        )
    )

    study = service.run()

    assert study.files_used[0].exists is False
    assert study.files_used[1].exists is False
    assert study.trading_days_analyzed == 0
    assert "missing locally" in study.data_readiness_summary


def test_pair_engine_runs_for_non_spy_csgp_pair_without_algorithm_change(tmp_path: Path) -> None:
    primary_path = tmp_path / "AAA_recent_1min.csv"
    comparison_path = tmp_path / "BBB_recent_1min.csv"
    _write_pair_fixture(primary_path, comparison_path)
    service = PairMorningTriggerExitStudyService(
        PairMorningTriggerExitConfig(
            study_name="AAA / BBB Pair Study",
            primary_symbol="AAA",
            comparison_symbol="BBB",
            primary_file_path=primary_path,
            comparison_file_path=comparison_path,
            relationship_name="Fixture inverse relationship",
            primary_down_label="AAA down",
            primary_up_label="AAA up",
            comparison_stronger_label="BBB stronger",
            comparison_weaker_label="BBB weaker",
        )
    )

    study = service.run()

    assert study.primary_symbol == "AAA"
    assert study.comparison_symbol == "BBB"
    assert study.setup_families[0].family_label == "AAA down / BBB stronger"
    assert study.setup_families[1].family_label == "AAA up / BBB weaker"
    assert study.ranked_trigger_exit_combinations


def test_pair_engine_detects_family_a_and_family_b_triggers(tmp_path: Path) -> None:
    study = _pair_service(tmp_path).run()

    family_a = next(row for row in study.trigger_condition_summaries if row.condition_id == "A1")
    family_b = next(row for row in study.trigger_condition_summaries if row.condition_id == "B1")

    assert family_a.examples_found == 6
    assert family_b.examples_found == 3
    assert "SPY down / CSGP stronger" in family_a.family_label
    assert "SPY up / CSGP weaker" in family_b.family_label


def test_pair_engine_measures_outcomes_thresholds_and_giveback(tmp_path: Path) -> None:
    study = _pair_service(tmp_path).run()
    a1_1100 = next(
        row
        for row in study.outcome_window_summaries
        if row.condition_id == "A1" and row.outcome_window_label == "10:00-11:00"
    )
    b1_1030 = next(
        row
        for row in study.outcome_window_summaries
        if row.condition_id == "B1" and row.outcome_window_label == "10:00-10:30"
    )

    assert a1_1100.matching_mornings == 6
    assert a1_1100.favorable_count == 6
    assert a1_1100.favorable_percent == 100.0
    assert a1_1100.median_post_trigger_move is not None
    assert a1_1100.threshold_reached_counts["Reached +0.50% from trigger"] == 6
    assert a1_1100.kept_half_count == 6
    assert a1_1100.gave_back_half_count == 0
    assert b1_1030.matching_mornings == 3
    assert b1_1030.rating == "Too few examples"
    assert "Reached -0.50% from trigger" in b1_1030.threshold_reached_counts


def test_pair_engine_ranks_conservatively(tmp_path: Path) -> None:
    study = _pair_service(tmp_path).run()

    assert study.ranked_trigger_exit_combinations[0].rating == "Interesting but needs more history"
    assert "needs more history" in study.best_current_research_clue
    assert any(row.rating == "Too few examples" for row in study.ranked_trigger_exit_combinations)
    assert "not enough to judge" not in study.plain_english_bottom_line.lower()


def test_pair_engine_handles_no_trigger_examples_and_missing_trigger_bars(tmp_path: Path) -> None:
    primary_path = tmp_path / "AAA_recent_1min.csv"
    comparison_path = tmp_path / "BBB_recent_1min.csv"
    _write_custom_file(
        primary_path,
        [
            ("2026-06-01", "09:30", 100.0, 100.0),
            ("2026-06-01", "09:45", 100.1, 100.1),
        ],
    )
    _write_custom_file(
        comparison_path,
        [
            ("2026-06-01", "09:30", 50.0, 50.0),
            ("2026-06-01", "09:45", 50.1, 50.1),
        ],
    )
    service = PairMorningTriggerExitStudyService(
        PairMorningTriggerExitConfig(
            study_name="AAA / BBB Pair Study",
            primary_symbol="AAA",
            comparison_symbol="BBB",
            primary_file_path=primary_path,
            comparison_file_path=comparison_path,
            relationship_name="Fixture relationship",
            primary_down_label="AAA down",
            primary_up_label="AAA up",
            comparison_stronger_label="BBB stronger",
            comparison_weaker_label="BBB weaker",
        )
    )

    study = service.run()

    assert study.trading_days_analyzed == 1
    assert all(row.examples_found == 0 for row in study.trigger_condition_summaries)
    assert "no trigger examples" in study.plain_english_bottom_line.lower()


def test_spy_csgp_trigger_exit_api_and_ui_routes(monkeypatch, tmp_path: Path) -> None:
    service = _pair_service(tmp_path)
    monkeypatch.setattr(main, "spy_csgp_trigger_exit_service", service)

    api_response = client.get("/intraday/research/spy-csgp/trigger-exit-study")
    ui_response = client.get("/ui/intraday-lab/research/spy-csgp/trigger-exit-study")

    assert api_response.status_code == 200
    data = api_response.json()
    assert data["study_name"] == "SPY / CSGP Morning Divergence Trigger and Exit Study"
    assert data["primary_symbol"] == "SPY"
    assert data["comparison_symbol"] == "CSGP"
    assert data["primary_file_used"].endswith("SPY_recent_1min.csv")
    assert data["comparison_file_used"].endswith("CSGP_recent_1min.csv")
    assert data["relationship_tested"] == "Morning inverse relationship"
    assert data["real_money_status"] == "Not allowed"
    assert data["overlap_range_analyzed"]["trading_dates"] == 9
    assert data["ranked_trigger_exit_combinations"]
    assert data["no_external_calls"] is True

    assert ui_response.status_code == 200
    for phrase in [
        "Bottom line",
        "Study name",
        "Primary symbol",
        "Comparison symbol",
        "Relationship tested",
        "Primary file used",
        "Comparison file used",
        "Trigger time",
        "SPY down / CSGP stronger setups",
        "SPY up / CSGP weaker setups",
        "Ranked trigger + exit combinations",
        "Giveback / hold behavior",
        "Real-money status:",
        "Not allowed",
    ]:
        assert phrase in ui_response.text
    for forbidden in [
        "Trade button",
        "entry order",
        "exit order",
        "paper ready",
        "live ready",
        "real-money ready",
        "validated",
        "profitable",
        "proven",
    ]:
        assert forbidden.lower() not in ui_response.text.lower()


def test_spy_csgp_pages_link_to_trigger_exit_study() -> None:
    research_response = client.get("/ui/intraday-lab/research")
    audit_response = client.get("/ui/intraday-lab/research/spy-csgp")
    divergence_response = client.get("/ui/intraday-lab/research/spy-csgp/morning-divergence")

    for response in [research_response, audit_response, divergence_response]:
        assert response.status_code == 200
        assert "/ui/intraday-lab/research/spy-csgp/trigger-exit-study" in response.text


def _pair_service(tmp_path: Path) -> PairMorningTriggerExitStudyService:
    primary_path = tmp_path / "SPY_recent_1min.csv"
    comparison_path = tmp_path / "CSGP_recent_1min.csv"
    _write_pair_fixture(primary_path, comparison_path)
    return PairMorningTriggerExitStudyService(
        PairMorningTriggerExitConfig(
            study_name="SPY / CSGP Morning Divergence Trigger and Exit Study",
            primary_symbol="SPY",
            comparison_symbol="CSGP",
            primary_file_path=primary_path,
            comparison_file_path=comparison_path,
            relationship_name="Morning inverse relationship",
            primary_down_label="SPY down",
            primary_up_label="SPY up",
            comparison_stronger_label="CSGP stronger",
            comparison_weaker_label="CSGP weaker",
        )
    )


def _write_pair_fixture(primary_path: Path, comparison_path: Path) -> None:
    primary_rows: list[tuple[str, str, float, float]] = []
    comparison_rows: list[tuple[str, str, float, float]] = []
    start = date(2026, 6, 1)
    for index in range(6):
        session = (start + timedelta(days=index)).isoformat()
        primary_rows.extend(
            [
                (session, "09:30", 100.0, 100.0),
                (session, "10:00", 99.4, 99.4),
                (session, "10:30", 99.2, 99.2),
                (session, "11:00", 99.1, 99.1),
                (session, "12:00", 99.0, 99.0),
                (session, "15:59", 98.8, 98.8),
            ]
        )
        comparison_rows.extend(
            [
                (session, "09:30", 50.0, 50.0),
                (session, "10:00", 50.2, 50.2),
                (session, "10:30", 50.55, 50.55),
                (session, "11:00", 50.85, 50.85),
                (session, "12:00", 51.05, 51.05),
                (session, "15:59", 50.9, 50.9),
            ]
        )
    for index in range(6, 9):
        session = (start + timedelta(days=index)).isoformat()
        primary_rows.extend(
            [
                (session, "09:30", 100.0, 100.0),
                (session, "10:00", 100.6, 100.6),
                (session, "10:30", 100.8, 100.8),
                (session, "11:00", 101.0, 101.0),
                (session, "12:00", 101.2, 101.2),
                (session, "15:59", 101.1, 101.1),
            ]
        )
        comparison_rows.extend(
            [
                (session, "09:30", 50.0, 50.0),
                (session, "10:00", 49.8, 49.8),
                (session, "10:30", 49.45, 49.45),
                (session, "11:00", 49.3, 49.3),
                (session, "12:00", 49.2, 49.2),
                (session, "15:59", 49.35, 49.35),
            ]
        )
    _write_custom_file(primary_path, primary_rows)
    _write_custom_file(comparison_path, comparison_rows)


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
