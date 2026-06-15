"""Generic local out-of-sample gates for intraday research."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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
    ReplaySessionOutcome,
)
from edgelab.intraday.replay import HistoricalIntradayReplayEngine
from edgelab.intraday.setups import IntradaySetupDetector
from edgelab.intraday.variant_study import (
    _definition_by_id,
    _setup_outcomes,
    _spy_qqq_disagreement_outcomes,
    _summary_for_outcomes,
    _variant_specs,
)
from edgelab.intraday.variant_study_schema import (
    VariantResultSummary,
    VariantStudyRequest,
)
from edgelab.research_runs.schema import (
    ResearchRunCreateRequest,
    ResearchRunFreshness,
    ResearchRunFreshnessStatus,
    ResearchRunType,
    SavedResearchRun,
)
from edgelab.research_runs.service import FirstRateResearchRunService

from .out_of_sample_gate_schema import (
    OUT_OF_SAMPLE_GATE_CODE_VERSION,
    OutOfSampleDataQualityWarning,
    OutOfSampleGateConclusion,
    OutOfSampleGatePeriod,
    OutOfSampleGateRequest,
    OutOfSampleGateResult,
    OutOfSampleSplitStrategy,
    OutOfSampleVariantComparison,
    OutOfSampleVariantResult,
    conclusion_translation,
)

PROOF_LIMITATION = (
    "This is a holdout-style check using the current local file. Because these variants were "
    "identified after reviewing the full available sample, this is not a pure untouched-data test. "
    "It is not proof. A stronger check requires additional historical data or future data "
    "collected after the rules are locked."
)


class OutOfSampleSavedRunServiceProtocol(Protocol):
    """Small protocol for saved-run freshness lookups."""

    def latest_with_freshness(
        self,
        request: ResearchRunCreateRequest,
    ) -> tuple[SavedResearchRun | None, ResearchRunFreshness]:
        """Return latest matching run with freshness."""
        ...


@dataclass(frozen=True)
class OutOfSampleGateCacheKey:
    """Process-local cache key for out-of-sample gates."""

    instrument: str
    paired_instrument: str
    pattern_family: str
    variant_ids: tuple[str, ...]
    split_strategy: OutOfSampleSplitStrategy
    discovery_start: date
    discovery_end: date
    holdout_start: date
    holdout_end: date
    hold_minutes: int
    slippage_ticks: int
    commission_per_contract: float
    fast_failure_minutes: int
    file_signature: tuple[tuple[str, int, int], ...]
    code_version: str


@dataclass(frozen=True)
class OutOfSampleGateCacheEntry:
    """Cached out-of-sample result."""

    result: OutOfSampleGateResult
    computed_at: str
    elapsed_ms: int


@dataclass(frozen=True)
class TimeSplit:
    """Concrete time split resolved from available local sessions."""

    discovery_start: date
    discovery_end: date
    holdout_start: date
    holdout_end: date
    discovery_session_count: int
    holdout_session_count: int


class OutOfSampleGateService:
    """Run generic local out-of-sample checks for fixed research variants."""

    def __init__(
        self,
        *,
        research_run_service: OutOfSampleSavedRunServiceProtocol | None = None,
        provider: FirstRateLocalCSVHistoricalProvider | None = None,
        setup_detector: IntradaySetupDetector | None = None,
    ) -> None:
        self.provider = provider or FirstRateLocalCSVHistoricalProvider()
        self.research_run_service = research_run_service or FirstRateResearchRunService(
            provider=self.provider
        )
        self.setup_detector = setup_detector or IntradaySetupDetector()
        self._cached_provider = CachedFirstRateHistoricalDataProvider(self.provider)
        self._cache: dict[OutOfSampleGateCacheKey, OutOfSampleGateCacheEntry] = {}

    def run(self, request: OutOfSampleGateRequest | None = None) -> OutOfSampleGateResult:
        """Return a local read-only out-of-sample gate."""

        request = request or OutOfSampleGateRequest()
        primary_state = self._saved_state(request, request.instrument)
        paired_state = self._saved_state(request, request.paired_instrument)
        blocking_warnings = self._freshness_warnings(request, primary_state, paired_state)
        if blocking_warnings:
            return self._blocked_result(request, blocking_warnings, primary_state, paired_state)

        started_at = perf_counter()
        primary_summary, paired_summary = self._summaries(request)
        primary_outcomes = _setup_outcomes(primary_summary, request.pattern_family)
        paired_outcomes = _setup_outcomes(paired_summary, request.pattern_family)
        split = _resolve_quarter_split(request, primary_summary.session_outcomes)
        if split is None:
            return self._blocked_result(
                request,
                [
                    OutOfSampleDataQualityWarning(
                        code="time_split_unavailable",
                        message=(
                            "EdgeLab could not find enough local sessions on both sides of the "
                            "fixed time split."
                        ),
                    )
                ],
                primary_state,
                paired_state,
            )

        cache_key = self._cache_key(request, split)
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

        result = self._result_from_outcomes(
            request=request,
            split=split,
            primary_outcomes=primary_outcomes,
            paired_outcomes=paired_outcomes,
            primary_state=primary_state,
            paired_state=paired_state,
            computed_at=utc_now().isoformat(),
            elapsed_ms=round((perf_counter() - started_at) * 1000),
        )
        self._cache[cache_key] = OutOfSampleGateCacheEntry(
            result=result,
            computed_at=str(result.cache_metadata["computed_at"]),
            elapsed_ms=int(result.cache_metadata["elapsed_ms"]),
        )
        return result

    def _saved_state(
        self, request: OutOfSampleGateRequest, instrument: str
    ) -> tuple[SavedResearchRun | None, ResearchRunFreshness]:
        run_request = ResearchRunCreateRequest(
            run_type=ResearchRunType.FIRSTRATE_MANY_MORNING_REPLAY,
            symbol=instrument,
            hold_minutes=request.hold_minutes,
            slippage_ticks=request.slippage_ticks,
            commission_per_contract=request.commission_per_contract,
        )
        return self.research_run_service.latest_with_freshness(run_request)

    def _summaries(
        self, request: OutOfSampleGateRequest
    ) -> tuple[MultiSessionReplaySummary, MultiSessionReplaySummary]:
        engine = HistoricalIntradayReplayEngine(
            provider=self._cached_provider,
            setup_detector=self.setup_detector,
        )
        runner = MultiSessionPatternRunner(provider=self._cached_provider, replay_engine=engine)
        return (
            runner.run(
                MultiSessionReplayRequest(
                    symbol=request.instrument,
                    hold_minutes=request.hold_minutes,
                    slippage_ticks=request.slippage_ticks,
                    commission_per_contract=request.commission_per_contract,
                    minimum_useful_sessions=request.minimum_discovery_examples,
                    minimum_setup_examples=request.minimum_discovery_examples,
                )
            ),
            runner.run(
                MultiSessionReplayRequest(
                    symbol=request.paired_instrument,
                    hold_minutes=request.hold_minutes,
                    slippage_ticks=request.slippage_ticks,
                    commission_per_contract=request.commission_per_contract,
                    minimum_useful_sessions=request.minimum_discovery_examples,
                    minimum_setup_examples=request.minimum_discovery_examples,
                )
            ),
        )

    def _result_from_outcomes(
        self,
        *,
        request: OutOfSampleGateRequest,
        split: TimeSplit,
        primary_outcomes: list[ReplaySessionOutcome],
        paired_outcomes: list[ReplaySessionOutcome],
        primary_state: tuple[SavedResearchRun | None, ResearchRunFreshness],
        paired_state: tuple[SavedResearchRun | None, ResearchRunFreshness],
        computed_at: str,
        elapsed_ms: int,
    ) -> OutOfSampleGateResult:
        discovery_primary = _outcomes_in_period(
            primary_outcomes, split.discovery_start, split.discovery_end
        )
        holdout_primary = _outcomes_in_period(
            primary_outcomes, split.holdout_start, split.holdout_end
        )
        discovery_paired = _outcomes_in_period(
            paired_outcomes, split.discovery_start, split.discovery_end
        )
        holdout_paired = _outcomes_in_period(
            paired_outcomes, split.holdout_start, split.holdout_end
        )
        comparisons = [
            self._comparison_for_variant(
                request=request,
                variant_id=variant_id,
                discovery_primary=discovery_primary,
                holdout_primary=holdout_primary,
                discovery_paired=discovery_paired,
                holdout_paired=holdout_paired,
            )
            for variant_id in request.variant_ids
        ]
        warnings = _cost_warnings(comparisons)
        gate_conclusion = _overall_conclusion(comparisons, warnings)
        text = _gate_text(request, comparisons, gate_conclusion)
        discovery_period = OutOfSampleGatePeriod(
            label="Discovery period",
            start_date=split.discovery_start,
            end_date=split.discovery_end,
            session_count=split.discovery_session_count,
            plain_english_summary=(
                "The earlier local period where EdgeLab checks what the fixed idea looked like."
            ),
        )
        holdout_period = OutOfSampleGatePeriod(
            label="Holdout period",
            start_date=split.holdout_start,
            end_date=split.holdout_end,
            session_count=split.holdout_session_count,
            plain_english_summary=("The later local period used for this first honesty check."),
        )
        return OutOfSampleGateResult(
            gate_id=_gate_id(request),
            instrument=request.instrument,
            paired_instrument=request.paired_instrument,
            pattern_family=request.pattern_family.value,
            variant_ids=list(request.variant_ids),
            split_strategy=request.split_strategy,
            discovery_period=discovery_period,
            holdout_period=holdout_period,
            discovery_result=_period_result_text("Discovery", comparisons),
            holdout_result=_period_result_text("Holdout", comparisons),
            comparison_result=text["comparison_result"],
            gate_conclusion=gate_conclusion,
            gate_conclusion_translation=conclusion_translation(gate_conclusion),
            bottom_line=text["bottom_line"],
            what_edgelab_checked=text["what_edgelab_checked"],
            what_changed_on_later_data=text["what_changed_on_later_data"],
            what_this_means=text["what_this_means"],
            what_edgelab_should_test_next=text["what_edgelab_should_test_next"],
            why_this_might_be_misleading=text["why_this_might_be_misleading"],
            proof_limitations=PROOF_LIMITATION,
            variant_comparisons=comparisons,
            data_quality_warnings=warnings,
            cache_metadata={
                "cache_status": "fresh",
                "computed_at": computed_at,
                "elapsed_ms": elapsed_ms,
            },
            evidence_details={
                "saved_run_states": _saved_states_payload(request, primary_state, paired_state),
                "split_cutoff_date": request.holdout_start_date.isoformat(),
                "active_variant_ids": list(request.variant_ids),
            },
        )

    def _comparison_for_variant(
        self,
        *,
        request: OutOfSampleGateRequest,
        variant_id: str,
        discovery_primary: list[ReplaySessionOutcome],
        holdout_primary: list[ReplaySessionOutcome],
        discovery_paired: list[ReplaySessionOutcome],
        holdout_paired: list[ReplaySessionOutcome],
    ) -> OutOfSampleVariantComparison:
        definition = _definition_by_id(variant_id)
        discovery_outcomes = _variant_outcomes(
            variant_id, discovery_primary, discovery_paired, request
        )
        holdout_outcomes = _variant_outcomes(variant_id, holdout_primary, holdout_paired, request)
        variant_request = VariantStudyRequest(
            symbol=request.instrument,
            paired_symbol=request.paired_instrument,
            setup_family=request.pattern_family,
            hold_minutes=request.hold_minutes,
            slippage_ticks=request.slippage_ticks,
            commission_per_contract=request.commission_per_contract,
            minimum_completed_examples=request.minimum_discovery_examples,
            fast_failure_minutes=request.fast_failure_minutes,
        )
        discovery_summary = _summary_for_outcomes(
            definition=definition,
            request=variant_request,
            outcomes=discovery_outcomes,
            baseline_outcomes=discovery_primary,
            data_blocked=False,
        )
        holdout_summary = _summary_for_outcomes(
            definition=definition,
            request=variant_request,
            outcomes=holdout_outcomes,
            baseline_outcomes=holdout_primary,
            data_blocked=False,
        )
        conclusion, warnings = _variant_conclusion(request, discovery_summary, holdout_summary)
        comparison_text = _comparison_text(discovery_summary, holdout_summary, conclusion)
        return OutOfSampleVariantComparison(
            variant_id=variant_id,
            plain_english_label=definition.plain_english_label,
            discovery_result=_variant_result_from_summary(discovery_summary),
            holdout_result=_variant_result_from_summary(holdout_summary),
            comparison_result=comparison_text,
            gate_conclusion=conclusion,
            gate_conclusion_translation=conclusion_translation(conclusion),
            data_quality_warnings=warnings,
            evidence_details={
                "discovery_internal_classification": (
                    discovery_summary.conservative_classification.value
                ),
                "holdout_internal_classification": (
                    holdout_summary.conservative_classification.value
                ),
            },
        )

    def _blocked_result(
        self,
        request: OutOfSampleGateRequest,
        warnings: list[OutOfSampleDataQualityWarning],
        primary_state: tuple[SavedResearchRun | None, ResearchRunFreshness],
        paired_state: tuple[SavedResearchRun | None, ResearchRunFreshness],
    ) -> OutOfSampleGateResult:
        return OutOfSampleGateResult(
            gate_id=_gate_id(request),
            instrument=request.instrument,
            paired_instrument=request.paired_instrument,
            pattern_family=request.pattern_family.value,
            variant_ids=list(request.variant_ids),
            split_strategy=request.split_strategy,
            discovery_result="No discovery result is available because the check is blocked.",
            holdout_result="No holdout result is available because the check is blocked.",
            comparison_result="EdgeLab could not compare the two periods fairly.",
            gate_conclusion=OutOfSampleGateConclusion.BLOCKED_BY_DATA_QUALITY,
            gate_conclusion_translation=conclusion_translation(
                OutOfSampleGateConclusion.BLOCKED_BY_DATA_QUALITY
            ),
            bottom_line="EdgeLab cannot run this holdout-style check until local data is current.",
            what_edgelab_checked=(
                "EdgeLab checked whether saved local research results and local files were ready."
            ),
            what_changed_on_later_data="No later-data check was run.",
            what_this_means="Refresh the saved local analysis before trusting this page.",
            what_edgelab_should_test_next=(
                f"Run local analysis for {request.instrument} and {request.paired_instrument}, "
                "then reopen this page."
            ),
            why_this_might_be_misleading=(
                "Missing or stale local context could make the holdout-style check unfair."
            ),
            proof_limitations=PROOF_LIMITATION,
            variant_comparisons=[],
            data_quality_warnings=warnings,
            cache_metadata={"cache_status": "not_used"},
            evidence_details={
                "saved_run_states": _saved_states_payload(request, primary_state, paired_state)
            },
        )

    def _freshness_warnings(
        self,
        request: OutOfSampleGateRequest,
        primary_state: tuple[SavedResearchRun | None, ResearchRunFreshness],
        paired_state: tuple[SavedResearchRun | None, ResearchRunFreshness],
    ) -> list[OutOfSampleDataQualityWarning]:
        warnings: list[OutOfSampleDataQualityWarning] = []
        if primary_state[1].status != ResearchRunFreshnessStatus.FRESH:
            warnings.append(
                OutOfSampleDataQualityWarning(
                    code="primary_saved_run_missing_or_stale",
                    message=(
                        f"{request.instrument} needs a current saved local result before EdgeLab "
                        "can run the holdout-style check."
                    ),
                )
            )
        if paired_state[1].status != ResearchRunFreshnessStatus.FRESH:
            warnings.append(
                OutOfSampleDataQualityWarning(
                    code="paired_saved_run_missing_or_stale",
                    message=(
                        f"{request.paired_instrument} needs a current saved local result before "
                        "EdgeLab can check symbol-disagreement variants."
                    ),
                )
            )
        return warnings

    def _cache_key(
        self,
        request: OutOfSampleGateRequest,
        split: TimeSplit,
    ) -> OutOfSampleGateCacheKey:
        symbols = {request.instrument, request.paired_instrument}
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
        return OutOfSampleGateCacheKey(
            instrument=request.instrument,
            paired_instrument=request.paired_instrument,
            pattern_family=request.pattern_family.value,
            variant_ids=request.variant_ids,
            split_strategy=request.split_strategy,
            discovery_start=split.discovery_start,
            discovery_end=split.discovery_end,
            holdout_start=split.holdout_start,
            holdout_end=split.holdout_end,
            hold_minutes=request.hold_minutes,
            slippage_ticks=request.slippage_ticks,
            commission_per_contract=request.commission_per_contract,
            fast_failure_minutes=request.fast_failure_minutes,
            file_signature=file_signature,
            code_version=OUT_OF_SAMPLE_GATE_CODE_VERSION,
        )


def _resolve_quarter_split(
    request: OutOfSampleGateRequest,
    outcomes: list[ReplaySessionOutcome],
) -> TimeSplit | None:
    if request.split_strategy != OutOfSampleSplitStrategy.CALENDAR_QUARTER_HOLDOUT:
        return None
    session_dates = sorted(
        {outcome.session_date for outcome in outcomes if outcome.session_date is not None}
    )
    discovery_dates = [
        session_date for session_date in session_dates if session_date < request.holdout_start_date
    ]
    holdout_dates = [
        session_date for session_date in session_dates if session_date >= request.holdout_start_date
    ]
    if not discovery_dates or not holdout_dates:
        return None
    return TimeSplit(
        discovery_start=discovery_dates[0],
        discovery_end=discovery_dates[-1],
        holdout_start=holdout_dates[0],
        holdout_end=holdout_dates[-1],
        discovery_session_count=len(discovery_dates),
        holdout_session_count=len(holdout_dates),
    )


def _variant_outcomes(
    variant_id: str,
    primary_outcomes: list[ReplaySessionOutcome],
    paired_outcomes: list[ReplaySessionOutcome],
    request: OutOfSampleGateRequest,
) -> list[ReplaySessionOutcome]:
    if variant_id == "broad_baseline":
        return primary_outcomes
    if variant_id == "spy_qqq_disagreement":
        return _spy_qqq_disagreement_outcomes(primary_outcomes, paired_outcomes)
    variant_request = VariantStudyRequest(
        symbol=request.instrument,
        paired_symbol=request.paired_instrument,
        setup_family=request.pattern_family,
        hold_minutes=request.hold_minutes,
        slippage_ticks=request.slippage_ticks,
        commission_per_contract=request.commission_per_contract,
        fast_failure_minutes=request.fast_failure_minutes,
    )
    for spec in _variant_specs():
        if spec.definition.variant_id == variant_id:
            return spec.filter_outcomes(primary_outcomes, variant_request)
    raise ValueError(f"unknown variant_id: {variant_id}")


def _outcomes_in_period(
    outcomes: list[ReplaySessionOutcome],
    start_date: date,
    end_date: date,
) -> list[ReplaySessionOutcome]:
    return [
        outcome
        for outcome in outcomes
        if outcome.session_date is not None and start_date <= outcome.session_date <= end_date
    ]


def _variant_result_from_summary(summary: VariantResultSummary) -> OutOfSampleVariantResult:
    return OutOfSampleVariantResult(
        variant_id=summary.variant_id,
        plain_english_label=summary.plain_english_label,
        examples_found=summary.examples_found,
        examples_completed=summary.examples_completed,
        moved_as_expected_count=summary.moved_as_expected_count,
        moved_against_test_count=summary.moved_against_test_count,
        did_not_move_enough_count=summary.did_not_move_enough_count,
        average_pretend_result=summary.average_pretend_result,
        cost_changed_result_count=summary.cost_changed_result_count,
        plain_english_result=_plain_variant_result(summary),
        evidence_details={
            "session_ids": summary.evidence_details.get("session_ids", []),
            "favorable_share": summary.evidence_details.get("favorable_share"),
            "clarity_score": summary.evidence_details.get("clarity_score"),
        },
    )


def _plain_variant_result(summary: VariantResultSummary) -> str:
    if summary.examples_completed < 10:
        return "Not enough examples."
    if summary.moved_against_test_count >= summary.moved_as_expected_count:
        return "Mixed results / no clear answer."
    if summary.average_pretend_result is not None and summary.average_pretend_result <= 0:
        return "Mixed results / no clear answer."
    return "Looked more interesting but still unproven."


def _variant_conclusion(
    request: OutOfSampleGateRequest,
    discovery: VariantResultSummary,
    holdout: VariantResultSummary,
) -> tuple[OutOfSampleGateConclusion, list[str]]:
    if discovery.examples_completed < request.minimum_discovery_examples:
        return (
            OutOfSampleGateConclusion.NEEDS_MORE_DATA,
            ["The earlier period had too few examples for this fixed version."],
        )
    if holdout.examples_completed < request.minimum_holdout_examples:
        return (
            OutOfSampleGateConclusion.NOT_ENOUGH_HOLDOUT_EXAMPLES,
            ["The later period had too few examples for this fixed version."],
        )
    cost_share = holdout.cost_changed_result_count / holdout.examples_completed
    if cost_share >= request.meaningful_cost_change_share:
        return (
            OutOfSampleGateConclusion.BECAME_UNCLEAR,
            ["Costs changed enough examples that EdgeLab should not call this held up."],
        )
    if holdout.average_pretend_result is None:
        return OutOfSampleGateConclusion.BECAME_UNCLEAR, []
    if holdout.average_pretend_result < 0:
        return OutOfSampleGateConclusion.WEAKER_ON_HOLDOUT, []
    if holdout.moved_against_test_count >= holdout.moved_as_expected_count:
        return OutOfSampleGateConclusion.WEAKER_ON_HOLDOUT, []
    margin = max(1, round(holdout.examples_completed * 0.10))
    if holdout.moved_as_expected_count <= holdout.moved_against_test_count + margin:
        return OutOfSampleGateConclusion.BECAME_UNCLEAR, []
    if (
        holdout.variant_id != "broad_baseline"
        and holdout.baseline_comparison.clarity_delta_points is not None
        and holdout.baseline_comparison.clarity_delta_points < 10
    ):
        return (
            OutOfSampleGateConclusion.BECAME_UNCLEAR,
            ["The later period did not separate clearly from the broad comparison group."],
        )
    return OutOfSampleGateConclusion.HELD_UP_IN_FIRST_CHECK, []


def _comparison_text(
    discovery: VariantResultSummary,
    holdout: VariantResultSummary,
    conclusion: OutOfSampleGateConclusion,
) -> str:
    if conclusion == OutOfSampleGateConclusion.HELD_UP_IN_FIRST_CHECK:
        return (
            f"{holdout.plain_english_label} still looked interesting in the later period, "
            "but this is not a recommendation."
        )
    if conclusion == OutOfSampleGateConclusion.BECAME_UNCLEAR:
        return (
            f"{holdout.plain_english_label} became mixed on the later data, so EdgeLab did not "
            "get a clear answer."
        )
    if conclusion == OutOfSampleGateConclusion.NOT_ENOUGH_HOLDOUT_EXAMPLES:
        return f"{holdout.plain_english_label} had too few later examples to judge fairly."
    if conclusion == OutOfSampleGateConclusion.WEAKER_ON_HOLDOUT:
        return (
            f"{holdout.plain_english_label} looked weaker in the later period than EdgeLab "
            "would want."
        )
    if conclusion == OutOfSampleGateConclusion.NEEDS_MORE_DATA:
        return f"{discovery.plain_english_label} needs more history before this check can decide."
    return "A data problem prevented a fair comparison."


def _overall_conclusion(
    comparisons: list[OutOfSampleVariantComparison],
    warnings: list[OutOfSampleDataQualityWarning],
) -> OutOfSampleGateConclusion:
    if any(warning.code.startswith("blocked") for warning in warnings):
        return OutOfSampleGateConclusion.BLOCKED_BY_DATA_QUALITY
    conclusions = {comparison.gate_conclusion for comparison in comparisons}
    target_conclusions = {
        comparison.gate_conclusion
        for comparison in comparisons
        if comparison.variant_id in {"failed_push_from_above", "spy_qqq_disagreement"}
    }
    if OutOfSampleGateConclusion.HELD_UP_IN_FIRST_CHECK in target_conclusions:
        return OutOfSampleGateConclusion.HELD_UP_IN_FIRST_CHECK
    if OutOfSampleGateConclusion.BECAME_UNCLEAR in target_conclusions:
        return OutOfSampleGateConclusion.BECAME_UNCLEAR
    if OutOfSampleGateConclusion.WEAKER_ON_HOLDOUT in target_conclusions:
        return OutOfSampleGateConclusion.WEAKER_ON_HOLDOUT
    if conclusions == {OutOfSampleGateConclusion.NOT_ENOUGH_HOLDOUT_EXAMPLES}:
        return OutOfSampleGateConclusion.NOT_ENOUGH_HOLDOUT_EXAMPLES
    if OutOfSampleGateConclusion.NEEDS_MORE_DATA in conclusions:
        return OutOfSampleGateConclusion.NEEDS_MORE_DATA
    return OutOfSampleGateConclusion.BECAME_UNCLEAR


def _gate_text(
    request: OutOfSampleGateRequest,
    comparisons: list[OutOfSampleVariantComparison],
    conclusion: OutOfSampleGateConclusion,
) -> dict[str, str]:
    target = {
        comparison.variant_id: comparison
        for comparison in comparisons
        if comparison.variant_id in {"failed_push_from_above", "spy_qqq_disagreement"}
    }
    if conclusion == OutOfSampleGateConclusion.HELD_UP_IN_FIRST_CHECK:
        bottom_line = (
            "One SPY failed early move version still looked interesting in the later period, "
            "but it remains research-only."
        )
    elif conclusion == OutOfSampleGateConclusion.WEAKER_ON_HOLDOUT:
        bottom_line = (
            "The interesting-looking SPY failed early move versions did not pass this first "
            "holdout-style check."
        )
    else:
        bottom_line = (
            "The SPY failed early move variants became mixed on the later period, so EdgeLab "
            "does not have a clear answer."
        )
    changed_parts = [
        f"{comparison.plain_english_label}: {comparison.gate_conclusion_translation}"
        for comparison in target.values()
    ]
    return {
        "bottom_line": bottom_line,
        "what_edgelab_checked": (
            f"EdgeLab split the local {request.instrument} history into an earlier discovery "
            "period and a later holdout-style period, then reran the fixed variants."
        ),
        "what_changed_on_later_data": " ".join(changed_parts)
        or "No target variant could be compared.",
        "what_this_means": (
            "This is useful for deciding what to study next, not for deciding what to do with "
            "real money."
        ),
        "what_edgelab_should_test_next": (
            "Keep the rules fixed and test them on additional historical data or future local "
            "data collected after the rules are locked."
        ),
        "why_this_might_be_misleading": PROOF_LIMITATION,
        "comparison_result": (
            "EdgeLab compared each fixed version in the earlier and later periods without "
            "changing the split after seeing the result."
        ),
    }


def _period_result_text(
    label: str,
    comparisons: list[OutOfSampleVariantComparison],
) -> str:
    interesting = [
        comparison.plain_english_label
        for comparison in comparisons
        if (
            label == "Discovery"
            and comparison.discovery_result.plain_english_result
            == "Looked more interesting but still unproven."
        )
        or (
            label == "Holdout"
            and comparison.holdout_result.plain_english_result
            == "Looked more interesting but still unproven."
        )
    ]
    if interesting:
        return f"{label} period: {', '.join(interesting)} looked more interesting but unproven."
    return f"{label} period: results were mixed or there were too few examples."


def _cost_warnings(
    comparisons: list[OutOfSampleVariantComparison],
) -> list[OutOfSampleDataQualityWarning]:
    warnings: list[OutOfSampleDataQualityWarning] = []
    if any(comparison.data_quality_warnings for comparison in comparisons):
        warnings.append(
            OutOfSampleDataQualityWarning(
                code="variant_level_warnings_present",
                message="One or more fixed versions had a warning that limits the check.",
            )
        )
    return warnings


def _saved_states_payload(
    request: OutOfSampleGateRequest,
    primary_state: tuple[SavedResearchRun | None, ResearchRunFreshness],
    paired_state: tuple[SavedResearchRun | None, ResearchRunFreshness],
) -> dict[str, dict[str, object]]:
    primary_run, primary_freshness = primary_state
    paired_run, paired_freshness = paired_state
    return {
        request.instrument: {
            "run_id": primary_run.run_id if primary_run else None,
            "freshness": primary_freshness.status.value,
            "message": primary_freshness.message,
        },
        request.paired_instrument: {
            "run_id": paired_run.run_id if paired_run else None,
            "freshness": paired_freshness.status.value,
            "message": paired_freshness.message,
        },
    }


def _gate_id(request: OutOfSampleGateRequest) -> str:
    return f"{request.instrument.lower()}-early-move-failed-out-of-sample-gate"
