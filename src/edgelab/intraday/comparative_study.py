"""Local SPY/QQQ comparative pattern studies."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Protocol

from edgelab.intraday.csv_normalizers import FirstRateLocalCSVHistoricalProvider
from edgelab.intraday.firstrate_replay import (
    CachedFirstRateHistoricalDataProvider,
    summarize_first_hour_completeness,
)
from edgelab.intraday.historical_schema import utc_now
from edgelab.intraday.pattern_results import MultiSessionPatternRunner
from edgelab.intraday.pattern_results_schema import (
    MultiSessionReplayRequest,
    MultiSessionReplaySummary,
    PatternResultClassification,
    ReplayResultBucket,
    ReplaySessionOutcome,
    SetupTypeSummary,
)
from edgelab.intraday.replay import HistoricalIntradayReplayEngine
from edgelab.intraday.schema import IntradaySetupType, normalize_symbol
from edgelab.intraday.setups import IntradaySetupDetector
from edgelab.research_runs.schema import (
    ResearchRunCreateRequest,
    ResearchRunFreshness,
    ResearchRunFreshnessStatus,
    ResearchRunType,
    SavedResearchRun,
)
from edgelab.research_runs.service import FirstRateResearchRunService

from .comparative_study_schema import (
    COMPARATIVE_STUDY_CODE_VERSION,
    ComparativeStudyClassification,
    ComparativeStudyQualityIssue,
    ComparativeStudyRequest,
    ComparativeStudyResult,
    SetupFamilyComparison,
    SymbolComparisonSummary,
)


class FirstRateSavedRunServiceProtocol(Protocol):
    """Small protocol for saved-run freshness lookups."""

    def latest_with_freshness(
        self,
        request: ResearchRunCreateRequest,
    ) -> tuple[SavedResearchRun | None, ResearchRunFreshness]:
        """Return latest matching run with freshness."""
        ...


@dataclass(frozen=True)
class ComparativeStudyCacheKey:
    """Process-local cache key for local comparative studies."""

    symbols: tuple[str, str]
    setup_family: IntradaySetupType
    start_date: object
    end_date: object
    hold_minutes: int
    slippage_ticks: int
    commission_per_contract: float
    file_signature: tuple[tuple[str, int, int], ...]
    code_version: str


@dataclass(frozen=True)
class ComparativeStudyCacheEntry:
    """Cached comparative study result."""

    result: ComparativeStudyResult
    computed_at: str
    elapsed_ms: int


class SpyQqqComparativeStudyService:
    """Build a conservative SPY/QQQ Opening Range Failure comparison."""

    def __init__(
        self,
        *,
        research_run_service: FirstRateSavedRunServiceProtocol | None = None,
        provider: FirstRateLocalCSVHistoricalProvider | None = None,
        setup_detector: IntradaySetupDetector | None = None,
    ) -> None:
        self.provider = provider or FirstRateLocalCSVHistoricalProvider()
        self.research_run_service = research_run_service or FirstRateResearchRunService(
            provider=self.provider
        )
        self.setup_detector = setup_detector or IntradaySetupDetector()
        self._cached_provider = CachedFirstRateHistoricalDataProvider(self.provider)
        self._cache: dict[ComparativeStudyCacheKey, ComparativeStudyCacheEntry] = {}

    def compare(self, request: ComparativeStudyRequest | None = None) -> ComparativeStudyResult:
        """Return a local read-only comparative study result."""

        request = request or ComparativeStudyRequest()
        saved_states = self._saved_run_states(request)
        missing_or_stale = [
            state
            for state in saved_states.values()
            if state[1].status != ResearchRunFreshnessStatus.FRESH
        ]
        if missing_or_stale:
            return self._unavailable_result(request, saved_states)

        cache_key = self._cache_key(request)
        cached_entry = self._cache.get(cache_key)
        if cached_entry is not None:
            return cached_entry.result.model_copy(
                update={
                    "cache_metadata": {
                        "cache_status": "cached",
                        "computed_at": cached_entry.computed_at,
                        "elapsed_ms": cached_entry.elapsed_ms,
                    }
                }
            )

        started_at = perf_counter()
        summaries = self._run_symbol_summaries(request)
        result = self._result_from_summaries(
            request=request,
            saved_states=saved_states,
            summaries=summaries,
            cache_status="fresh",
            computed_at=utc_now().isoformat(),
            elapsed_ms=round((perf_counter() - started_at) * 1000),
        )
        self._cache[cache_key] = ComparativeStudyCacheEntry(
            result=result,
            computed_at=str(result.cache_metadata["computed_at"]),
            elapsed_ms=int(result.cache_metadata["elapsed_ms"]),
        )
        return result

    def _saved_run_states(
        self,
        request: ComparativeStudyRequest,
    ) -> dict[str, tuple[SavedResearchRun | None, ResearchRunFreshness]]:
        states: dict[str, tuple[SavedResearchRun | None, ResearchRunFreshness]] = {}
        for symbol in request.symbols:
            run_request = ResearchRunCreateRequest(
                run_type=ResearchRunType.FIRSTRATE_MANY_MORNING_REPLAY,
                symbol=symbol,
                start_date=request.start_date,
                end_date=request.end_date,
                hold_minutes=request.hold_minutes,
                slippage_ticks=request.slippage_ticks,
                commission_per_contract=request.commission_per_contract,
            )
            states[symbol] = self.research_run_service.latest_with_freshness(run_request)
        return states

    def _unavailable_result(
        self,
        request: ComparativeStudyRequest,
        saved_states: dict[str, tuple[SavedResearchRun | None, ResearchRunFreshness]],
    ) -> ComparativeStudyResult:
        symbol_summaries = [
            _symbol_unavailable_summary(symbol, run, freshness)
            for symbol, (run, freshness) in saved_states.items()
        ]
        issue = ComparativeStudyQualityIssue(
            code="saved_runs_missing_or_stale",
            message=(
                "EdgeLab needs current saved local SPY and QQQ research runs before comparing "
                "the early-failed-move pattern."
            ),
        )
        bottom_line = (
            "EdgeLab cannot compare SPY and QQQ yet because one or both saved local results "
            "are missing or may be stale."
        )
        what_compared = (
            "EdgeLab checked whether current saved local SPY and QQQ results exist for the "
            "same early-failed-move test."
        )
        what_different = (
            "No symbol difference was reviewed because the saved local inputs are not complete."
        )
        why_matter = (
            "A comparison needs matching local results so EdgeLab does not mix old and current "
            "source files."
        )
        why_misleading = (
            "A stale or missing saved result could make the two symbols look different for the "
            "wrong reason."
        )
        next_test = (
            "Run local analysis for SPY and QQQ, then reopen this comparison after both saved "
            "results still match their local files."
        )
        comparison = SetupFamilyComparison(
            setup_family=request.setup_family,
            classification=ComparativeStudyClassification.NOT_ENOUGH_EVIDENCE,
            symbol_summaries=symbol_summaries,
            bottom_line=bottom_line,
            what_edgelab_compared=what_compared,
            what_looked_different=what_different,
            why_that_might_matter=why_matter,
            why_this_might_be_misleading=why_misleading,
            what_edgelab_should_test_next=next_test,
            evidence_details={"saved_run_states": _saved_state_details(saved_states)},
        )
        return ComparativeStudyResult(
            study_id="spy-qqq-opening-range-failure",
            request=request,
            comparison_available=False,
            classification=ComparativeStudyClassification.NOT_ENOUGH_EVIDENCE,
            setup_family_comparison=comparison,
            quality_issues=[issue],
            cache_metadata={"cache_status": "not_used"},
            bottom_line=bottom_line,
            what_edgelab_compared=what_compared,
            what_looked_different=what_different,
            why_that_might_matter=why_matter,
            why_this_might_be_misleading=why_misleading,
            what_edgelab_should_test_next=next_test,
            evidence_details=comparison.evidence_details,
        )

    def _run_symbol_summaries(
        self,
        request: ComparativeStudyRequest,
    ) -> dict[str, MultiSessionReplaySummary]:
        summaries: dict[str, MultiSessionReplaySummary] = {}
        engine = HistoricalIntradayReplayEngine(
            provider=self._cached_provider,
            setup_detector=self.setup_detector,
        )
        runner = MultiSessionPatternRunner(provider=self._cached_provider, replay_engine=engine)
        for symbol in request.symbols:
            summaries[symbol] = runner.run(
                MultiSessionReplayRequest(
                    symbol=symbol,
                    start_date=request.start_date,
                    end_date=request.end_date,
                    hold_minutes=request.hold_minutes,
                    slippage_ticks=request.slippage_ticks,
                    commission_per_contract=request.commission_per_contract,
                    minimum_useful_sessions=request.minimum_useful_sessions,
                    minimum_setup_examples=request.minimum_setup_examples,
                    minimum_worth_more_testing_examples=(
                        request.minimum_worth_more_testing_examples
                    ),
                )
            )
        return summaries

    def _result_from_summaries(
        self,
        *,
        request: ComparativeStudyRequest,
        saved_states: dict[str, tuple[SavedResearchRun | None, ResearchRunFreshness]],
        summaries: dict[str, MultiSessionReplaySummary],
        cache_status: str,
        computed_at: str,
        elapsed_ms: int,
    ) -> ComparativeStudyResult:
        symbol_summaries = [
            self._symbol_summary(
                symbol=symbol,
                request=request,
                summary=summaries[symbol],
                saved_state=saved_states[symbol],
            )
            for symbol in request.symbols
        ]
        classification = _classify_comparison(symbol_summaries, request)
        text = _comparison_text(symbol_summaries, classification)
        quality_issues = _comparison_quality_issues(symbol_summaries, classification)
        comparison = SetupFamilyComparison(
            setup_family=request.setup_family,
            classification=classification,
            symbol_summaries=symbol_summaries,
            bottom_line=text["bottom_line"],
            what_edgelab_compared=text["what_edgelab_compared"],
            what_looked_different=text["what_looked_different"],
            why_that_might_matter=text["why_that_might_matter"],
            why_this_might_be_misleading=text["why_this_might_be_misleading"],
            what_edgelab_should_test_next=text["what_edgelab_should_test_next"],
            evidence_details=_comparison_evidence(symbol_summaries, saved_states),
        )
        return ComparativeStudyResult(
            study_id="spy-qqq-opening-range-failure",
            request=request,
            comparison_available=True,
            classification=classification,
            setup_family_comparison=comparison,
            quality_issues=quality_issues,
            cache_metadata={
                "cache_status": cache_status,
                "computed_at": computed_at,
                "elapsed_ms": elapsed_ms,
            },
            bottom_line=comparison.bottom_line,
            what_edgelab_compared=comparison.what_edgelab_compared,
            what_looked_different=comparison.what_looked_different,
            why_that_might_matter=comparison.why_that_might_matter,
            why_this_might_be_misleading=comparison.why_this_might_be_misleading,
            what_edgelab_should_test_next=comparison.what_edgelab_should_test_next,
            evidence_details=comparison.evidence_details,
        )

    def _symbol_summary(
        self,
        *,
        symbol: str,
        request: ComparativeStudyRequest,
        summary: MultiSessionReplaySummary,
        saved_state: tuple[SavedResearchRun | None, ResearchRunFreshness],
    ) -> SymbolComparisonSummary:
        saved_run, freshness = saved_state
        setup_outcomes = [
            outcome
            for outcome in summary.session_outcomes
            if outcome.setup_type == request.setup_family and outcome.setup_found
        ]
        completed = [outcome for outcome in setup_outcomes if outcome.completed_pretend_result]
        setup_type_summary = _setup_type_summary(summary, request.setup_family)
        completeness = self._cached_provider.first_hour_completeness_for_sessions(
            symbol,
            request.start_date,
            request.end_date,
        )
        completeness_summary = summarize_first_hour_completeness(completeness)
        setup_classification = (
            setup_type_summary.classification.value
            if setup_type_summary is not None
            else PatternResultClassification.NOT_ENOUGH_EXAMPLES.value
        )
        return SymbolComparisonSummary(
            symbol=symbol,
            saved_run_id=saved_run.run_id if saved_run else None,
            saved_run_freshness=freshness.status,
            saved_run_message=freshness.message,
            comparison_available=True,
            sessions_tested=summary.sessions_tested,
            usable_sessions=summary.usable_sessions,
            possible_setup_count=len(setup_outcomes),
            sit_out_count=summary.sit_out_count,
            completed_pretend_result_count=len(completed),
            helpful_afterward_count=_bucket_count(completed, ReplayResultBucket.FAVORABLE),
            wrong_way_afterward_count=_bucket_count(completed, ReplayResultBucket.FAILED),
            flat_afterward_count=_bucket_count(completed, ReplayResultBucket.FLAT),
            incomplete_pretend_result_count=sum(
                1 for outcome in setup_outcomes if not outcome.completed_pretend_result
            ),
            setup_classification=setup_classification,
            direction_context_counts=_counts(
                outcome.setup_direction.value if outcome.setup_direction else "unknown"
                for outcome in setup_outcomes
            ),
            opening_gap_bucket_counts=_counts(
                outcome.opening_gap_bucket or "unknown" for outcome in setup_outcomes
            ),
            first_hour_range_width_bucket_counts=_counts(
                outcome.opening_range_width_bucket or "unknown" for outcome in setup_outcomes
            ),
            first_hour_completeness_counts={
                "complete": completeness_summary.complete,
                "minor_gaps": completeness_summary.minor_gaps,
                "major_gaps": completeness_summary.major_gaps,
                "replay_unsafe": completeness_summary.replay_unsafe,
            },
            plain_english_summary=_symbol_plain_summary(symbol, setup_type_summary, summary),
            evidence_details={
                "overall_classification": summary.classification.value,
                "sessions_found": summary.sessions_found,
                "skipped_due_to_data": summary.skipped_due_to_data,
                "cost_changed_conclusion_count": summary.cost_changed_conclusion_count,
                "quality_issue_count": len(summary.quality_issues),
            },
        )

    def _cache_key(self, request: ComparativeStudyRequest) -> ComparativeStudyCacheKey:
        normalized_symbols = set(request.symbols)
        file_signature = tuple(
            sorted(
                (
                    item.path,
                    item.size_bytes,
                    item.modified_time_ns,
                )
                for item in self.provider.file_cache_signature()
                if self.provider.normalizer.infer_symbol_from_path(Path(item.path))
                in normalized_symbols
            )
        )
        return ComparativeStudyCacheKey(
            symbols=request.symbols,
            setup_family=request.setup_family,
            start_date=request.start_date,
            end_date=request.end_date,
            hold_minutes=request.hold_minutes,
            slippage_ticks=request.slippage_ticks,
            commission_per_contract=request.commission_per_contract,
            file_signature=file_signature,
            code_version=COMPARATIVE_STUDY_CODE_VERSION,
        )


def _symbol_unavailable_summary(
    symbol: str,
    run: SavedResearchRun | None,
    freshness: ResearchRunFreshness,
) -> SymbolComparisonSummary:
    return SymbolComparisonSummary(
        symbol=symbol,
        saved_run_id=run.run_id if run else None,
        saved_run_freshness=freshness.status,
        saved_run_message=freshness.message,
        comparison_available=False,
        sessions_tested=0,
        usable_sessions=0,
        possible_setup_count=0,
        sit_out_count=0,
        completed_pretend_result_count=0,
        helpful_afterward_count=0,
        wrong_way_afterward_count=0,
        flat_afterward_count=0,
        incomplete_pretend_result_count=0,
        setup_classification=PatternResultClassification.NOT_ENOUGH_EXAMPLES.value,
        plain_english_summary=(
            f"{normalize_symbol(symbol)} needs a fresh saved local result before EdgeLab can "
            "compare it."
        ),
    )


def _setup_type_summary(
    summary: MultiSessionReplaySummary,
    setup_family: IntradaySetupType,
) -> SetupTypeSummary | None:
    return next(
        (
            setup_summary
            for setup_summary in summary.setup_type_summaries
            if setup_summary.setup_type == setup_family
        ),
        None,
    )


def _classify_comparison(
    symbol_summaries: list[SymbolComparisonSummary],
    request: ComparativeStudyRequest,
) -> ComparativeStudyClassification:
    if any(
        summary.first_hour_completeness_counts.get("replay_unsafe", 0) > 0
        for summary in symbol_summaries
    ):
        return ComparativeStudyClassification.BLOCKED_BY_DATA_QUALITY
    if any(
        summary.usable_sessions < request.minimum_useful_sessions for summary in symbol_summaries
    ):
        return ComparativeStudyClassification.NOT_ENOUGH_EVIDENCE
    if any(
        summary.completed_pretend_result_count < request.minimum_setup_examples
        for summary in symbol_summaries
    ):
        return ComparativeStudyClassification.NOT_ENOUGH_EVIDENCE

    by_symbol = {summary.symbol: summary for summary in symbol_summaries}
    spy = by_symbol.get("SPY")
    qqq = by_symbol.get("QQQ")
    if spy is None or qqq is None:
        return ComparativeStudyClassification.SYMBOL_DIFFERENCE_NEEDS_REVIEW

    spy_rank = _classification_rank(spy.setup_classification)
    qqq_rank = _classification_rank(qqq.setup_classification)
    if spy_rank > qqq_rank:
        return ComparativeStudyClassification.SPY_MORE_INTERESTING
    if qqq_rank > spy_rank:
        return ComparativeStudyClassification.QQQ_MORE_INTERESTING

    setup_rate_delta = abs(
        _rate(spy.possible_setup_count, spy.usable_sessions)
        - _rate(qqq.possible_setup_count, qqq.usable_sessions)
    )
    sit_out_delta = abs(
        _rate(spy.sit_out_count, spy.usable_sessions)
        - _rate(qqq.sit_out_count, qqq.usable_sessions)
    )
    if setup_rate_delta >= 0.20 or sit_out_delta >= 0.20:
        return ComparativeStudyClassification.SYMBOL_DIFFERENCE_NEEDS_REVIEW
    if spy.setup_classification == PatternResultClassification.WEAK_OR_INCONSISTENT.value:
        return ComparativeStudyClassification.TOO_NOISY_TO_COMPARE
    return ComparativeStudyClassification.SIMILAR_BEHAVIOR


def _comparison_text(
    symbol_summaries: list[SymbolComparisonSummary],
    classification: ComparativeStudyClassification,
) -> dict[str, str]:
    by_symbol = {summary.symbol: summary for summary in symbol_summaries}
    spy = by_symbol.get("SPY", symbol_summaries[0])
    qqq = by_symbol.get("QQQ", symbol_summaries[-1])
    base = {
        "what_edgelab_compared": (
            "EdgeLab compared past SPY and QQQ mornings where the first market move failed."
        ),
        "why_that_might_matter": (
            "If this difference holds up in more testing, EdgeLab may need separate rules "
            "for SPY and QQQ."
        ),
        "why_this_might_be_misleading": (
            "This is one local historical sample using simple rules, so symbol differences can "
            "come from noise, data gaps, or a setup definition that is still too broad."
        ),
        "what_edgelab_should_test_next": (
            "Check whether opening gap size or first-hour range explains the difference."
        ),
    }
    if classification == ComparativeStudyClassification.SPY_MORE_INTERESTING:
        bottom = (
            "SPY looked more interesting than QQQ for this early-failed-move pattern, but the "
            "result is still not strong enough to trust."
        )
        different = (
            "SPY had fewer setup examples than QQQ, but its result looked less noisy. "
            "QQQ produced more examples, but they were more mixed."
        )
    elif classification == ComparativeStudyClassification.QQQ_MORE_INTERESTING:
        bottom = (
            "QQQ looked more interesting than SPY for this early-failed-move pattern, but the "
            "result is still not strong enough to trust."
        )
        different = (
            "QQQ looked cleaner than SPY in this local sample, but EdgeLab still needs more "
            "controlled testing before trusting the difference."
        )
    elif classification == ComparativeStudyClassification.TOO_NOISY_TO_COMPARE:
        bottom = "SPY and QQQ were too mixed to compare cleanly for this early-failed-move pattern."
        different = (
            "Both symbols looked mixed, so EdgeLab should avoid reading too much into "
            "the difference."
        )
    elif classification == ComparativeStudyClassification.SIMILAR_BEHAVIOR:
        bottom = "SPY and QQQ looked broadly similar for this early-failed-move pattern."
        different = (
            "The setup and sit-out mix did not separate the two symbols enough for a "
            "strong follow-up."
        )
    elif classification == ComparativeStudyClassification.BLOCKED_BY_DATA_QUALITY:
        bottom = (
            "EdgeLab cannot compare SPY and QQQ cleanly because local data quality needs review."
        )
        different = "The biggest difference is data quality, not pattern behavior."
    elif classification == ComparativeStudyClassification.NOT_ENOUGH_EVIDENCE:
        bottom = "EdgeLab does not have enough comparable examples yet."
        different = "One or both symbols had too few usable examples for a clean comparison."
    else:
        bottom = (
            "EdgeLab found a symbol difference that needs review before any variant work starts."
        )
        different = (
            f"SPY had {spy.possible_setup_count} possible examples and {spy.sit_out_count} "
            f"sit-outs; QQQ had {qqq.possible_setup_count} possible examples and "
            f"{qqq.sit_out_count} sit-outs."
        )
    return {"bottom_line": bottom, "what_looked_different": different, **base}


def _comparison_quality_issues(
    symbol_summaries: list[SymbolComparisonSummary],
    classification: ComparativeStudyClassification,
) -> list[ComparativeStudyQualityIssue]:
    issues: list[ComparativeStudyQualityIssue] = []
    if classification in {
        ComparativeStudyClassification.NOT_ENOUGH_EVIDENCE,
        ComparativeStudyClassification.TOO_NOISY_TO_COMPARE,
    }:
        issues.append(
            ComparativeStudyQualityIssue(
                code=classification.value,
                message="EdgeLab should treat this comparison as a guide for more research only.",
            )
        )
    for summary in symbol_summaries:
        if summary.first_hour_completeness_counts.get("minor_gaps", 0) > 0:
            issues.append(
                ComparativeStudyQualityIssue(
                    code=f"{summary.symbol.lower()}_minor_gaps",
                    message=(
                        f"{summary.symbol} has small first-hour gaps in the local file, so "
                        "the comparison needs caution."
                    ),
                )
            )
    return issues


def _symbol_plain_summary(
    symbol: str,
    setup_summary: SetupTypeSummary | None,
    summary: MultiSessionReplaySummary,
) -> str:
    normalized_symbol = normalize_symbol(symbol)
    if setup_summary is None:
        return f"{normalized_symbol} did not show enough early-failed-move examples yet."
    return (
        f"{normalized_symbol} had {setup_summary.examples_found} possible early-failed-move "
        f"examples across {summary.usable_sessions} usable mornings."
    )


def _comparison_evidence(
    symbol_summaries: list[SymbolComparisonSummary],
    saved_states: dict[str, tuple[SavedResearchRun | None, ResearchRunFreshness]],
) -> dict[str, object]:
    return {
        "symbols": [summary.symbol for summary in symbol_summaries],
        "saved_run_states": _saved_state_details(saved_states),
        "symbol_counts": {
            summary.symbol: {
                "sessions_tested": summary.sessions_tested,
                "usable_sessions": summary.usable_sessions,
                "possible_setup_count": summary.possible_setup_count,
                "sit_out_count": summary.sit_out_count,
                "helpful_afterward_count": summary.helpful_afterward_count,
                "wrong_way_afterward_count": summary.wrong_way_afterward_count,
                "flat_afterward_count": summary.flat_afterward_count,
                "direction_context_counts": summary.direction_context_counts,
                "opening_gap_bucket_counts": summary.opening_gap_bucket_counts,
                "first_hour_range_width_bucket_counts": (
                    summary.first_hour_range_width_bucket_counts
                ),
                "first_hour_completeness_counts": summary.first_hour_completeness_counts,
            }
            for summary in symbol_summaries
        },
    }


def _saved_state_details(
    saved_states: dict[str, tuple[SavedResearchRun | None, ResearchRunFreshness]],
) -> dict[str, dict[str, object]]:
    return {
        symbol: {
            "run_id": run.run_id if run else None,
            "freshness": freshness.status.value,
            "message": freshness.message,
        }
        for symbol, (run, freshness) in saved_states.items()
    }


def _classification_rank(classification: str) -> int:
    ranks = {
        PatternResultClassification.NOT_ENOUGH_EXAMPLES.value: 0,
        PatternResultClassification.BLOCKED_BY_DATA_QUALITY.value: 0,
        PatternResultClassification.WEAK_OR_INCONSISTENT.value: 1,
        PatternResultClassification.INTERESTING_BUT_UNPROVEN.value: 2,
        PatternResultClassification.WORTH_MORE_TESTING.value: 3,
        PatternResultClassification.SIT_OUT_RULES_NEED_REVIEW.value: 1,
    }
    return ranks.get(classification, 0)


def _bucket_count(outcomes: list[ReplaySessionOutcome], bucket: ReplayResultBucket) -> int:
    return sum(1 for outcome in outcomes if outcome.result_bucket == bucket)


def _counts(values: Iterable[object]) -> dict[str, int]:
    return dict(Counter(str(value) for value in values))


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0
    return numerator / denominator
