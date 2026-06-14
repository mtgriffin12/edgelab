from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from edgelab.intraday.comparative_study import SpyQqqComparativeStudyService
from edgelab.intraday.comparative_study_schema import (
    ComparativeStudyClassification,
    ComparativeStudyRequest,
    ComparativeStudyResult,
    SetupFamilyComparison,
    SymbolComparisonSummary,
)
from edgelab.intraday.csv_normalizers import FirstRateLocalCSVHistoricalProvider
from edgelab.intraday.schema import IntradaySetupType
from edgelab.research_runs.schema import (
    ResearchRunCreateRequest,
    ResearchRunFreshnessStatus,
)
from edgelab.research_runs.service import FirstRateResearchRunService
from edgelab.research_runs.store import SQLiteResearchRunStore


def test_comparative_schema_rejects_unsafe_copy() -> None:
    with pytest.raises(ValueError):
        _sample_result(bottom_line="This comparison is proven.")

    with pytest.raises(ValueError):
        _sample_result(bottom_line="Buy now because SPY looked better.")


def test_comparative_classification_values_are_conservative() -> None:
    values = {item.value for item in ComparativeStudyClassification}

    assert {
        "similar_behavior",
        "symbol_difference_needs_review",
        "spy_more_interesting",
        "qqq_more_interesting",
        "too_noisy_to_compare",
        "not_enough_evidence",
        "blocked_by_data_quality",
    } == values
    assert all("ready" not in value for value in values)


def test_comparative_service_returns_missing_saved_run_state_without_creating_runs(
    tmp_path: Path,
) -> None:
    provider = _provider_with_sessions(tmp_path)
    service = FirstRateResearchRunService(
        store=SQLiteResearchRunStore(tmp_path / "runs.db"),
        provider=provider,
    )
    comparative_service = SpyQqqComparativeStudyService(
        research_run_service=service,
        provider=provider,
    )

    result = comparative_service.compare()

    assert result.comparison_available is False
    assert result.classification == ComparativeStudyClassification.NOT_ENOUGH_EVIDENCE
    assert result.real_money_status == "Not allowed"
    assert "Run local analysis" in result.what_edgelab_should_test_next
    assert service.list_runs() == []
    assert not (tmp_path / "runs.db").exists()


def test_comparative_service_uses_fresh_saved_runs_and_process_cache(tmp_path: Path) -> None:
    provider = _provider_with_sessions(tmp_path)
    saved_run_service = FirstRateResearchRunService(
        store=SQLiteResearchRunStore(tmp_path / "runs.db"),
        provider=provider,
    )
    saved_run_service.run_firstrate_many_morning(ResearchRunCreateRequest(symbol="SPY"))
    saved_run_service.run_firstrate_many_morning(ResearchRunCreateRequest(symbol="QQQ"))
    comparative_service = SpyQqqComparativeStudyService(
        research_run_service=saved_run_service,
        provider=provider,
    )

    first = comparative_service.compare()
    second = comparative_service.compare()

    assert first.comparison_available is True
    assert first.real_money_status == "Not allowed"
    assert {summary.symbol for summary in first.setup_family_comparison.symbol_summaries} == {
        "SPY",
        "QQQ",
    }
    assert all(
        summary.saved_run_freshness == ResearchRunFreshnessStatus.FRESH
        for summary in first.setup_family_comparison.symbol_summaries
    )
    assert first.cache_metadata["cache_status"] == "fresh"
    assert second.cache_metadata["cache_status"] == "cached"


def test_comparative_service_detects_stale_saved_run(tmp_path: Path) -> None:
    provider = _provider_with_sessions(tmp_path)
    saved_run_service = FirstRateResearchRunService(
        store=SQLiteResearchRunStore(tmp_path / "runs.db"),
        provider=provider,
    )
    saved_run_service.run_firstrate_many_morning(ResearchRunCreateRequest(symbol="SPY"))
    saved_run_service.run_firstrate_many_morning(ResearchRunCreateRequest(symbol="QQQ"))
    (tmp_path / "SPY_1min_firstratedata.csv").write_text(
        (tmp_path / "SPY_1min_firstratedata.csv").read_text(encoding="utf-8")
        + _row("2024-01-03 10:31:00"),
        encoding="utf-8",
    )
    comparative_service = SpyQqqComparativeStudyService(
        research_run_service=saved_run_service,
        provider=provider,
    )

    result = comparative_service.compare()

    assert result.comparison_available is False
    assert any(
        summary.symbol == "SPY" and summary.saved_run_freshness == ResearchRunFreshnessStatus.STALE
        for summary in result.setup_family_comparison.symbol_summaries
    )


