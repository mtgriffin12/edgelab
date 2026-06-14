from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from edgelab.app import main
from edgelab.intraday.csv_normalizers import (
    FirstRateHistoricalCSVNormalizer,
    FirstRateLocalCSVHistoricalProvider,
)
from edgelab.intraday.firstrate_replay import (
    CachedFirstRateHistoricalDataProvider,
    FirstHourCompletenessLabel,
    first_hour_completeness_for_import_result,
    summarize_first_hour_completeness,
)
from edgelab.intraday.historical_schema import HistoricalIntradayAdjustmentMode
from edgelab.intraday.pattern_results import MultiSessionPatternRunner
from edgelab.intraday.pattern_results_schema import PatternResultClassification
from edgelab.intraday.replay import HistoricalIntradayReplayEngine
from edgelab.intraday.replay_schema import HistoricalReplayRequest, HistoricalReplayStatus

client = TestClient(main.app)


def test_first_hour_completeness_labels_and_missing_timestamps(tmp_path: Path) -> None:
    provider = _provider_with_sessions(
        tmp_path,
        {
            "2024-01-02": _full_first_hour_rows("2024-01-02"),
            "2024-01-03": _first_hour_rows("2024-01-03", missing_minutes={7, 8}),
            "2024-01-04": _first_hour_rows("2024-01-04", missing_minutes=set(range(5, 15))),
            "2024-01-05": _first_hour_rows("2024-01-05", missing_minutes=set(range(5, 25))),
            "2024-01-06": [
                *_first_hour_rows("2024-01-06"),
                _row("2024-01-06 09:31:00"),
            ],
        },
    )

    result = provider.load_sessions("SPY", include_bars=True)
    completeness = first_hour_completeness_for_import_result(result)
    by_session = {item.session_id: item for item in completeness}

    assert (
        by_session["SPY-2024-01-02"].first_hour_completeness_label
        == FirstHourCompletenessLabel.COMPLETE
    )
    assert (
        by_session["SPY-2024-01-03"].first_hour_completeness_label
        == FirstHourCompletenessLabel.MINOR_GAPS
    )
    assert (
        by_session["SPY-2024-01-04"].first_hour_completeness_label
        == FirstHourCompletenessLabel.MAJOR_GAPS
    )
    assert (
        by_session["SPY-2024-01-05"].first_hour_completeness_label
        == FirstHourCompletenessLabel.REPLAY_UNSAFE
    )
    assert (
        by_session["SPY-2024-01-06"].first_hour_completeness_label
        == FirstHourCompletenessLabel.REPLAY_UNSAFE
    )
    assert len(by_session["SPY-2024-01-03"].missing_first_hour_timestamps_utc) == 2
    assert by_session["SPY-2024-01-03"].missing_first_hour_timestamps_utc[0].isoformat() == (
        "2024-01-03T14:37:00+00:00"
    )
    assert by_session["SPY-2024-01-06"].duplicate_first_hour_timestamps_utc == [
        datetime.fromisoformat("2024-01-06T14:31:00+00:00")
    ]

    summary = summarize_first_hour_completeness(completeness)
    assert summary.complete == 1
    assert summary.minor_gaps == 1
    assert summary.major_gaps == 1
    assert summary.replay_unsafe == 2


def test_firstrate_replay_bridge_uses_existing_replay_engine(tmp_path: Path) -> None:
    base_provider = _provider_with_sessions(
        tmp_path,
        {"2024-01-02": _full_first_hour_rows("2024-01-02")},
    )
    provider = CachedFirstRateHistoricalDataProvider(base_provider)
    engine = HistoricalIntradayReplayEngine(provider=provider)

    result = engine.replay(HistoricalReplayRequest(symbol="SPY", session_id="SPY-2024-01-02"))

    assert result.status in {HistoricalReplayStatus.COMPLETED, HistoricalReplayStatus.INCOMPLETE}
    assert result.research_only_status == "Research only"
    assert result.real_money_status == "Not allowed"
    assert result.steps
    for step in result.steps:
        if step.latest_visible_bar_utc is not None:
            assert step.latest_visible_bar_utc <= step.replay_time_utc
        visible = step.evidence_details.get("visible_bar_timestamps_utc", [])
        assert all(timestamp <= step.replay_time_utc for timestamp in visible)


def test_firstrate_many_morning_summary_uses_symbol_filter(tmp_path: Path) -> None:
    _write_firstrate_file(
        tmp_path / "SPY_1min_firstratedata.csv",
        _full_first_hour_rows("2024-01-02"),
    )
    _write_firstrate_file(
        tmp_path / "QQQ_1min_firstratedata.csv",
        _full_first_hour_rows("2024-01-03"),
    )
    provider = CachedFirstRateHistoricalDataProvider(_provider(tmp_path))
    engine = HistoricalIntradayReplayEngine(provider=provider)
    runner = MultiSessionPatternRunner(provider=provider, replay_engine=engine)

    summary = runner.run(main._multi_session_request(symbol="SPY"))

    assert summary.symbol == "SPY"
    assert summary.sessions_found == 1
    assert all(outcome.symbol == "SPY" for outcome in summary.session_outcomes)
    assert summary.real_money_status == "Not allowed"
    assert summary.classification == PatternResultClassification.NOT_ENOUGH_EXAMPLES
    assert "validated edge" not in summary.model_dump_json().lower()


