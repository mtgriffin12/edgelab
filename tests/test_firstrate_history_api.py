from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from edgelab.app import main
from edgelab.intraday.csv_normalizers import (
    FirstRateHistoricalCSVNormalizer,
    FirstRateLocalCSVHistoricalProvider,
)
from edgelab.intraday.historical_schema import HistoricalIntradayAdjustmentMode

client = TestClient(main.app)


def test_firstrate_files_endpoint(monkeypatch, tmp_path: Path) -> None:
    provider = _provider_with_sample(tmp_path)
    monkeypatch.setattr(main, "firstrate_historical_provider", provider)

    response = client.get("/intraday/history/firstrate/files")

    assert response.status_code == 200
    data = response.json()
    assert data["research_only_status"] == "Research only"
    assert data["real_money_status"] == "Not allowed"
    assert data["files_found"] == 1
    assert data["files"][0]["symbol"] == "SPY"


def test_firstrate_dry_run_endpoint(monkeypatch, tmp_path: Path) -> None:
    provider = _provider_with_sample(tmp_path)
    monkeypatch.setattr(main, "firstrate_historical_provider", provider)

    response = client.get("/intraday/history/firstrate/dry-run")

    assert response.status_code == 200
    data = response.json()
    assert data["files_found"] == 1
    assert data["symbols_detected"] == ["SPY"]
    assert data["row_count"] == 5
    assert data["readiness_counts"]["ready_for_replay"] == 1
    assert data["research_only_status"] == "Research only"
    assert data["real_money_status"] == "Not allowed"
    assert "real-money status is Not allowed" in data["plain_english_summary"]


def test_firstrate_symbol_sessions_endpoint(monkeypatch, tmp_path: Path) -> None:
    provider = _provider_with_sample(tmp_path)
    monkeypatch.setattr(main, "firstrate_historical_provider", provider)

    response = client.get("/intraday/history/firstrate/SPY/sessions")

    assert response.status_code == 200
    data = response.json()
    assert data["sessions"][0]["session_id"] == "SPY-2024-01-02"
    assert data["sessions"][0]["readiness"] == "ready_for_replay"
    assert data["bars_loaded"] == 0
    assert data["real_money_status"] == "Not allowed"


def test_firstrate_session_detail_endpoint(monkeypatch, tmp_path: Path) -> None:
    provider = _provider_with_sample(tmp_path)
    monkeypatch.setattr(main, "firstrate_historical_provider", provider)

    response = client.get("/intraday/history/firstrate/SPY/sessions/SPY-2024-01-02")

    assert response.status_code == 200
    data = response.json()
    assert data["sessions"][0]["session_id"] == "SPY-2024-01-02"
    assert data["bars_loaded"] == 5
    assert "bars" not in data
    assert data["research_only_status"] == "Research only"
    assert data["real_money_status"] == "Not allowed"


def test_firstrate_missing_session_returns_404(monkeypatch, tmp_path: Path) -> None:
    provider = _provider_with_sample(tmp_path)
    monkeypatch.setattr(main, "firstrate_historical_provider", provider)

    response = client.get("/intraday/history/firstrate/SPY/sessions/missing-session")

    assert response.status_code == 404


def _provider_with_sample(tmp_path: Path) -> FirstRateLocalCSVHistoricalProvider:
    path = tmp_path / "SPY_1min_firstratedata.csv"
    rows = [
        "2024-01-02 09:30:00,100.00,100.50,99.90,100.25,1000",
        "2024-01-02 09:31:00,100.25,100.60,100.10,100.50,1001",
        "2024-01-02 09:32:00,100.50,100.70,100.20,100.45,1002",
        "2024-01-02 09:33:00,100.45,100.80,100.30,100.70,1003",
        "2024-01-02 09:34:00,100.70,100.90,100.40,100.55,1004",
    ]
    path.write_text("timestamp,open,high,low,close,volume\n" + "\n".join(rows) + "\n")
    return FirstRateLocalCSVHistoricalProvider(
        data_dir=tmp_path,
        normalizer=FirstRateHistoricalCSVNormalizer(
            adjustment_mode=HistoricalIntradayAdjustmentMode.UNADJUSTED
        ),
    )
