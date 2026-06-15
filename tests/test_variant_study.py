from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from edgelab.intraday.csv_normalizers import FirstRateLocalCSVHistoricalProvider
from edgelab.intraday.variant_study import (
    ControlledVariantStudyService,
    controlled_variant_definitions,
)
from edgelab.intraday.variant_study_schema import (
    VariantBaselineComparison,
    VariantDefinition,
    VariantResultSummary,
    VariantStudyClassification,
    VariantStudyRequest,
    VariantStudyResult,
)
from edgelab.research_runs.schema import (
    ResearchRunCreateRequest,
)
from edgelab.research_runs.service import FirstRateResearchRunService
from edgelab.research_runs.store import SQLiteResearchRunStore


def test_variant_schema_rejects_unsafe_copy() -> None:
    with pytest.raises(ValueError):
        _sample_result(bottom_line="This variant is proven.")

    with pytest.raises(ValueError):
        _sample_result(bottom_line="Buy now because this variant looked cleaner.")


def test_variant_classification_values_are_conservative() -> None:
    values = {item.value for item in VariantStudyClassification}

    assert values == {
        "not_enough_examples",
        "blocked_by_data_quality",
        "too_noisy",
        "weaker_than_baseline",
        "similar_to_baseline",
        "interesting_but_unproven",
        "worth_more_testing",
    }
    assert all("ready" not in value for value in values)


def test_variant_definitions_are_fixed_and_compare_to_baseline() -> None:
    definitions = controlled_variant_definitions()

    assert [definition.variant_id for definition in definitions] == [
        "broad_baseline",
        "failed_push_from_above",
        "failed_selloff_from_below",
        "fast_failure",
        "slow_failure",
        "spy_qqq_disagreement",
    ]
    assert all(definition.plain_english_label for definition in definitions)
    assert all(definition.why_it_might_matter for definition in definitions)
    assert all(definition.real_money_status == "Not allowed" for definition in definitions)
    assert all(
        definition.baseline_compared_against == "broad_baseline" for definition in definitions
    )


def test_variant_service_requires_fresh_spy_without_creating_runs(tmp_path: Path) -> None:
    provider = _provider_with_variant_sessions(tmp_path)
    saved_run_service = FirstRateResearchRunService(
        store=SQLiteResearchRunStore(tmp_path / "runs.db"),
        provider=provider,
    )
    service = ControlledVariantStudyService(
        research_run_service=saved_run_service,
        provider=provider,
    )

    result = service.run()

    assert result.study_available is False
    assert result.classification == VariantStudyClassification.BLOCKED_BY_DATA_QUALITY
    assert result.real_money_status == "Not allowed"
    assert saved_run_service.list_runs() == []
    assert not (tmp_path / "runs.db").exists()


def test_variant_service_uses_saved_runs_and_process_cache(tmp_path: Path) -> None:
    provider = _provider_with_variant_sessions(tmp_path)
    saved_run_service = FirstRateResearchRunService(
        store=SQLiteResearchRunStore(tmp_path / "runs.db"),
        provider=provider,
    )
    saved_run_service.run_firstrate_many_morning(ResearchRunCreateRequest(symbol="SPY"))
    saved_run_service.run_firstrate_many_morning(ResearchRunCreateRequest(symbol="QQQ"))
    service = ControlledVariantStudyService(
        research_run_service=saved_run_service,
        provider=provider,
    )

    first = service.run()
    second = service.run()

    assert first.study_available is True
    assert first.real_money_status == "Not allowed"
    assert first.cache_metadata["cache_status"] == "fresh"
    assert second.cache_metadata["cache_status"] == "cached"
    by_id = {summary.variant_id: summary for summary in first.variant_summaries}
    assert by_id["broad_baseline"].examples_found >= 20
    assert by_id["failed_push_from_above"].examples_found > 0
    assert by_id["failed_selloff_from_below"].examples_found > 0
    assert by_id["fast_failure"].examples_found > 0
    assert by_id["slow_failure"].examples_found > 0
    assert by_id["spy_qqq_disagreement"].examples_found > 0
    assert (
        by_id["opening_gap_context_check"].conservative_classification
        == VariantStudyClassification.BLOCKED_BY_DATA_QUALITY
    )


def test_variant_service_blocks_only_disagreement_when_qqq_is_stale(tmp_path: Path) -> None:
    provider = _provider_with_variant_sessions(tmp_path)
    saved_run_service = FirstRateResearchRunService(
        store=SQLiteResearchRunStore(tmp_path / "runs.db"),
        provider=provider,
    )
    saved_run_service.run_firstrate_many_morning(ResearchRunCreateRequest(symbol="SPY"))
    saved_run_service.run_firstrate_many_morning(ResearchRunCreateRequest(symbol="QQQ"))
    (tmp_path / "QQQ_1min_firstratedata.csv").write_text(
        (tmp_path / "QQQ_1min_firstratedata.csv").read_text(encoding="utf-8")
        + _stable_session_rows(date(2024, 2, 20)),
        encoding="utf-8",
    )
    service = ControlledVariantStudyService(
        research_run_service=saved_run_service,
        provider=provider,
    )

    result = service.run()

    assert result.study_available is True
    by_id = {summary.variant_id: summary for summary in result.variant_summaries}
    assert by_id["broad_baseline"].examples_found > 0
    assert (
        by_id["spy_qqq_disagreement"].conservative_classification
        == VariantStudyClassification.BLOCKED_BY_DATA_QUALITY
    )
    assert any(issue.code == "paired_saved_run_missing_or_stale" for issue in result.quality_issues)