def _sample_result(
    *, bottom_line: str = "SPY looked more interesting but still needs review."
) -> ComparativeStudyResult:
    symbol_summaries = [
        SymbolComparisonSummary(
            symbol="SPY",
            saved_run_freshness=ResearchRunFreshnessStatus.FRESH,
            saved_run_message="This saved result still matches the local source file.",
            comparison_available=True,
            sessions_tested=30,
            usable_sessions=30,
            possible_setup_count=12,
            sit_out_count=5,
            completed_pretend_result_count=12,
            helpful_afterward_count=7,
            wrong_way_afterward_count=5,
            flat_afterward_count=0,
            incomplete_pretend_result_count=0,
            setup_classification="interesting_but_unproven",
            plain_english_summary="SPY had enough local examples to review.",
        ),
        SymbolComparisonSummary(
            symbol="QQQ",
            saved_run_freshness=ResearchRunFreshnessStatus.FRESH,
            saved_run_message="This saved result still matches the local source file.",
            comparison_available=True,
            sessions_tested=30,
            usable_sessions=30,
            possible_setup_count=12,
            sit_out_count=5,
            completed_pretend_result_count=12,
            helpful_afterward_count=5,
            wrong_way_afterward_count=7,
            flat_afterward_count=0,
            incomplete_pretend_result_count=0,
            setup_classification="weak_or_inconsistent",
            plain_english_summary="QQQ had enough local examples to review.",
        ),
    ]
    comparison = SetupFamilyComparison(
        setup_family=IntradaySetupType.OPENING_RANGE_FAILURE,
        classification=ComparativeStudyClassification.SPY_MORE_INTERESTING,
        symbol_summaries=symbol_summaries,
        bottom_line=bottom_line,
        what_edgelab_compared="EdgeLab compared failed early moves in SPY and QQQ.",
        what_looked_different="SPY looked more interesting than QQQ in the local sample.",
        why_that_might_matter="The difference can guide the next research test.",
        why_this_might_be_misleading="This is one local historical sample with simple rules.",
        what_edgelab_should_test_next="Compare opening gap size and first-hour range width.",
    )
    return ComparativeStudyResult(
        study_id="spy-qqq-opening-range-failure",
        request=ComparativeStudyRequest(),
        comparison_available=True,
        classification=ComparativeStudyClassification.SPY_MORE_INTERESTING,
        setup_family_comparison=comparison,
        bottom_line=comparison.bottom_line,
        what_edgelab_compared=comparison.what_edgelab_compared,
        what_looked_different=comparison.what_looked_different,
        why_that_might_matter=comparison.why_that_might_matter,
        why_this_might_be_misleading=comparison.why_this_might_be_misleading,
        what_edgelab_should_test_next=comparison.what_edgelab_should_test_next,
    )


def _provider_with_sessions(tmp_path: Path) -> FirstRateLocalCSVHistoricalProvider:
    for symbol in ["SPY", "QQQ"]:
        _write_firstrate_file(
            tmp_path / f"{symbol}_1min_firstratedata.csv",
            "".join(_row(f"2024-01-02 09:{minute:02d}:00") for minute in range(30, 60))
            + "".join(_row(f"2024-01-02 10:{minute:02d}:00") for minute in range(0, 31)),
        )
    return FirstRateLocalCSVHistoricalProvider(tmp_path)


def _write_firstrate_file(path: Path, rows: str) -> None:
    path.write_text("timestamp,open,high,low,close,volume\n" + rows, encoding="utf-8")


def _row(timestamp: str) -> str:
    parsed = datetime.fromisoformat(timestamp).replace(tzinfo=UTC)
    close = 100.5 if parsed.minute % 2 == 0 else 99.5
    return f"{timestamp},100,101,99,{close},1000\n"
