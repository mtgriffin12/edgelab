from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from edgelab.app import main
from edgelab.intraday.csv_normalizers import (
    FirstRateHistoricalCSVNormalizer,
    FirstRateLocalCSVHistoricalProvider,
)
from edgelab.intraday.historical_schema import HistoricalIntradayAdjustmentMode
from edgelab.intraday.spy_csgp_data_audit import SpyCsgpDataAuditService

client = TestClient(main.app)


def test_spy_csgp_audit_detects_local_files_and_missing_csgp(tmp_path: Path) -> None:
    provider = _provider_with_spy_and_qqq(tmp_path)
    audit = SpyCsgpDataAuditService(provider=provider, as_of=date(2026, 6, 23)).run()

    assert audit.available_symbols == ["QQQ", "SPY"]
    assert audit.spy_data_found is True
    assert audit.csgp_data_found is False
    assert audit.spy_summary is not None
    assert audit.spy_summary.symbol == "SPY"
    assert audit.spy_summary.row_count == 10
    assert audit.spy_summary.start_date == date(2023, 9, 28)
    assert audit.spy_summary.end_date == date(2023, 9, 29)
    assert audit.spy_summary.calendar_days_covered == 2
    assert audit.spy_summary.apparent_trading_sessions == 2
    assert audit.spy_summary.usable_first_hour_sessions == 2
    assert audit.spy_summary.first_hour_data_appears_usable is True
    assert "too old" in audit.current_spy_data_plain_english
    assert audit.spy_data_recent_enough_for_last_year_observation is False
    assert audit.csgp_data_plain_english == (
        "EdgeLab does not currently see a local CSGP FirstRate CSV file."
    )
    assert audit.legacy_spy_summary is not None
    assert audit.legacy_spy_summary.filename == "SPY_1min_firstratedata.csv"
    assert audit.recent_spy_summary is None
    assert audit.recent_csgp_summary is None
    assert audit.recent_pair_has_enough_overlap is False
    assert "does not yet see recent SPY or CSGP" in audit.recent_pair_plain_english


def test_spy_csgp_audit_detects_recent_pair_and_prefers_it(tmp_path: Path) -> None:
    _write_firstrate_file(
        tmp_path / "SPY_1min_firstratedata.csv",
        _rows_for_date("2023-09-29", 430.0),
    )
    _write_firstrate_file(
        tmp_path / "SPY_recent_1min.csv",
        _rows_for_date("2026-06-22", 500.0),
    )
    _write_firstrate_file(
        tmp_path / "CSGP_recent_1min.csv",
        _rows_for_date("2026-06-22", 80.0),
    )
    provider = FirstRateLocalCSVHistoricalProvider(
        data_dir=tmp_path,
        normalizer=FirstRateHistoricalCSVNormalizer(
            adjustment_mode=HistoricalIntradayAdjustmentMode.UNADJUSTED
        ),
    )

    audit = SpyCsgpDataAuditService(provider=provider, as_of=date(2026, 6, 23)).run()

    assert audit.spy_data_found is True
    assert audit.csgp_data_found is True
    assert audit.legacy_spy_summary is not None
    assert audit.legacy_spy_summary.start_date == date(2023, 9, 29)
    assert audit.recent_spy_summary is not None
    assert audit.recent_spy_summary.start_date == date(2026, 6, 22)
    assert audit.recent_csgp_summary is not None
    assert audit.recent_csgp_summary.start_date == date(2026, 6, 22)
    assert audit.spy_summary == audit.recent_spy_summary
    assert audit.csgp_summary == audit.recent_csgp_summary
    assert audit.recent_pair_has_enough_overlap is True
    assert "overlapping dates" in audit.recent_pair_plain_english


