from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from edgelab.app import main
from edgelab.intraday.csv_normalizers import FirstRateLocalCSVHistoricalProvider
from edgelab.research_runs.schema import (
    ResearchRunCreateRequest,
    ResearchRunFreshnessStatus,
    ResearchRunStatus,
    ResearchRunType,
    SavedResearchRun,
)
from edgelab.research_runs.service import (
    FirstRateResearchRunService,
    ResearchRunSourceMissingError,
)
from edgelab.research_runs.store import SQLiteResearchRunStore

client = TestClient(main.app)


def test_saved_research_run_schema_normalizes_symbol_and_rejects_unsafe_copy() -> None:
    request = ResearchRunCreateRequest(symbol="spy")

    assert request.symbol == "SPY"

    with pytest.raises(ValueError):
        _sample_run(
            "unsafe",
            plain_english_bottom_line="This result is ready for real money.",
        )

    with pytest.raises(ValueError):
        _sample_run(
            "overconfident",
            plain_english_bottom_line="This setup is proven by the sample.",
        )


def test_research_run_store_creates_reads_lists_and_finds_latest(tmp_path: Path) -> None:
    store = SQLiteResearchRunStore(tmp_path / "runs.db")
    older = _sample_run("older", completed_at=datetime(2024, 1, 1, tzinfo=UTC))
    newer = _sample_run("newer", completed_at=datetime(2024, 1, 2, tzinfo=UTC))

    assert store.list() == []

    store.insert(older)
    store.insert(newer)

    assert store.get("older") == older
    listed = store.list(symbol="spy")
    assert [run.run_id for run in listed] == ["newer", "older"]
    latest = store.get_latest_matching(ResearchRunCreateRequest(symbol="SPY"))
    assert latest is not None
    assert latest.run_id == "newer"
    assert (
        store.get_latest_matching(ResearchRunCreateRequest(symbol="SPY", hold_minutes=10)) is None
    )


def test_research_run_freshness_detects_source_and_schema_changes(tmp_path: Path) -> None:
    provider = _provider_with_sessions(tmp_path, "SPY")
    store = SQLiteResearchRunStore(tmp_path / "runs.db")
    service = FirstRateResearchRunService(store=store, provider=provider)

    run = service.run_firstrate_many_morning(ResearchRunCreateRequest(symbol="SPY"))
    assert service.freshness_for_run(run).status == ResearchRunFreshnessStatus.FRESH

    csv_path = tmp_path / "SPY_1min_firstratedata.csv"
    csv_path.write_text(
        csv_path.read_text(encoding="utf-8") + _row("2024-01-02 10:31:00"), encoding="utf-8"
    )
    assert service.freshness_for_run(run).status == ResearchRunFreshnessStatus.STALE
    assert service.freshness_for_run(run).message == (
        "This saved result may be stale because the source file changed."
    )

    stale_schema = run.model_copy(update={"schema_version": "older_schema"})
    assert service.freshness_for_run(stale_schema).status == ResearchRunFreshnessStatus.STALE


def test_firstrate_research_run_service_saves_compact_result(tmp_path: Path) -> None:
    service = FirstRateResearchRunService(
        store=SQLiteResearchRunStore(tmp_path / "runs.db"),
        provider=_provider_with_sessions(tmp_path, "SPY"),
    )

    run = service.run_firstrate_many_morning(ResearchRunCreateRequest(symbol="SPY"))

    assert run.symbol == "SPY"
    assert run.run_status == ResearchRunStatus.COMPLETED
    assert run.research_only_status == "Research only"
    assert run.real_money_status == "Not allowed"
    assert run.evidence_details["sessions_found"] == 1
    assert "session_outcomes" not in run.summary_result
    assert run.source_file_path.endswith("SPY_1min_firstratedata.csv")
    assert "validated edge" not in run.model_dump_json().lower()


def test_firstrate_research_run_service_missing_source_does_not_save(tmp_path: Path) -> None:
    store = SQLiteResearchRunStore(tmp_path / "runs.db")
    service = FirstRateResearchRunService(
        store=store, provider=FirstRateLocalCSVHistoricalProvider(tmp_path)
    )

    with pytest.raises(ResearchRunSourceMissingError):
        service.run_firstrate_many_morning(ResearchRunCreateRequest(symbol="SPY"))

    assert store.list() == []
    assert not store.db_path.exists()


