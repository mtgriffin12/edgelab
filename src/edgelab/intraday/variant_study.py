"""Controlled local intraday variant studies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Protocol

from edgelab.intraday.csv_normalizers import FirstRateLocalCSVHistoricalProvider
from edgelab.intraday.firstrate_replay import CachedFirstRateHistoricalDataProvider
from edgelab.intraday.historical_schema import utc_now
from edgelab.intraday.pattern_results import MultiSessionPatternRunner
from edgelab.intraday.pattern_results_schema import (
    MultiSessionReplayRequest,
    MultiSessionReplaySummary,
    ReplayResultBucket,
    ReplaySessionOutcome,
)
from edgelab.intraday.replay import HistoricalIntradayReplayEngine
from edgelab.intraday.schema import IntradaySetupDirection, IntradaySetupType
from edgelab.intraday.setups import IntradaySetupDetector
from edgelab.research_runs.schema import (
    ResearchRunCreateRequest,
    ResearchRunFreshness,
    ResearchRunFreshnessStatus,
    ResearchRunType,
    SavedResearchRun,
)
from edgelab.research_runs.service import FirstRateResearchRunService

from .variant_study_schema import (
    VARIANT_STUDY_CODE_VERSION,
    VariantBaselineComparison,
    VariantDefinition,
    VariantResultSummary,
    VariantStudyClassification,
    VariantStudyQualityIssue,
    VariantStudyRequest,
    VariantStudyResult,
    saved_run_state_payload,
)


class VariantSavedRunServiceProtocol(Protocol):
    """Small protocol for saved-run freshness lookups."""

    def latest_with_freshness(
        self,
        request: ResearchRunCreateRequest,
    ) -> tuple[SavedResearchRun | None, ResearchRunFreshness]:
        """Return latest matching run with freshness."""
        ...


@dataclass(frozen=True)
class VariantStudyCacheKey:
    """Process-local cache key for controlled variant studies."""

    symbol: str
    paired_symbol: str
    setup_family: IntradaySetupType
    start_date: object
    end_date: object
    hold_minutes: int
    slippage_ticks: int
    commission_per_contract: float
    fast_failure_minutes: int
    file_signature: tuple[tuple[str, int, int], ...]
    code_version: str


@dataclass(frozen=True)
class VariantStudyCacheEntry:
    """Cached controlled variant study result."""

    result: VariantStudyResult
    computed_at: str
    elapsed_ms: int


@dataclass(frozen=True)
class VariantSpec:
    """One fixed variant rule."""

    definition: VariantDefinition
    filter_outcomes: Callable[
        [list[ReplaySessionOutcome], VariantStudyRequest], list[ReplaySessionOutcome]
    ]


def controlled_variant_definitions() -> list[VariantDefinition]:
    """Return the fixed Phase 7X-2H controlled variant definitions."""

    return [spec.definition for spec in _variant_specs()]


class ControlledVariantStudyService:
    """Build a conservative controlled variant study for one local symbol."""

    def __init__(
        self,
        *,
        research_run_service: VariantSavedRunServiceProtocol | None = None,
        provider: FirstRateLocalCSVHistoricalProvider | None = None,
        setup_detector: IntradaySetupDetector | None = None,
    ) -> None:
        self.provider = provider or FirstRateLocalCSVHistoricalProvider()
        self.research_run_service = research_run_service or FirstRateResearchRunService(
            provider=self.provider
        )
        self.setup_detector = setup_detector or IntradaySetupDetector()
        self._cached_provider = CachedFirstRateHistoricalDataProvider(self.provider)
        self._cache: dict[VariantStudyCacheKey, VariantStudyCacheEntry] = {}

    def run(self, request: VariantStudyRequest | None = None) -> VariantStudyResult:
        """Return a local read-only controlled variant study."""

        request = request or VariantStudyRequest()
        primary_state = self._saved_state(request, request.symbol)
        paired_state = self._saved_state(request, request.paired_symbol)
        if primary_state[1].status != ResearchRunFreshnessStatus.FRESH:
            return self._unavailable_result(request, primary_state, paired_state)

        cache_key = self._cache_key(
            request, include_paired=paired_state[1].status == ResearchRunFreshnessStatus.FRESH
        )
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
        summaries = {request.symbol: self._multi_session_summary(request, request.symbol)}
        if paired_state[1].status == ResearchRunFreshnessStatus.FRESH:
            summaries[request.paired_symbol] = self._multi_session_summary(
                request, request.paired_symbol
            )
        result = self._result_from_summaries(
            request=request,
            primary_state=primary_state,
            paired_state=paired_state,
            summaries=summaries,
            cache_status="fresh",
            computed_at=utc_now().isoformat(),
            elapsed_ms=round((perf_counter() - started_at) * 1000),
        )
        self._cache[cache_key] = VariantStudyCacheEntry(
            result=result,
            computed_at=str(result.cache_metadata["computed_at"]),
            elapsed_ms=int(result.cache_metadata["elapsed_ms"]),
        )
        return result

    def _saved_state(
        self, request: VariantStudyRequest, symbol: str
    ) -> tuple[SavedResearchRun | None, ResearchRunFreshness]:
        run_request = ResearchRunCreateRequest(
            run_type=ResearchRunType.FIRSTRATE_MANY_MORNING_REPLAY,
            symbol=symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            hold_minutes=request.hold_minutes,
            slippage_ticks=request.slippage_ticks,
            commission_per_contract=request.commission_per_contract,
        )
        return self.research_run_service.latest_with_freshness(run_request)

    def _multi_session_summary(
        self, request: VariantStudyRequest, symbol: str
    ) -> MultiSessionReplaySummary:
        engine = HistoricalIntradayReplayEngine(
            provider=self._cached_provider,
            setup_detector=self.setup_detector,
        )
        runner = MultiSessionPatternRunner(provider=self._cached_provider, replay_engine=engine)
        return runner.run(
            MultiSessionReplayRequest(
                symbol=symbol,
                start_date=request.start_date,
                end_date=request.end_date,
                hold_minutes=request.hold_minutes,
                slippage_ticks=request.slippage_ticks,
                commission_per_contract=request.commission_per_contract,
                minimum_useful_sessions=request.minimum_useful_sessions,
                minimum_setup_examples=request.minimum_completed_examples,
                minimum_worth_more_testing_examples=request.minimum_worth_more_testing_examples,
            )
        )

    def _unavailable_result(
        self,
        request: VariantStudyRequest,
        primary_state: tuple[SavedResearchRun | None, ResearchRunFreshness],
        paired_state: tuple[SavedResearchRun | None, ResearchRunFreshness],
    ) -> VariantStudyResult:
        issue = VariantStudyQualityIssue(
            code="fresh_spy_saved_run_required",
            message=(
                f"EdgeLab needs a current saved local {request.symbol} result before it can "
                "compare controlled versions of the failed early move pattern."
            ),
        )
        baseline = VariantBaselineComparison(
            plain_english_summary=(
                "No baseline comparison is available until the saved local result is current."
            )
        )
        return VariantStudyResult(
            study_id=_study_id(request),
            request=request,
            study_available=False,
            classification=VariantStudyClassification.BLOCKED_BY_DATA_QUALITY,
            bottom_line=(
                f"EdgeLab cannot test {request.symbol} variants yet because the saved local "
                "result is missing or may be stale."
            ),
            what_edgelab_tested=(
                "EdgeLab checked whether the saved local result is current enough to support "
                "a controlled variant study."
            ),
            what_looked_different="No variants were compared yet.",
            which_version_deserves_more_testing=(
                "No version deserves more testing from this view yet."
            ),
            why_this_might_be_misleading=(
                "A missing or stale saved result could make a variant look different for the "
                "wrong reason."
            ),
            what_edgelab_should_test_next=(
                f"Run local analysis for {request.symbol}, then reopen this controlled "
                "variant study."
            ),
            baseline_comparison=baseline,
            variant_summaries=[],
            quality_issues=[issue],
            cache_metadata={"cache_status": "not_used"},
            evidence_details={
                "saved_run_states": _saved_states_payload(request, primary_state, paired_state)
            },
        )

    def _result_from_summaries(
        self,
        *,
        request: VariantStudyRequest,
        primary_state: tuple[SavedResearchRun | None, ResearchRunFreshness],
        paired_state: tuple[SavedResearchRun | None, ResearchRunFreshness],
        summaries: dict[str, MultiSessionReplaySummary],
        cache_status: str,
        computed_at: str,
        elapsed_ms: int,
    ) -> VariantStudyResult:
        primary_outcomes = _setup_outcomes(summaries[request.symbol], request.setup_family)
        paired_outcomes = (
            _setup_outcomes(summaries[request.paired_symbol], request.setup_family)
            if request.paired_symbol in summaries
            else []
        )
        baseline = _summary_for_outcomes(
            definition=_definition_by_id("broad_baseline"),
            request=request,
            outcomes=primary_outcomes,
            baseline_outcomes=primary_outcomes,
            data_blocked=False,
        )
        variant_summaries = [baseline]
        for spec in _variant_specs():
            if spec.definition.variant_id == "broad_baseline":
                continue
            if spec.definition.variant_id == "spy_qqq_disagreement":
                if paired_state[1].status != ResearchRunFreshnessStatus.FRESH:
                    variant_summaries.append(
                        _blocked_summary(
                            spec.definition,
                            request,
                            "A current saved local QQQ result is needed for this comparison.",
                            baseline,
                        )
                    )
                    continue
                outcomes = _spy_qqq_disagreement_outcomes(
                    primary_outcomes,
                    paired_outcomes,
                )
            else:
                outcomes = spec.filter_outcomes(primary_outcomes, request)
            variant_summaries.append(
                _summary_for_outcomes(
                    definition=spec.definition,
                    request=request,
                    outcomes=outcomes,
                    baseline_outcomes=primary_outcomes,
                    data_blocked=False,
                )
            )

        variant_summaries.extend(_readiness_checks(request, primary_outcomes, baseline))
        classification = _study_classification(variant_summaries)
        text = _study_text(request, variant_summaries, classification)
        issues = _quality_issues(request, variant_summaries, primary_state, paired_state)
        baseline_comparison = VariantBaselineComparison(
            baseline_variant_id="broad_baseline",
            variant_favorable_share=baseline.baseline_comparison.variant_favorable_share,
            baseline_favorable_share=baseline.baseline_comparison.baseline_favorable_share,
            clarity_delta_points=0,
            plain_english_summary=(
                "The broad failed early move group is the anchor every controlled version "
                "compares against."
            ),
        )
        return VariantStudyResult(
            study_id=_study_id(request),
            request=request,
            study_available=True,
            classification=classification,
            bottom_line=text["bottom_line"],
            what_edgelab_tested=text["what_edgelab_tested"],
            what_looked_different=text["what_looked_different"],
            which_version_deserves_more_testing=text["which_version_deserves_more_testing"],
            why_this_might_be_misleading=text["why_this_might_be_misleading"],
            what_edgelab_should_test_next=text["what_edgelab_should_test_next"],
            baseline_comparison=baseline_comparison,
            variant_summaries=variant_summaries,
            quality_issues=issues,
            cache_metadata={
                "cache_status": cache_status,
                "computed_at": computed_at,
                "elapsed_ms": elapsed_ms,
            },
            evidence_details={
                "saved_run_states": _saved_states_payload(request, primary_state, paired_state),
                "active_variant_ids": [
                    definition.variant_id
                    for definition in controlled_variant_definitions()
                    if definition.is_active_variant
                ],
                "context_check_ids": [
                    "opening_gap_context_check",
                    "range_width_context_check",
                ],
            },
        )

    def _cache_key(
        self, request: VariantStudyRequest, *, include_paired: bool
    ) -> VariantStudyCacheKey:
        symbols = {request.symbol}
        if include_paired:
            symbols.add(request.paired_symbol)
        file_signature = tuple(
            sorted(
                (
                    item.path,
                    item.size_bytes,
                    item.modified_time_ns,
                )
                for item in self.provider.file_cache_signature()
                if self.provider.normalizer.infer_symbol_from_path(Path(item.path)) in symbols
            )
        )
        return VariantStudyCacheKey(
            symbol=request.symbol,
            paired_symbol=request.paired_symbol,
            setup_family=request.setup_family,
            start_date=request.start_date,
            end_date=request.end_date,
            hold_minutes=request.hold_minutes,
            slippage_ticks=request.slippage_ticks,
            commission_per_contract=request.commission_per_contract,
            fast_failure_minutes=request.fast_failure_minutes,
            file_signature=file_signature,
            code_version=VARIANT_STUDY_CODE_VERSION,
        )


def _variant_specs() -> list[VariantSpec]:
    return [
        VariantSpec(
            definition=VariantDefinition(
                variant_id="broad_baseline",
                plain_english_label="Broad failed early move",
                rule_definition="All failed early move examples for the selected symbol.",
                why_it_might_matter="It gives every narrower version a fair comparison point.",
                baseline_compared_against="broad_baseline",
                what_would_disprove_it=(
                    "The broad group is too mixed to guide the next research step."
                ),
            ),
            filter_outcomes=lambda outcomes, _request: outcomes,
        ),
        VariantSpec(
            definition=VariantDefinition(
                variant_id="failed_push_from_above",
                plain_english_label="Failed push from above",
                rule_definition=(
                    "Only failed early moves where the first push above the early range did "
                    "not hold."
                ),
                why_it_might_matter=(
                    "Upside failures may behave differently from downside failures."
                ),
                what_would_disprove_it=(
                    "It looks no clearer than the broad failed early move group."
                ),
            ),
            filter_outcomes=lambda outcomes, _request: [
                outcome
                for outcome in outcomes
                if outcome.setup_direction == IntradaySetupDirection.SHORT_CONTEXT
            ],
        ),
        VariantSpec(
            definition=VariantDefinition(
                variant_id="failed_selloff_from_below",
                plain_english_label="Failed selloff from below",
                rule_definition=(
                    "Only failed early moves where the first push below the early range recovered."
                ),
                why_it_might_matter=(
                    "Downside failures may behave differently from upside failures."
                ),
                what_would_disprove_it=(
                    "It looks no clearer than the broad failed early move group."
                ),
            ),
            filter_outcomes=lambda outcomes, _request: [
                outcome
                for outcome in outcomes
                if outcome.setup_direction == IntradaySetupDirection.LONG_CONTEXT
            ],
        ),
        VariantSpec(
            definition=VariantDefinition(
                variant_id="fast_failure",
                plain_english_label="Failed quickly",
                rule_definition=(
                    "Only failed early moves detected within 15 minutes of the regular open."
                ),
                why_it_might_matter=(
                    "A quick failure may be cleaner than a late first-hour failure."
                ),
                what_would_disprove_it=(
                    "It has too few examples or does not separate from the broad group."
                ),
            ),
            filter_outcomes=lambda outcomes, request: [
                outcome
                for outcome in outcomes
                if _failure_minutes(outcome) <= request.fast_failure_minutes
            ],
        ),
        VariantSpec(
            definition=VariantDefinition(
                variant_id="slow_failure",
                plain_english_label="Failed later",
                rule_definition=(
                    "Only failed early moves detected after 15 minutes from the regular open."
                ),
                why_it_might_matter="A later failure may be more mixed than an immediate failure.",
                what_would_disprove_it=(
                    "It has too few examples or does not separate from the broad group."
                ),
            ),
            filter_outcomes=lambda outcomes, request: [
                outcome
                for outcome in outcomes
                if _failure_minutes(outcome) > request.fast_failure_minutes
            ],
        ),
        VariantSpec(
            definition=VariantDefinition(
                variant_id="spy_qqq_disagreement",
                plain_english_label="SPY and QQQ disagreed",
                rule_definition=(
                    "SPY has a failed early move while same-date QQQ lacks the same direction."
                ),
                why_it_might_matter=(
                    "Symbol disagreement may explain why SPY looked more interesting."
                ),
                what_would_disprove_it=(
                    "It has too few examples or does not improve on the broad SPY group."
                ),
            ),
            filter_outcomes=lambda outcomes, _request: outcomes,
        ),
    ]


def _definition_by_id(variant_id: str) -> VariantDefinition:
    for definition in controlled_variant_definitions():
        if definition.variant_id == variant_id:
            return definition
    raise ValueError(f"unknown variant_id: {variant_id}")


def _setup_outcomes(
    summary: MultiSessionReplaySummary, setup_family: IntradaySetupType
) -> list[ReplaySessionOutcome]:
    return [
        outcome
        for outcome in summary.session_outcomes
        if outcome.setup_found and outcome.setup_type == setup_family
    ]


def _summary_for_outcomes(
    *,
    definition: VariantDefinition,
    request: VariantStudyRequest,
    outcomes: list[ReplaySessionOutcome],
    baseline_outcomes: list[ReplaySessionOutcome],
    data_blocked: bool,
) -> VariantResultSummary:
    completed = [outcome for outcome in outcomes if outcome.completed_pretend_result]
    baseline_completed = [
        outcome for outcome in baseline_outcomes if outcome.completed_pretend_result
    ]
    net_results = [
        outcome.pretend_net_result
        for outcome in completed
        if outcome.pretend_net_result is not None
    ]
    moved_as_expected = _bucket_count(completed, ReplayResultBucket.FAVORABLE)
    moved_against = _bucket_count(completed, ReplayResultBucket.FAILED)
    did_not_move_enough = _bucket_count(completed, ReplayResultBucket.FLAT)
    baseline_expected = _bucket_count(baseline_completed, ReplayResultBucket.FAVORABLE)
    baseline_against = _bucket_count(baseline_completed, ReplayResultBucket.FAILED)
    favorable_share = _share(moved_as_expected, len(completed))
    baseline_favorable_share = _share(baseline_expected, len(baseline_completed))
    clarity = _clarity_score(moved_as_expected, moved_against, len(completed))
    baseline_clarity = _clarity_score(
        baseline_expected,
        baseline_against,
        len(baseline_completed),
    )
    clarity_delta = (
        clarity - baseline_clarity if clarity is not None and baseline_clarity is not None else None
    )
    average_result = _average(net_results)
    classification = _classify_variant(
        definition=definition,
        request=request,
        completed_count=len(completed),
        moved_as_expected=moved_as_expected,
        moved_against=moved_against,
        did_not_move_enough=did_not_move_enough,
        average_result=average_result,
        clarity_delta_points=clarity_delta,
        data_blocked=data_blocked,
    )
    comparison = VariantBaselineComparison(
        baseline_variant_id="broad_baseline",
        variant_favorable_share=favorable_share,
        baseline_favorable_share=baseline_favorable_share,
        clarity_delta_points=clarity_delta,
        plain_english_summary=_baseline_comparison_text(
            definition.variant_id, classification, clarity_delta
        ),
    )
    return VariantResultSummary(
        variant_id=definition.variant_id,
        plain_english_label=definition.plain_english_label,
        rule_definition=definition.rule_definition,
        why_it_might_matter=definition.why_it_might_matter,
        baseline_compared_against=definition.baseline_compared_against,
        examples_found=len(outcomes),
        examples_completed=len(completed),
        moved_as_expected_count=moved_as_expected,
        moved_against_test_count=moved_against,
        did_not_move_enough_count=did_not_move_enough,
        average_pretend_result=average_result,
        worst_pretend_result=min(net_results) if net_results else None,
        best_pretend_result=max(net_results) if net_results else None,
        cost_changed_result_count=sum(
            1 for outcome in completed if outcome.cost_changed_conclusion
        ),
        conservative_classification=classification,
        what_would_disprove_it=definition.what_would_disprove_it,
        baseline_comparison=comparison,
        evidence_details={
            "variant_id": definition.variant_id,
            "setup_family": request.setup_family.value,
            "session_ids": [outcome.session_id for outcome in outcomes],
            "favorable_share": favorable_share,
            "baseline_favorable_share": baseline_favorable_share,
            "clarity_score": clarity,
            "baseline_clarity_score": baseline_clarity,
        },
    )


def _blocked_summary(
    definition: VariantDefinition,
    request: VariantStudyRequest,
    reason: str,
    baseline: VariantResultSummary,
) -> VariantResultSummary:
    comparison = VariantBaselineComparison(
        plain_english_summary=(
            "This version cannot be compared until the needed local context is current."
        )
    )
    return VariantResultSummary(
        variant_id=definition.variant_id,
        plain_english_label=definition.plain_english_label,
        rule_definition=definition.rule_definition,
        why_it_might_matter=definition.why_it_might_matter,
        examples_found=0,
        examples_completed=0,
        moved_as_expected_count=0,
        moved_against_test_count=0,
        did_not_move_enough_count=0,
        cost_changed_result_count=0,
        conservative_classification=VariantStudyClassification.BLOCKED_BY_DATA_QUALITY,
        what_would_disprove_it=definition.what_would_disprove_it,
        baseline_comparison=comparison,
        evidence_details={
            "variant_id": definition.variant_id,
            "setup_family": request.setup_family.value,
            "blocked_reason": reason,
            "baseline_examples_completed": baseline.examples_completed,
        },
    )


def _readiness_checks(
    request: VariantStudyRequest,
    baseline_outcomes: list[ReplaySessionOutcome],
    baseline: VariantResultSummary,
) -> list[VariantResultSummary]:
    completed = [outcome for outcome in baseline_outcomes if outcome.completed_pretend_result]
    known_gap = [
        outcome for outcome in completed if outcome.opening_gap_bucket not in {None, "unknown"}
    ]
    gap_known_share = len(known_gap) / len(completed) if completed else 0
    gap_definition = VariantDefinition(
        variant_id="opening_gap_context_check",
        plain_english_label="Opening gap context check",
        rule_definition=(
            "Checks whether opening gap context is complete enough before gap variants are trusted."
        ),
        why_it_might_matter="Gap size may matter, but missing context can create false confidence.",
        what_would_disprove_it="Opening gap context is missing for too many examples.",
        is_active_variant=False,
    )
    gap_summary = _blocked_summary(
        gap_definition,
        request,
        "Opening gap context is missing for too many baseline examples.",
        baseline,
    )
    if gap_known_share >= 0.80:
        gap_summary = _summary_for_outcomes(
            definition=gap_definition,
            request=request,
            outcomes=known_gap,
            baseline_outcomes=baseline_outcomes,
            data_blocked=False,
        )

    range_definition = VariantDefinition(
        variant_id="range_width_context_check",
        plain_english_label="Range width context check",
        rule_definition=(
            "Checks whether narrow or wide first-hour ranges have enough examples to review."
        ),
        why_it_might_matter="The width of the first-hour area may change how noisy the pattern is.",
        what_would_disprove_it="Narrow or wide range groups have too few finished examples.",
        is_active_variant=False,
    )
    narrow_or_wide = [
        outcome
        for outcome in baseline_outcomes
        if outcome.opening_range_width_bucket in {"narrow", "wide"}
    ]
    range_summary = _summary_for_outcomes(
        definition=range_definition,
        request=request,
        outcomes=narrow_or_wide,
        baseline_outcomes=baseline_outcomes,
        data_blocked=False,
    )
    if range_summary.examples_completed < request.minimum_completed_examples:
        range_summary = range_summary.model_copy(
            update={
                "conservative_classification": VariantStudyClassification.NOT_ENOUGH_EXAMPLES,
                "baseline_comparison": VariantBaselineComparison(
                    plain_english_summary=(
                        "Narrow and wide range groups are too thin to compare against the "
                        "broad group."
                    )
                ),
            }
        )
    return [gap_summary, range_summary]


def _classify_variant(
    *,
    definition: VariantDefinition,
    request: VariantStudyRequest,
    completed_count: int,
    moved_as_expected: int,
    moved_against: int,
    did_not_move_enough: int,
    average_result: float | None,
    clarity_delta_points: float | None,
    data_blocked: bool,
) -> VariantStudyClassification:
    if data_blocked:
        return VariantStudyClassification.BLOCKED_BY_DATA_QUALITY
    if completed_count < request.minimum_completed_examples:
        return VariantStudyClassification.NOT_ENOUGH_EXAMPLES
    if average_result is None:
        return VariantStudyClassification.TOO_NOISY
    if abs(moved_as_expected - moved_against) <= max(1, round(completed_count * 0.10)):
        return VariantStudyClassification.TOO_NOISY
    if definition.variant_id == "broad_baseline":
        if moved_as_expected > moved_against + did_not_move_enough and average_result > 0:
            return VariantStudyClassification.INTERESTING_BUT_UNPROVEN
        return VariantStudyClassification.TOO_NOISY
    if clarity_delta_points is None:
        return VariantStudyClassification.SIMILAR_TO_BASELINE
    if clarity_delta_points <= -request.minimum_clarity_improvement_points:
        return VariantStudyClassification.WEAKER_THAN_BASELINE
    if abs(clarity_delta_points) < request.minimum_clarity_improvement_points:
        return VariantStudyClassification.SIMILAR_TO_BASELINE
    favorable_share = moved_as_expected / completed_count if completed_count else 0
    if (
        completed_count >= request.minimum_worth_more_testing_examples
        and favorable_share >= 0.60
        and average_result > 0
        and clarity_delta_points >= request.minimum_clarity_improvement_points
    ):
        return VariantStudyClassification.WORTH_MORE_TESTING
    if moved_as_expected > moved_against + did_not_move_enough and average_result > 0:
        return VariantStudyClassification.INTERESTING_BUT_UNPROVEN
    return VariantStudyClassification.TOO_NOISY


def _spy_qqq_disagreement_outcomes(
    spy_outcomes: list[ReplaySessionOutcome],
    qqq_outcomes: list[ReplaySessionOutcome],
) -> list[ReplaySessionOutcome]:
    qqq_by_date = {outcome.session_date: outcome for outcome in qqq_outcomes}
    selected: list[ReplaySessionOutcome] = []
    for spy_outcome in spy_outcomes:
        qqq_outcome = qqq_by_date.get(spy_outcome.session_date)
        if qqq_outcome is None or qqq_outcome.setup_direction != spy_outcome.setup_direction:
            selected.append(spy_outcome)
    return selected


def _failure_minutes(outcome: ReplaySessionOutcome) -> float:
    signal_time = outcome.signal_bar_timestamp
    regular_open_time = outcome.regular_open_timestamp
    if not isinstance(signal_time, datetime) or not isinstance(regular_open_time, datetime):
        return 9999
    return (signal_time - regular_open_time).total_seconds() / 60


def _study_classification(
    summaries: list[VariantResultSummary],
) -> VariantStudyClassification:
    active = [
        summary
        for summary in summaries
        if summary.variant_id
        not in {
            "broad_baseline",
            "opening_gap_context_check",
            "range_width_context_check",
        }
    ]
    rank = {
        VariantStudyClassification.BLOCKED_BY_DATA_QUALITY: 0,
        VariantStudyClassification.NOT_ENOUGH_EXAMPLES: 0,
        VariantStudyClassification.WEAKER_THAN_BASELINE: 1,
        VariantStudyClassification.TOO_NOISY: 1,
        VariantStudyClassification.SIMILAR_TO_BASELINE: 2,
        VariantStudyClassification.INTERESTING_BUT_UNPROVEN: 3,
        VariantStudyClassification.WORTH_MORE_TESTING: 4,
    }
    return max(
        (summary.conservative_classification for summary in active),
        key=lambda classification: rank[classification],
        default=VariantStudyClassification.NOT_ENOUGH_EXAMPLES,
    )


def _study_text(
    request: VariantStudyRequest,
    summaries: list[VariantResultSummary],
    classification: VariantStudyClassification,
) -> dict[str, str]:
    best = _best_summary(summaries)
    if classification == VariantStudyClassification.WORTH_MORE_TESTING and best is not None:
        bottom_line = (
            f"EdgeLab found one {request.symbol} failed early move version worth more testing, "
            "but it is still research-only."
        )
        deserves = f"{best.plain_english_label} deserves the next controlled research pass."
    elif classification == VariantStudyClassification.INTERESTING_BUT_UNPROVEN and best is not None:
        bottom_line = (
            f"EdgeLab found one {request.symbol} failed early move version that is interesting "
            "but still too thin to trust."
        )
        deserves = f"{best.plain_english_label} may deserve more testing, not paper mode."
    else:
        bottom_line = (
            f"EdgeLab tested controlled {request.symbol} failed early move versions, but none "
            "is clear enough yet."
        )
        deserves = "No version deserves promotion yet; the next step is tighter research."
    return {
        "bottom_line": bottom_line,
        "what_edgelab_tested": (
            "EdgeLab compared pre-chosen versions of the failed early move pattern against the "
            "broad SPY baseline."
        ),
        "what_looked_different": _difference_text(summaries),
        "which_version_deserves_more_testing": deserves,
        "why_this_might_be_misleading": (
            "This is one local historical sample. The variants were not tested on fresh future "
            "data, and smaller groups can look cleaner by chance."
        ),
        "what_edgelab_should_test_next": (
            "Keep the strongest variant fixed, then test it on more data with an experiment ledger."
        ),
    }


def _best_summary(summaries: list[VariantResultSummary]) -> VariantResultSummary | None:
    eligible = [
        summary
        for summary in summaries
        if summary.variant_id
        not in {
            "broad_baseline",
            "opening_gap_context_check",
            "range_width_context_check",
        }
        and summary.conservative_classification
        in {
            VariantStudyClassification.WORTH_MORE_TESTING,
            VariantStudyClassification.INTERESTING_BUT_UNPROVEN,
        }
    ]
    return max(
        eligible,
        key=lambda summary: summary.baseline_comparison.clarity_delta_points or 0,
        default=None,
    )


def _difference_text(summaries: list[VariantResultSummary]) -> str:
    best = _best_summary(summaries)
    if best is not None:
        return (
            f"{best.plain_english_label} looked clearer than the broad group, but it still "
            "needs more controlled testing."
        )
    thin = [
        summary.plain_english_label
        for summary in summaries
        if summary.conservative_classification == VariantStudyClassification.NOT_ENOUGH_EXAMPLES
    ]
    if thin:
        return "Some versions were too thin to compare cleanly."
    return "The controlled versions looked too similar or too noisy to separate confidently."


def _quality_issues(
    request: VariantStudyRequest,
    summaries: list[VariantResultSummary],
    primary_state: tuple[SavedResearchRun | None, ResearchRunFreshness],
    paired_state: tuple[SavedResearchRun | None, ResearchRunFreshness],
) -> list[VariantStudyQualityIssue]:
    issues: list[VariantStudyQualityIssue] = []
    if primary_state[1].status == ResearchRunFreshnessStatus.FRESH:
        issues.append(
            VariantStudyQualityIssue(
                code="local_research_only",
                message=(
                    "This controlled variant study is local research only, not a recommendation."
                ),
            )
        )
    if paired_state[1].status != ResearchRunFreshnessStatus.FRESH:
        issues.append(
            VariantStudyQualityIssue(
                code="paired_saved_run_missing_or_stale",
                message=(
                    f"{request.paired_symbol} needs a current saved local result before the "
                    "SPY and QQQ disagreement version can be trusted."
                ),
            )
        )
    if any(
        summary.variant_id == "opening_gap_context_check"
        and summary.conservative_classification
        == VariantStudyClassification.BLOCKED_BY_DATA_QUALITY
        for summary in summaries
    ):
        issues.append(
            VariantStudyQualityIssue(
                code="opening_gap_context_incomplete",
                message=(
                    "Opening gap context is incomplete, so gap-size versions are not compared yet."
                ),
            )
        )
    return issues


def _baseline_comparison_text(
    variant_id: str,
    classification: VariantStudyClassification,
    clarity_delta: float | None,
) -> str:
    if variant_id == "broad_baseline":
        return "This is the broad comparison group for every controlled version."
    if classification == VariantStudyClassification.BLOCKED_BY_DATA_QUALITY:
        return "This version is blocked by missing or incomplete local context."
    if classification == VariantStudyClassification.NOT_ENOUGH_EXAMPLES:
        return "This version has too few finished examples to compare fairly."
    if classification == VariantStudyClassification.WEAKER_THAN_BASELINE:
        return "This version looked weaker than the broad group."
    if classification == VariantStudyClassification.SIMILAR_TO_BASELINE:
        return "This version looked too similar to the broad group."
    if classification == VariantStudyClassification.WORTH_MORE_TESTING:
        return "This version looked cleaner than the broad group and is worth more testing."
    if classification == VariantStudyClassification.INTERESTING_BUT_UNPROVEN:
        return "This version looked cleaner than the broad group, but the evidence is still thin."
    if clarity_delta is not None:
        return "This version did not separate clearly from the broad group."
    return "This version is too mixed to compare confidently."


def _saved_states_payload(
    request: VariantStudyRequest,
    primary_state: tuple[SavedResearchRun | None, ResearchRunFreshness],
    paired_state: tuple[SavedResearchRun | None, ResearchRunFreshness],
) -> dict[str, dict[str, object]]:
    primary_run, primary_freshness = primary_state
    paired_run, paired_freshness = paired_state
    return {
        request.symbol: saved_run_state_payload(
            run_id=primary_run.run_id if primary_run else None,
            freshness=primary_freshness.status,
            message=primary_freshness.message,
        ),
        request.paired_symbol: saved_run_state_payload(
            run_id=paired_run.run_id if paired_run else None,
            freshness=paired_freshness.status,
            message=paired_freshness.message,
        ),
    }


def _study_id(request: VariantStudyRequest) -> str:
    return f"{request.symbol.lower()}-early-move-failed-variant-study"


def _bucket_count(outcomes: list[ReplaySessionOutcome], bucket: ReplayResultBucket) -> int:
    return sum(1 for outcome in outcomes if outcome.result_bucket == bucket)


def _share(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _clarity_score(expected: int, against: int, completed: int) -> float | None:
    if completed == 0:
        return None
    return (expected - against) / completed * 100


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