def test_spy_csgp_audit_defines_required_data_and_study_plan(tmp_path: Path) -> None:
    audit = SpyCsgpDataAuditService(
        provider=_provider_with_spy_and_qqq(tmp_path),
        as_of=date(2026, 6, 23),
    ).run()

    required_symbols = {item.symbol for item in audit.required_files}
    assert required_symbols == {"SPY", "CSGP"}
    assert "SPY_recent_1min.csv" in audit.required_files[0].recommended_path
    assert audit.required_files[0].required_columns == [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
    assert "datetime" in audit.required_files[0].acceptable_alternative_columns
    assert "trailing 12 months" in audit.recommended_data_window
    assert "trailing 24 months" in audit.recommended_data_window
    assert {window.local_time_window for window in audit.morning_windows} >= {
        "9:30-9:45",
        "9:30-10:00",
        "9:30-10:30",
        "10:00-11:00",
    }
    assert "SPY down at least 1.00%" in audit.spy_weakness_thresholds
    assert "CSGP positive while SPY is negative" in audit.csgp_strength_thresholds
    assert "number of matching mornings" in audit.future_metrics
    assert "whether CSGP continues after 10:00" in audit.future_metrics


def test_spy_csgp_audit_is_local_read_only_and_needs_no_credentials(tmp_path: Path) -> None:
    audit = SpyCsgpDataAuditService(
        provider=_provider_with_spy_and_qqq(tmp_path),
        as_of=date(2026, 6, 23),
    ).run()

    assert audit.provider_supports_external_calls is False
    assert audit.provider_requires_credentials is False
    assert audit.no_live_data_requested is True
    assert audit.no_ai_or_model_calls is True
    assert audit.no_batch_results_saved is True
    assert audit.local_save_deferred is True
    assert audit.research_only_status == "Research only"
    assert audit.real_money_status == "Not allowed"


def test_spy_csgp_data_audit_api_and_ui_routes(monkeypatch, tmp_path: Path) -> None:
    service = SpyCsgpDataAuditService(
        provider=_provider_with_spy_and_qqq(tmp_path),
        as_of=date(2026, 6, 23),
    )
    monkeypatch.setattr(main, "spy_csgp_data_audit_service", service)

    api_response = client.get("/intraday/research/spy-csgp/data-audit")
    ui_response = client.get("/ui/intraday-lab/research/spy-csgp")
    research_response = client.get("/ui/intraday-lab/research")

    assert api_response.status_code == 200
    api_data = api_response.json()
    assert api_data["spy_data_found"] is True
    assert api_data["csgp_data_found"] is False
    assert api_data["provider_supports_external_calls"] is False
    assert api_data["provider_requires_credentials"] is False
    assert api_data["real_money_status"] == "Not allowed"

    assert ui_response.status_code == 200
    for phrase in [
        "SPY / CSGP Morning Data Audit",
        "Bottom line",
        "Exact data needed next",
        "SPY_recent_1min.csv",
        "CSGP_recent_1min.csv",
        "Recent SPY file",
        "Recent CSGP file",
        "Local MarketData.app download helper",
        "MARKETDATA_APP_TOKEN",
        "python -m edgelab.intraday.marketdata_app_downloader",
        "Open to 15 minutes",
        "SPY down at least 1.00%",
        "CSGP positive while SPY is negative",
        "What the future study should measure",
        "Evidence Details",
        "Real-money status:",
        "Not allowed",
    ]:
        assert phrase in ui_response.text
    for forbidden in [
        "Trade button",
        "place order",
        "paper ready",
        "live ready",
        "ready for real money",
    ]:
        assert forbidden.lower() not in ui_response.text.lower()

    assert research_response.status_code == 200
    assert "SPY / CSGP Morning Divergence Data Audit" in research_response.text


def _provider_with_spy_and_qqq(tmp_path: Path) -> FirstRateLocalCSVHistoricalProvider:
    _write_firstrate_file(
        tmp_path / "SPY_1min_firstratedata.csv",
        [
            *_rows_for_date("2023-09-28", 430.0),
            *_rows_for_date("2023-09-29", 431.0),
        ],
    )
    _write_firstrate_file(
        tmp_path / "QQQ_1min_firstratedata.csv",
        _rows_for_date("2023-09-29", 360.0),
    )
    return FirstRateLocalCSVHistoricalProvider(
        data_dir=tmp_path,
        normalizer=FirstRateHistoricalCSVNormalizer(
            adjustment_mode=HistoricalIntradayAdjustmentMode.UNADJUSTED
        ),
    )


def _rows_for_date(session_date: str, start_price: float) -> list[str]:
    return [
        (
            f"{session_date} 09:{30 + minute:02d}:00,"
            f"{start_price + minute:.2f},"
            f"{start_price + minute + 0.25:.2f},"
            f"{start_price + minute - 0.25:.2f},"
            f"{start_price + minute + 0.10:.2f},"
            f"{1000 + minute}"
        )
        for minute in range(5)
    ]


def _write_firstrate_file(path: Path, rows: list[str]) -> None:
    path.write_text("timestamp,open,high,low,close,volume\n" + "\n".join(rows) + "\n")