def test_research_run_api_and_ui_routes(monkeypatch, tmp_path: Path) -> None:
    service = FirstRateResearchRunService(
        store=SQLiteResearchRunStore(tmp_path / "runs.db"),
        provider=_provider_with_sessions(tmp_path, "SPY"),
    )
    monkeypatch.setattr(main, "research_run_service", service)

    empty_page = client.get("/ui/intraday-lab/firstrate/SPY/latest-result")
    assert empty_page.status_code == 200
    assert "No saved local result matches SPY yet." in empty_page.text
    assert "Run local analysis" in empty_page.text
    assert "Real-money status: Not allowed" in empty_page.text

    created = client.post("/intraday/research-runs/firstrate/SPY")
    assert created.status_code == 200
    created_json = created.json()
    run_id = created_json["run"]["run_id"]
    assert created_json["run"]["real_money_status"] == "Not allowed"
    assert created_json["freshness"]["status"] == "fresh"

    listed = client.get("/intraday/research-runs?symbol=SPY")
    latest = client.get("/intraday/research-runs/latest?symbol=SPY")
    detail = client.get(f"/intraday/research-runs/{run_id}")
    card = client.get(f"/intraday/research-runs/{run_id}/card")
    list_page = client.get("/ui/intraday-lab/research-runs")
    detail_page = client.get(f"/ui/intraday-lab/research-runs/{run_id}")
    latest_page = client.get("/ui/intraday-lab/firstrate/SPY/latest-result")

    for response in [listed, latest, detail, card, list_page, detail_page, latest_page]:
        assert response.status_code == 200
        assert "Not allowed" in response.text
        assert "buy now" not in response.text.lower()
        assert "ready for real money" not in response.text.lower()

    assert "Saved Research Runs" in list_page.text
    assert "Bottom line" in detail_page.text
    assert "What EdgeLab tested" in detail_page.text
    assert "Evidence details" in detail_page.text
    assert "Latest Saved Result" in latest_page.text


def test_processed_and_raw_data_are_not_tracked() -> None:
    result = subprocess.run(
        ["git", "ls-files", "data/raw", "data/processed"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=True,
    )

    assert result.stdout == ""


def _sample_run(
    run_id: str,
    *,
    completed_at: datetime | None = None,
    plain_english_bottom_line: str = "Not enough examples yet for this local saved result.",
) -> SavedResearchRun:
    timestamp = completed_at or datetime(2024, 1, 1, 12, tzinfo=UTC)
    return SavedResearchRun(
        run_id=run_id,
        run_type=ResearchRunType.FIRSTRATE_MANY_MORNING_REPLAY,
        symbol="SPY",
        source_name="FirstRate Local CSV Historical Provider",
        source_file_path="/tmp/SPY_1min_firstratedata.csv",
        source_file_size=123,
        source_file_modified_time=456,
        source_data_fingerprint="fingerprint",
        start_date=None,
        end_date=None,
        hold_minutes=5,
        slippage_ticks=1,
        commission_per_contract=0,
        run_status=ResearchRunStatus.COMPLETED,
        started_at=timestamp,
        completed_at=timestamp,
        elapsed_ms=10,
        summary_result={"sessions_found": 1},
        first_hour_completeness_summary={"complete": 1},
        evidence_details={"sessions_found": 1, "sessions_tested": 1, "usable_sessions": 1},
        quality_issues=[],
        plain_english_bottom_line=plain_english_bottom_line,
        what_edgelab_tested="EdgeLab tested one local FirstRate morning in practice mode.",
        what_edgelab_found="The sample is too small to trust.",
        is_this_enough_to_trust="No. This local saved result needs more examples.",
        what_to_test_next="Test more local mornings and review source quality.",
    )


def _provider_with_sessions(tmp_path: Path, symbol: str) -> FirstRateLocalCSVHistoricalProvider:
    _write_firstrate_file(
        tmp_path / f"{symbol}_1min_firstratedata.csv",
        "".join(_row(f"2024-01-02 09:{minute:02d}:00") for minute in range(30, 60))
        + "".join(_row(f"2024-01-02 10:{minute:02d}:00") for minute in range(0, 31)),
    )
    return FirstRateLocalCSVHistoricalProvider(tmp_path)


def _write_firstrate_file(path: Path, rows: str) -> None:
    path.write_text("timestamp,open,high,low,close,volume\n" + rows, encoding="utf-8")


def _row(timestamp: str) -> str:
    return f"{timestamp},100,101,99,100.5,1000\n"