def _sample_result(
    *, bottom_line: str = "One fixed version looked interesting but still needs review."
) -> VariantStudyResult:
    definition = VariantDefinition(
        variant_id="broad_baseline",
        plain_english_label="Broad failed early move",
        rule_definition="All failed early move examples.",
        why_it_might_matter="It gives every version a fair comparison point.",
        what_would_disprove_it="The broad group is too mixed.",
    )
    comparison = VariantBaselineComparison(
        plain_english_summary="This is the broad comparison group."
    )
    summary = VariantResultSummary(
        variant_id=definition.variant_id,
        plain_english_label=definition.plain_english_label,
        rule_definition=definition.rule_definition,
        why_it_might_matter=definition.why_it_might_matter,
        examples_found=20,
        examples_completed=20,
        moved_as_expected_count=12,
        moved_against_test_count=8,
        did_not_move_enough_count=0,
        cost_changed_result_count=0,
        conservative_classification=VariantStudyClassification.INTERESTING_BUT_UNPROVEN,
        what_would_disprove_it=definition.what_would_disprove_it,
        baseline_comparison=comparison,
    )
    return VariantStudyResult(
        study_id="spy-early-move-failed-variant-study",
        request=VariantStudyRequest(),
        study_available=True,
        classification=VariantStudyClassification.INTERESTING_BUT_UNPROVEN,
        bottom_line=bottom_line,
        what_edgelab_tested="EdgeLab compared fixed versions of one local research idea.",
        what_looked_different="One version looked cleaner than the broad group.",
        which_version_deserves_more_testing="One version may deserve another research pass.",
        why_this_might_be_misleading="Small local groups can look cleaner by chance.",
        what_edgelab_should_test_next="Test the fixed version on more local data.",
        baseline_comparison=comparison,
        variant_summaries=[summary],
    )


def _provider_with_variant_sessions(tmp_path: Path) -> FirstRateLocalCSVHistoricalProvider:
    start = date(2024, 1, 2)
    spy_rows = []
    qqq_rows = []
    for index in range(24):
        session_date = start + timedelta(days=index)
        direction = "short" if index % 2 == 0 else "long"
        fail_minute = 6 if index < 12 else 22
        spy_rows.append(_variant_session_rows(session_date, direction, fail_minute))
        qqq_rows.append(_stable_session_rows(session_date))
    _write_firstrate_file(tmp_path / "SPY_1min_firstratedata.csv", "".join(spy_rows))
    _write_firstrate_file(tmp_path / "QQQ_1min_firstratedata.csv", "".join(qqq_rows))
    return FirstRateLocalCSVHistoricalProvider(tmp_path)


def _write_firstrate_file(path: Path, rows: str) -> None:
    path.write_text("timestamp,open,high,low,close,volume\n" + rows, encoding="utf-8")


def _variant_session_rows(session_date: date, direction: str, fail_minute: int) -> str:
    rows = []
    for minute_index in range(61):
        timestamp = _timestamp(session_date, minute_index)
        open_price = 100.0
        high = 100.4
        low = 99.6
        close = 100.0
        if minute_index == fail_minute:
            if direction == "short":
                high = 101.2
                close = 100.45
            else:
                low = 98.8
                close = 99.55
        elif minute_index == fail_minute + 1:
            if direction == "short":
                high = 100.4
                low = 99.7
                close = 99.8
            else:
                high = 100.3
                low = 99.6
                close = 100.2
        elif minute_index > fail_minute + 1:
            if direction == "short":
                high = 100.0
                low = 98.8
                close = 99.0
            else:
                high = 101.2
                low = 100.0
                close = 101.0
        rows.append(_row(timestamp, open_price, high, low, close))
    return "".join(rows)


def _stable_session_rows(session_date: date) -> str:
    rows = []
    for minute_index in range(61):
        timestamp = _timestamp(session_date, minute_index)
        rows.append(_row(timestamp, 100.0, 100.2, 99.8, 100.0))
    return "".join(rows)


def _timestamp(session_date: date, minute_index: int) -> str:
    parsed = datetime.combine(session_date, datetime.min.time()).replace(
        hour=9,
        minute=30,
    ) + timedelta(minutes=minute_index)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _row(timestamp: str, open_price: float, high: float, low: float, close: float) -> str:
    return f"{timestamp},{open_price:.2f},{high:.2f},{low:.2f},{close:.2f},1000\n"