def test_firstrate_replay_and_summary_api_routes(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        main,
        "firstrate_historical_provider",
        _provider_with_sessions(tmp_path, {"2024-01-02": _full_first_hour_rows("2024-01-02")}),
    )

    replay = client.get("/intraday/history/firstrate/SPY/sessions/SPY-2024-01-02/replay")
    card = client.get("/intraday/history/firstrate/SPY/sessions/SPY-2024-01-02/replay/card")
    summary = client.get("/intraday/history/firstrate/SPY/multi-session-summary")
    patterns = client.get("/intraday/history/firstrate/SPY/pattern-results")
    no_trade = client.get("/intraday/history/firstrate/SPY/no-trade-analysis")

    assert replay.status_code == 200
    replay_data = replay.json()
    assert replay_data["research_only_status"] == "Research only"
    assert replay_data["real_money_status"] == "Not allowed"
    assert replay_data["first_hour_completeness"]["first_hour_completeness_label"] == "complete"
    assert "buy now" not in replay.text.lower()

    assert card.status_code == 200
    assert "Past Morning Practice Test" in card.text
    assert "First-hour completeness" in card.text
    assert "Not allowed" in card.text

    for response in [summary, patterns, no_trade]:
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "SPY"
        assert data["real_money_status"] == "Not allowed"
        assert data["first_hour_completeness_summary"]["complete"] == 1
        assert data["cache_metadata"]["cache_status"] in {"fresh", "cached"}
        assert "validated edge" not in response.text.lower()


def test_firstrate_multi_session_api_reuses_cache(monkeypatch, tmp_path: Path) -> None:
    provider = _provider_with_sessions(
        tmp_path,
        {"2024-01-02": _full_first_hour_rows("2024-01-02")},
    )
    monkeypatch.setattr(main, "firstrate_historical_provider", provider)
    main._firstrate_multi_session_cache.clear()
    call_count = 0
    original_run = MultiSessionPatternRunner.run

    def counting_run(self: MultiSessionPatternRunner, request):
        nonlocal call_count
        call_count += 1
        return original_run(self, request)

    monkeypatch.setattr(MultiSessionPatternRunner, "run", counting_run)

    first = client.get("/intraday/history/firstrate/SPY/multi-session-summary")
    second = client.get("/intraday/history/firstrate/SPY/multi-session-summary")
    patterns = client.get("/intraday/history/firstrate/SPY/pattern-results")
    no_trade = client.get("/intraday/history/firstrate/SPY/no-trade-analysis")

    assert first.status_code == 200
    assert second.status_code == 200
    assert patterns.status_code == 200
    assert no_trade.status_code == 200
    assert first.json()["cache_metadata"]["cache_status"] == "fresh"
    assert second.json()["cache_metadata"]["cache_status"] == "cached"
    assert patterns.json()["cache_metadata"]["cache_status"] == "cached"
    assert no_trade.json()["cache_metadata"]["cache_status"] == "cached"
    assert call_count == 1


