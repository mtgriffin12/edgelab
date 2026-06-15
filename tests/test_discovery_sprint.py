from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from edgelab.intraday.csv_normalizers import FirstRateLocalCSVHistoricalProvider
from edgelab.intraday.discovery_sprint import DiscoverySprintService
from edgelab.intraday.discovery_sprint_schema import (
    AIProposedIntradayIdea,
    DiscoverySprintClassification,
    DiscoverySprintRequest,
    SupportedRuleFamily,
)


def test_discovery_sprint_runs_all_fixed_ideas_without_saving_runs(tmp_path: Path) -> None:
    provider = _provider_with_discovery_sessions(tmp_path)
    metadata_only = provider.load_sessions("SPY")
    service = DiscoverySprintService(provider=provider)

    first = service.run(DiscoverySprintRequest(minimum_useful_sessions=8, minimum_examples=4))
    second = service.run(DiscoverySprintRequest(minimum_useful_sessions=8, minimum_examples=4))

    assert len(metadata_only.sessions) > 0
    assert metadata_only.bars == []
    assert first.strategy_count == 8
    assert len(first.strategy_results) == 8
    assert first.symbols_tested == ["QQQ", "SPY"]
    assert first.real_money_status == "Not allowed"
    assert first.research_only_status == "Research only"
    assert first.cache_metadata["cache_status"] == "computed"
    assert second.cache_metadata["cache_status"] == "cached"
    assert not (tmp_path / "runs.db").exists()
    assert any(
        instrument.sessions_tested > 0
        and instrument.usable_sessions > 0
        and instrument.completed_examples > 0
        for strategy in first.strategy_results
        for instrument in strategy.instrument_results
    )
    assert not all(
        strategy.classification == DiscoverySprintClassification.DATA_PROBLEM
        for strategy in first.strategy_results
    )
    failed = service.strategy_result("failed-early-move")
    assert failed is not None
    assert failed.classification == DiscoverySprintClassification.DID_NOT_HOLD_UP_LATER
    assert failed.real_money_status == "Not allowed"


def test_discovery_sprint_request_normalizes_symbols(tmp_path: Path) -> None:
    provider = _provider_with_discovery_sessions(tmp_path)
    service = DiscoverySprintService(provider=provider)

    result = service.run(
        DiscoverySprintRequest(
            symbols=("spy", "SPY", "qqq"),
            minimum_useful_sessions=8,
            minimum_examples=4,
        )
    )

    assert result.symbols_tested == ["SPY", "QQQ"]


def test_ai_idea_schema_rejects_unsupported_or_unsafe_specs() -> None:
    base = {
        "proposed_id": "future-gap-fade-check",
        "proposed_name": "Future Gap Fade Check",
        "plain_english_hypothesis": (
            "A local gap that comes back toward the prior reference level may be worth testing."
        ),
        "supported_rule_family": SupportedRuleFamily.GAP_FADE,
        "instruments_to_test": ("spy", "qqq"),
        "required_data": "Local one-minute first-hour bars.",
        "fixed_rule_definition": "Use fixed settings before looking at results.",
        "allowed_parameters": ("gap_size_bucket",),
        "disallowed_parameters": ("manual result review",),
        "expected_failure_modes": ("Needs more examples",),
        "reason_to_test": "It is simple and can be checked locally.",
        "safety_notes": "AI may propose the hypothesis only.",
    }

    safe = AIProposedIntradayIdea(**base)

    assert safe.instruments_to_test == ("SPY", "QQQ")
    with pytest.raises(ValidationError):
        AIProposedIntradayIdea(
            **{
                **base,
                "supported_rule_family": "visual_chart_pattern",
            }
        )
    with pytest.raises(ValueError):
        AIProposedIntradayIdea(
            **{
                **base,
                "plain_english_hypothesis": "This will work on more history.",
            }
        )
    with pytest.raises(ValueError):
        AIProposedIntradayIdea(
            **{
                **base,
                "fixed_rule_definition": "Change thresholds after seeing results.",
            }
        )


def _provider_with_discovery_sessions(tmp_path: Path) -> FirstRateLocalCSVHistoricalProvider:
    spy_rows = []
    qqq_rows = []
    start = date(2022, 12, 12)
    for index in range(16):
        session_date = start + timedelta(days=index)
        spy_rows.append(_failed_push_session_rows(session_date))
        qqq_rows.append(_failed_selloff_session_rows(session_date))
    _write_firstrate_file(tmp_path / "SPY_1min_firstratedata.csv", "".join(spy_rows))
    _write_firstrate_file(tmp_path / "QQQ_1min_firstratedata.csv", "".join(qqq_rows))
    return FirstRateLocalCSVHistoricalProvider(tmp_path)


def _write_firstrate_file(path: Path, rows: str) -> None:
    path.write_text("timestamp,open,high,low,close,volume\n" + rows, encoding="utf-8")


def _failed_push_session_rows(session_date: date) -> str:
    rows = []
    for minute_index in range(61):
        open_price = 100.0
        high = 100.4
        low = 99.6
        close = 100.0
        if minute_index == 6:
            high = 101.2
            close = 100.45
        elif minute_index > 7:
            low = 98.8
            close = 99.0
        rows.append(_row(_timestamp(session_date, minute_index), open_price, high, low, close))
    return "".join(rows)


def _failed_selloff_session_rows(session_date: date) -> str:
    rows = []
    for minute_index in range(61):
        open_price = 100.0
        high = 100.4
        low = 99.6
        close = 100.0
        if minute_index == 6:
            low = 98.8
            close = 99.55
        elif minute_index > 7:
            high = 101.2
            close = 101.0
        rows.append(_row(_timestamp(session_date, minute_index), open_price, high, low, close))
    return "".join(rows)


def _timestamp(session_date: date, minute_index: int) -> str:
    parsed = datetime.combine(session_date, datetime.min.time()).replace(
        hour=9,
        minute=30,
    ) + timedelta(minutes=minute_index)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _row(timestamp: str, open_price: float, high: float, low: float, close: float) -> str:
    return f"{timestamp},{open_price:.2f},{high:.2f},{low:.2f},{close:.2f},1000\n"