def test_firstrate_multi_session_cache_key_varies_and_invalidates(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _write_firstrate_file(
        tmp_path / "SPY_1min_firstratedata.csv",
        _full_first_hour_rows("2024-01-02"),
    )
    _write_firstrate_file(
        tmp_path / "QQQ_1min_firstratedata.csv",
        _full_first_hour_rows("2024-01-03"),
    )
    monkeypatch.setattr(main, "firstrate_historical_provider", _provider(tmp_path))
    main._firstrate_multi_session_cache.clear()
    call_count = 0
    original_run = MultiSessionPatternRunner.run

    def counting_run(self: MultiSessionPatternRunner, request):
        nonlocal call_count
        call_count += 1
        return original_run(self, request)

    monkeypatch.setattr(MultiSessionPatternRunner, "run", counting_run)

    assert client.get("/intraday/history/firstrate/SPY/multi-session-summary").status_code == 200
    assert client.get("/intraday/history/firstrate/SPY/multi-session-summary").status_code == 200
    assert call_count == 1

    assert client.get("/intraday/history/firstrate/QQQ/multi-session-summary").status_code == 200
    assert call_count == 2

    assert (
        client.get(
            "/intraday/history/firstrate/SPY/multi-session-summary?hold_minutes=7"
        ).status_code
        == 200
    )
    assert call_count == 3

    assert (
        client.get(
            "/intraday/history/firstrate/SPY/multi-session-summary?slippage_ticks=2"
        ).status_code
        == 200
    )
    assert call_count == 4

    assert (
        client.get(
            "/intraday/history/firstrate/SPY/multi-session-summary?commission_per_contract=1.25"
        ).status_code
        == 200
    )
    assert call_count == 5

    _write_firstrate_file(
        tmp_path / "SPY_1min_firstratedata.csv",
        [*_full_first_hour_rows("2024-01-02"), _row("2024-01-02 16:02:00")],
    )

    changed = client.get("/intraday/history/firstrate/SPY/multi-session-summary")

    assert changed.status_code == 200
    assert changed.json()["cache_metadata"]["cache_status"] == "fresh"
    assert call_count == 6


def test_firstrate_ui_pages_are_plain_and_research_only(monkeypatch, tmp_path: Path) -> None:
    _write_firstrate_file(
        tmp_path / "SPY_1min_firstratedata.csv",
        _full_first_hour_rows("2024-01-02"),
    )
    _write_firstrate_file(
        tmp_path / "QQQ_1min_firstratedata.csv",
        _full_first_hour_rows("2024-01-03"),
    )
    monkeypatch.setattr(main, "firstrate_historical_provider", _provider(tmp_path))

    paths = [
        "/ui/intraday-lab/firstrate",
        "/ui/intraday-lab/firstrate/SPY",
        "/ui/intraday-lab/firstrate/QQQ",
        "/ui/intraday-lab/firstrate/SPY/SPY-2024-01-02/replay",
        "/ui/intraday-lab/firstrate/SPY/multi-session-summary",
        "/ui/intraday-lab/firstrate/QQQ/multi-session-summary",
    ]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200
        assert "Bottom line" in response.text
        assert "What EdgeLab found" in response.text
        assert "What this means" in response.text
        assert "What to test next" in response.text
        assert "Real-money status: Not allowed" in response.text
        assert "Evidence details" in response.text
        assert "not live" in response.text.lower()
        assert "not a recommendation" in response.text.lower()
        assert "<button" not in response.text.lower()
        _assert_no_recommendation_or_overclaim(response.text)

    replay_response = client.get("/ui/intraday-lab/firstrate/SPY/SPY-2024-01-02/replay")
    assert replay_response.text.index("Internal replay status") > replay_response.text.index(
        "Evidence details"
    )
    assert replay_response.text.index("First-hour check") > replay_response.text.index(
        "Evidence details"
    )


def _provider_with_sessions(
    tmp_path: Path,
    rows_by_date: dict[str, list[dict[str, str]]],
) -> FirstRateLocalCSVHistoricalProvider:
    rows: list[dict[str, str]] = []
    for session_rows in rows_by_date.values():
        rows.extend(session_rows)
    _write_firstrate_file(tmp_path / "SPY_1min_firstratedata.csv", rows)
    return _provider(tmp_path)


def _assert_no_recommendation_or_overclaim(text: str) -> None:
    lowered = text.lower()
    forbidden_phrases = [
        "buy now",
        "sell now",
        "short now",
        "validated edge",
        "profitable",
        "reliable",
        "tradeable",
        "ready for real money",
        "real-money ready",
        "signal to act",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in lowered


def _provider(tmp_path: Path) -> FirstRateLocalCSVHistoricalProvider:
    return FirstRateLocalCSVHistoricalProvider(
        data_dir=tmp_path,
        normalizer=FirstRateHistoricalCSVNormalizer(
            adjustment_mode=HistoricalIntradayAdjustmentMode.UNADJUSTED
        ),
    )


def _full_first_hour_rows(session_date: str) -> list[dict[str, str]]:
    return _first_hour_rows(session_date)


def _first_hour_rows(
    session_date: str,
    *,
    missing_minutes: set[int] | None = None,
) -> list[dict[str, str]]:
    missing_minutes = missing_minutes or set()
    rows = [_row(f"{session_date} 08:00:00")]
    for minute in range(60):
        if minute in missing_minutes:
            continue
        hour = 9 if minute < 30 else 10
        minute_in_hour = 30 + minute if minute < 30 else minute - 30
        rows.append(_row(f"{session_date} {hour:02d}:{minute_in_hour:02d}:00"))
    rows.append(_row(f"{session_date} 10:30:00"))
    rows.append(_row(f"{session_date} 16:01:00"))
    return rows


def _write_firstrate_file(path: Path, rows: list[dict[str, str]]) -> None:
    header = "timestamp,open,high,low,close,volume\n"
    lines = [
        f"{row['timestamp']},{row['open']},{row['high']},{row['low']},{row['close']},{row['volume']}"
        for row in rows
    ]
    path.write_text(header + "\n".join(lines) + "\n")


def _row(
    timestamp: str,
    *,
    open_price: str = "100.00",
    high: str = "100.60",
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
