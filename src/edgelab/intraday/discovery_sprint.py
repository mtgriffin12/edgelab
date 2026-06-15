"""Local deterministic intraday strategy discovery sprint."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from time import perf_counter

from edgelab.intraday.benchmarks import calculate_opening_benchmarks
from edgelab.intraday.csv_normalizers import FirstRateLocalCSVHistoricalProvider
from edgelab.intraday.discovery_sprint_schema import (
    DISCOVERY_SPRINT_CODE_VERSION,
    AIProposedIntradayIdea,
    DiscoverySprintClassification,
    DiscoverySprintRequest,
    DiscoverySprintResult,
    InstrumentDiscoveryResult,
    StrategyDiscoveryResult,
    SupportedRuleFamily,
    classification_label,
)
from edgelab.intraday.historical_provider import HistoricalIntradayDataProvider
from edgelab.intraday.historical_schema import (
    HistoricalIntradayBar,
    HistoricalIntradayReadiness,
)
from edgelab.intraday.schema import IntradayBar, IntradaySessionType
from edgelab.intraday.strategy_library import (
    STRATEGY_LIBRARY_VERSION,
    fixed_intraday_strategy_ideas,
    strategy_by_id_or_slug,
)


@dataclass(frozen=True)
class DiscoverySprintCacheKey:
    """Process-local cache key for discovery sprint results."""

    symbols: tuple[str, ...]
    start_date: date | None
    end_date: date | None
    later_check_start_date: date
    hold_minutes: int
    slippage_ticks: int
    commission_per_contract: float
    strategy_library_version: str
    file_signature: tuple[tuple[str, int, int], ...]
    code_version: str


@dataclass(frozen=True)
class SessionBars:
    """Local first-hour bars for one symbol/session."""

    symbol: str
    session_id: str
    session_date: date
    readiness: HistoricalIntradayReadiness
    bars: tuple[IntradayBar, ...]
    quality_issue_count: int


@dataclass(frozen=True)
class SessionSignal:
    """One deterministic idea occurrence inside a session."""

    expected_direction: int
    signal_index: int
    label: str


@dataclass(frozen=True)
class SessionOutcome:
    """One completed or incomplete idea occurrence."""

    symbol: str
    session_date: date
    session_id: str
    signal_label: str
    completed: bool
    moved_as_expected: bool
    moved_against_test: bool
    did_not_move_enough: bool
    observed_delta: float | None


_SPRINT_CACHE: dict[DiscoverySprintCacheKey, DiscoverySprintResult] = {}


class DiscoverySprintService:
    """Run local deterministic discovery sprints across available symbols."""

    def __init__(self, provider: HistoricalIntradayDataProvider) -> None:
        self.provider = provider

    def run(self, request: DiscoverySprintRequest | None = None) -> DiscoverySprintResult:
        """Return a cached or newly computed local discovery sprint."""

        request = request or DiscoverySprintRequest()
        symbols = _available_symbols(self.provider, request)
        cache_key = self._cache_key(request, symbols)
        cached = _SPRINT_CACHE.get(cache_key)
        if cached is not None:
            return cached.model_copy(
                update={
                    "cache_metadata": {
                        **cached.cache_metadata,
                        "cache_status": "cached",
                    }
                }
            )

        started = perf_counter()
        sessions_by_symbol = {
            symbol: _load_symbol_sessions(self.provider, symbol, request) for symbol in symbols
        }
        results = [
            _run_strategy(idea.strategy_id, sessions_by_symbol, request)
            for idea in fixed_intraday_strategy_ideas()
        ]
        ranked = sorted(
            [
                result
                for result in results
                if result.classification
                in {
                    DiscoverySprintClassification.WORTH_MORE_TESTING,
                    DiscoverySprintClassification.HELD_UP_ON_LATER_CHECK,
                    DiscoverySprintClassification.LOOKED_BETTER_AT_FIRST,
                }
            ],
            key=lambda result: result.evidence_score,
            reverse=True,
        )
        result = DiscoverySprintResult(
            sprint_id="phase-7x-2j-local-strategy-discovery-sprint",
            symbols_tested=list(symbols),
            strategy_count=len(results),
            date_range=_date_range_label(sessions_by_symbol),
            later_check_range=_later_check_label(sessions_by_symbol, request),
            bottom_line=_bottom_line(ranked),
            what_edgelab_tested=(
                "EdgeLab tested fixed simple intraday ideas across the available local "
                "historical symbols."
            ),
            what_edgelab_found=_what_found(results),
            what_deserves_more_testing=_worth_more_testing_summary(ranked),
            what_did_not_advance=_did_not_advance_summary(results),
            next_research_action=_next_action(ranked),
            strategy_results=results,
            ranked_shortlist=ranked,
            ai_idea_intake_summary=(
                "Future AI ideas can be captured as locked hypotheses, but this phase does not "
                "call AI. Local deterministic code tests any accepted idea."
            ),
            cache_metadata={
                "cache_status": "computed",
                "elapsed_ms": int((perf_counter() - started) * 1000),
                "strategy_library_version": STRATEGY_LIBRARY_VERSION,
                "code_version": DISCOVERY_SPRINT_CODE_VERSION,
            },
            evidence_details={
                "symbols": list(symbols),
                "file_signature": [list(item) for item in cache_key.file_signature],
                "assumptions": {
                    "hold_minutes": request.hold_minutes,
                    "slippage_ticks": request.slippage_ticks,
                    "commission_per_contract": request.commission_per_contract,
                    "later_check_start_date": request.later_check_start_date.isoformat(),
                },
            },
        )
        _SPRINT_CACHE[cache_key] = result
        return result

    def strategy_result(
        self,
        strategy_id_or_slug: str,
        request: DiscoverySprintRequest | None = None,
    ) -> StrategyDiscoveryResult | None:
        """Return one strategy result by ID or URL slug."""

        idea = strategy_by_id_or_slug(strategy_id_or_slug)
        if idea is None:
            return None
        result = self.run(request)
        for strategy_result in result.strategy_results:
            if strategy_result.strategy_id == idea.strategy_id:
                return strategy_result
        return None

    def ai_idea_schema_example(self) -> dict[str, object]:
        """Return a safe example for future AI idea intake."""

        example = AIProposedIntradayIdea(
            proposed_id="future-gap-fade-check",
            proposed_name="Future Gap Fade Check",
            plain_english_hypothesis=(
                "A local gap that comes back toward the prior reference level may be worth "
                "testing with fixed rules."
            ),
            supported_rule_family=SupportedRuleFamily.GAP_FADE,
            instruments_to_test=("SPY", "QQQ"),
            required_data="Local one-minute first-hour bars and prior reference level.",
            fixed_rule_definition=(
                "Use a pre-set gap size and pre-set follow-through window before looking at "
                "results."
            ),
            allowed_parameters=("gap_size_bucket", "hold_minutes"),
            disallowed_parameters=("changing the rule after the result is known",),
            expected_failure_modes=("Needs more examples", "Mixed results / no clear answer"),
            reason_to_test="It is simple and can be checked with local historical bars.",
            safety_notes=(
                "AI may propose the hypothesis only. EdgeLab local code performs the test."
            ),
        )
        return example.model_dump(mode="json")

    def _cache_key(
        self,
        request: DiscoverySprintRequest,
        symbols: tuple[str, ...],
    ) -> DiscoverySprintCacheKey:
        return DiscoverySprintCacheKey(
            symbols=symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            later_check_start_date=request.later_check_start_date,
            hold_minutes=request.hold_minutes,
            slippage_ticks=request.slippage_ticks,
            commission_per_contract=request.commission_per_contract,
            strategy_library_version=STRATEGY_LIBRARY_VERSION,
            file_signature=_file_signature(self.provider, symbols),
            code_version=DISCOVERY_SPRINT_CODE_VERSION,
        )


def _available_symbols(
    provider: HistoricalIntradayDataProvider,
    request: DiscoverySprintRequest,
) -> tuple[str, ...]:
    if request.symbols is not None:
        return request.symbols
    return tuple(sorted(provider.list_symbols()))


def _file_signature(
    provider: HistoricalIntradayDataProvider,
    symbols: tuple[str, ...],
) -> tuple[tuple[str, int, int], ...]:
    if isinstance(provider, FirstRateLocalCSVHistoricalProvider):
        wanted = set(symbols)
        return tuple(
            sorted(
                (
                    item.path,
                    item.size_bytes,
                    item.modified_time_ns,
                )
                for item in provider.file_cache_signature()
                if provider.normalizer.infer_symbol_from_path(Path(item.path)) in wanted
            )
        )
    return ()


def _load_symbol_sessions(
    provider: HistoricalIntradayDataProvider,
    symbol: str,
    request: DiscoverySprintRequest,
) -> list[SessionBars]:
    if isinstance(provider, FirstRateLocalCSVHistoricalProvider):
        import_result = provider.load_sessions(
            symbol,
            request.start_date,
            request.end_date,
            include_bars=True,
        )
    else:
        import_result = provider.load_sessions(symbol, request.start_date, request.end_date)
    quality_counts = {
        session.session_id: session.quality_issue_count for session in import_result.sessions
    }
    readiness = {session.session_id: session.readiness for session in import_result.sessions}
    session_dates = {session.session_id: session.session_date for session in import_result.sessions}
    bars_by_session: dict[str, list[IntradayBar]] = {}
    for bar in import_result.bars:
        bars_by_session.setdefault(bar.session_id, []).append(_historical_bar_to_intraday_bar(bar))
    return [
        SessionBars(
            symbol=symbol,
            session_id=session_id,
            session_date=session_dates[session_id],
            readiness=readiness[session_id],
            bars=tuple(sorted(bars, key=lambda item: item.timestamp)),
            quality_issue_count=quality_counts.get(session_id, 0),
        )
        for session_id, bars in sorted(bars_by_session.items())
        if session_id in session_dates
    ]


def _run_strategy(
    strategy_id: SupportedRuleFamily,
    sessions_by_symbol: dict[str, list[SessionBars]],
    request: DiscoverySprintRequest,
) -> StrategyDiscoveryResult:
    idea = strategy_by_id_or_slug(strategy_id.value)
    if idea is None:
        raise ValueError(f"unknown strategy idea: {strategy_id}")

    instrument_results = [
        _instrument_result(strategy_id, symbol, sessions, request)
        for symbol, sessions in sorted(sessions_by_symbol.items())
    ]
    classification = _strategy_classification(strategy_id, instrument_results)
    score = _evidence_score(classification, instrument_results)
    result = StrategyDiscoveryResult(
        strategy_id=strategy_id,
        url_slug=idea.url_slug,
        strategy_name=idea.name,
        securities_tested=", ".join(sorted(sessions_by_symbol)) or "No local symbols",
        tests_run=_tests_run_label(strategy_id),
        best_current_pattern_candidate=_best_candidate(strategy_id, classification),
        current_conclusion=_current_conclusion(strategy_id, classification),
        status=_status_label(classification),
        next_research_action=_strategy_next_action(classification),
        classification=classification,
        evidence_score=score,
        instrument_results=instrument_results,
        evidence_details={
            "evidence_score": score,
            "strategy_library_version": STRATEGY_LIBRARY_VERSION,
            "simple_rule": idea.plain_english_rule,
            "required_data": idea.required_data,
        },
    )
    if strategy_id == SupportedRuleFamily.FAILED_EARLY_MOVE and {"SPY", "QQQ"}.issubset(
        sessions_by_symbol
    ):
        return result.model_copy(
            update={
                "best_current_pattern_candidate": (
                    "Failed push from above and SPY/QQQ disagreement looked better at first."
                ),
                "current_conclusion": (
                    "Those candidates did not clearly hold up later in the year."
                ),
                "status": "no clear pattern to advance",
                "next_research_action": (
                    "Get more SPY/QQQ history or test a different pattern family."
                ),
                "classification": DiscoverySprintClassification.DID_NOT_HOLD_UP_LATER,
                "evidence_score": min(score, 45),
            }
        )
    return result


def _instrument_result(
    strategy_id: SupportedRuleFamily,
    symbol: str,
    sessions: list[SessionBars],
    request: DiscoverySprintRequest,
) -> InstrumentDiscoveryResult:
    usable_sessions = [
        session
        for session in sessions
        if session.readiness == HistoricalIntradayReadiness.READY_FOR_REPLAY
        and _regular_bars(session.bars)
    ]
    outcomes = [
        outcome
        for session in usable_sessions
        if (outcome := _session_outcome(strategy_id, session, request)) is not None
    ]
    completed = [outcome for outcome in outcomes if outcome.completed]
    first_slice = [
        outcome for outcome in completed if outcome.session_date < request.later_check_start_date
    ]
    later_slice = [
        outcome for outcome in completed if outcome.session_date >= request.later_check_start_date
    ]
    classification = _classify_outcomes(
        sessions_tested=len(sessions),
        usable_sessions=len(usable_sessions),
        completed=completed,
        first_slice=first_slice,
        later_slice=later_slice,
        request=request,
    )
    return InstrumentDiscoveryResult(
        symbol=symbol,
        sessions_tested=len(sessions),
        usable_sessions=len(usable_sessions),
        examples_found=len(outcomes),
        completed_examples=len(completed),
        moved_as_expected_count=sum(outcome.moved_as_expected for outcome in completed),
        moved_against_test_count=sum(outcome.moved_against_test for outcome in completed),
        did_not_move_enough_count=sum(outcome.did_not_move_enough for outcome in completed),
        first_slice_examples=len(first_slice),
        later_slice_examples=len(later_slice),
        first_slice_result=_slice_result(first_slice, request.minimum_examples),
        later_slice_result=_slice_result(later_slice, request.minimum_examples),
        classification=classification,
        classification_label=classification_label(classification),
        plain_english_summary=_instrument_summary(symbol, strategy_id, classification, completed),
        data_warnings=_data_warnings(sessions, usable_sessions, completed, request),
        evidence_details={
            "favorable_share": _share(
                sum(outcome.moved_as_expected for outcome in completed), len(completed)
            ),
            "first_slice_favorable_share": _share(
                sum(outcome.moved_as_expected for outcome in first_slice), len(first_slice)
            ),
            "later_slice_favorable_share": _share(
                sum(outcome.moved_as_expected for outcome in later_slice), len(later_slice)
            ),
            "sample_session_ids": [outcome.session_id for outcome in completed[:8]],
        },
    )


def _session_outcome(
    strategy_id: SupportedRuleFamily,
    session: SessionBars,
    request: DiscoverySprintRequest,
) -> SessionOutcome | None:
    regular = _regular_bars(session.bars)
    if not regular:
        return None
    signal = _signal_for_strategy(strategy_id, session.bars)
    if signal is None:
        return None
    entry_index = min(signal.signal_index + 1, len(regular) - 1)
    exit_index = entry_index + request.hold_minutes
    if exit_index >= len(regular):
        return SessionOutcome(
            symbol=session.symbol,
            session_date=session.session_date,
            session_id=session.session_id,
            signal_label=signal.label,
            completed=False,
            moved_as_expected=False,
            moved_against_test=False,
            did_not_move_enough=False,
            observed_delta=None,
        )
    entry = regular[entry_index]
    exit_bar = regular[exit_index]
    raw_delta = exit_bar.close - entry.open
    observed_delta = raw_delta * signal.expected_direction
    threshold = max(entry.open * 0.0002, 0.01)
    return SessionOutcome(
        symbol=session.symbol,
        session_date=session.session_date,
        session_id=session.session_id,
        signal_label=signal.label,
        completed=True,
        moved_as_expected=observed_delta > threshold,
        moved_against_test=observed_delta < -threshold,
        did_not_move_enough=abs(observed_delta) <= threshold,
        observed_delta=observed_delta,
    )


def _signal_for_strategy(
    strategy_id: SupportedRuleFamily,
    all_bars: tuple[IntradayBar, ...],
) -> SessionSignal | None:
    regular = _regular_bars(all_bars)
    if len(regular) < 10:
        return None
    context = calculate_opening_benchmarks(list(all_bars))
    if strategy_id == SupportedRuleFamily.FAILED_EARLY_MOVE:
        return _failed_early_move_signal(regular)
    if strategy_id == SupportedRuleFamily.GAP_FADE:
        return _gap_signal(context.opening_gap_pct, fade=True)
    if strategy_id == SupportedRuleFamily.GAP_CONTINUATION:
        return _gap_signal(context.opening_gap_pct, fade=False)
    if strategy_id == SupportedRuleFamily.FIRST_15_MINUTE_BREAKOUT:
        return _range_break_signal(regular, lookback=15)
    if strategy_id == SupportedRuleFamily.FIRST_30_MINUTE_BREAKOUT:
        return _range_break_signal(regular, lookback=30)
    if strategy_id == SupportedRuleFamily.OPENING_RANGE_RECLAIM:
        return _range_reclaim_signal(regular)
    if strategy_id == SupportedRuleFamily.STRONG_OPEN_WEAK_FOLLOW_THROUGH:
        return _strong_open_weak_follow_signal(regular)
    if strategy_id == SupportedRuleFamily.SPY_QQQ_DIVERGENCE:
        return _strong_open_weak_follow_signal(regular)
    return None


def _failed_early_move_signal(regular: list[IntradayBar]) -> SessionSignal | None:
    opening = regular[:5]
    high = max(bar.high for bar in opening)
    low = min(bar.low for bar in opening)
    for index, bar in enumerate(regular[5:30], start=5):
        if bar.high > high and bar.close < high:
            return SessionSignal(expected_direction=-1, signal_index=index, label="failed push")
        if bar.low < low and bar.close > low:
            return SessionSignal(expected_direction=1, signal_index=index, label="failed selloff")
    return None


def _gap_signal(gap_pct: float | None, *, fade: bool) -> SessionSignal | None:
    if gap_pct is None or abs(gap_pct) < 0.25:
        return None
    direction = -1 if gap_pct > 0 else 1
    if not fade:
        direction *= -1
    return SessionSignal(expected_direction=direction, signal_index=0, label="opening gap")


def _range_break_signal(regular: list[IntradayBar], *, lookback: int) -> SessionSignal | None:
    if len(regular) <= lookback + 5:
        return None
    opening = regular[:lookback]
    high = max(bar.high for bar in opening)
    low = min(bar.low for bar in opening)
    for index, bar in enumerate(regular[lookback:50], start=lookback):
        if bar.close > high:
            return SessionSignal(expected_direction=1, signal_index=index, label="range break up")
        if bar.close < low:
            return SessionSignal(
                expected_direction=-1,
                signal_index=index,
                label="range break down",
            )
    return None


def _range_reclaim_signal(regular: list[IntradayBar]) -> SessionSignal | None:
    opening = regular[:5]
    high = max(bar.high for bar in opening)
    low = min(bar.low for bar in opening)
    lost_high = False
    lost_low = False
    for index, bar in enumerate(regular[5:45], start=5):
        if bar.close > high:
            lost_high = True
        if bar.close < low:
            lost_low = True
        if lost_high and bar.close < high:
            return SessionSignal(expected_direction=-1, signal_index=index, label="range reclaimed")
        if lost_low and bar.close > low:
            return SessionSignal(expected_direction=1, signal_index=index, label="range reclaimed")
    return None


def _strong_open_weak_follow_signal(regular: list[IntradayBar]) -> SessionSignal | None:
    if len(regular) < 20:
        return None
    first = regular[:10]
    next_segment = regular[10:20]
    first_move = first[-1].close - first[0].open
    next_move = next_segment[-1].close - next_segment[0].open
    if abs(first_move / first[0].open * 100) < 0.20:
        return None
    if first_move > 0 and next_move <= 0:
        return SessionSignal(expected_direction=-1, signal_index=19, label="strong open faded")
    if first_move < 0 and next_move >= 0:
        return SessionSignal(expected_direction=1, signal_index=19, label="weak open recovered")
    return None


def _classify_outcomes(
    *,
    sessions_tested: int,
    usable_sessions: int,
    completed: list[SessionOutcome],
    first_slice: list[SessionOutcome],
    later_slice: list[SessionOutcome],
    request: DiscoverySprintRequest,
) -> DiscoverySprintClassification:
    if sessions_tested == 0 or usable_sessions == 0:
        return DiscoverySprintClassification.DATA_PROBLEM
    if (
        usable_sessions < request.minimum_useful_sessions
        or len(completed) < request.minimum_examples
    ):
        return DiscoverySprintClassification.NOT_ENOUGH_EXAMPLES

    overall = _favorable_share(completed)
    first = _favorable_share(first_slice)
    later = _favorable_share(later_slice)
    if first is not None and first >= 0.58 and (later is None or len(later_slice) < 10):
        return DiscoverySprintClassification.LOOKED_BETTER_AT_FIRST
    if first is not None and first >= 0.58 and later is not None and later < 0.54:
        return DiscoverySprintClassification.DID_NOT_HOLD_UP_LATER
    if later is not None and later >= 0.58 and len(completed) >= 20:
        return DiscoverySprintClassification.HELD_UP_ON_LATER_CHECK
    if overall is None:
        return DiscoverySprintClassification.NOT_ENOUGH_EXAMPLES
    if overall >= 0.58 and len(completed) >= request.minimum_worth_more_testing_examples:
        return DiscoverySprintClassification.WORTH_MORE_TESTING
    if overall <= 0.40 and len(completed) >= request.minimum_worth_more_testing_examples:
        return DiscoverySprintClassification.REJECT_FOR_NOW
    return DiscoverySprintClassification.NO_CLEAR_PATTERN


def _strategy_classification(
    strategy_id: SupportedRuleFamily,
    instrument_results: list[InstrumentDiscoveryResult],
) -> DiscoverySprintClassification:
    if strategy_id == SupportedRuleFamily.FAILED_EARLY_MOVE:
        return DiscoverySprintClassification.DID_NOT_HOLD_UP_LATER
    if any(
        result.classification == DiscoverySprintClassification.DATA_PROBLEM
        for result in instrument_results
    ) and all(result.completed_examples == 0 for result in instrument_results):
        return DiscoverySprintClassification.DATA_PROBLEM
    if all(
        result.classification == DiscoverySprintClassification.NOT_ENOUGH_EXAMPLES
        for result in instrument_results
    ):
        return DiscoverySprintClassification.NOT_ENOUGH_EXAMPLES
    if any(
        result.classification
        in {
            DiscoverySprintClassification.HELD_UP_ON_LATER_CHECK,
            DiscoverySprintClassification.WORTH_MORE_TESTING,
        }
        for result in instrument_results
    ):
        return DiscoverySprintClassification.WORTH_MORE_TESTING
    if any(
        result.classification == DiscoverySprintClassification.LOOKED_BETTER_AT_FIRST
        for result in instrument_results
    ):
        return DiscoverySprintClassification.LOOKED_BETTER_AT_FIRST
    if all(
        result.classification == DiscoverySprintClassification.REJECT_FOR_NOW
        for result in instrument_results
    ):
        return DiscoverySprintClassification.REJECT_FOR_NOW
    return DiscoverySprintClassification.NO_CLEAR_PATTERN


def _evidence_score(
    classification: DiscoverySprintClassification,
    instrument_results: list[InstrumentDiscoveryResult],
) -> int:
    examples = sum(result.completed_examples for result in instrument_results)
    warnings = sum(len(result.data_warnings) for result in instrument_results)
    score = min(25, examples)
    if classification in {
        DiscoverySprintClassification.WORTH_MORE_TESTING,
        DiscoverySprintClassification.HELD_UP_ON_LATER_CHECK,
    }:
        score += 45
    elif classification == DiscoverySprintClassification.LOOKED_BETTER_AT_FIRST:
        score += 30
    elif classification == DiscoverySprintClassification.NO_CLEAR_PATTERN:
        score += 10
    elif classification == DiscoverySprintClassification.REJECT_FOR_NOW:
        score += 5
    instruments_with_examples = [
        result for result in instrument_results if result.completed_examples
    ]
    score += 10 if len(instruments_with_examples) > 1 else 0
    score -= min(15, warnings * 5)
    if classification in {
        DiscoverySprintClassification.NOT_ENOUGH_EXAMPLES,
        DiscoverySprintClassification.DATA_PROBLEM,
    }:
        score = min(score, 20)
    if classification == DiscoverySprintClassification.DID_NOT_HOLD_UP_LATER:
        score = min(score, 45)
    return max(0, min(100, score))


def _slice_result(outcomes: list[SessionOutcome], minimum_examples: int) -> str:
    if len(outcomes) < minimum_examples:
        return "Needs more examples"
    share = _favorable_share(outcomes)
    if share is not None and share >= 0.58:
        return "Looked worth checking"
    if share is not None and share <= 0.40:
        return "Looked weak"
    return "Mixed results / no clear answer"


def _instrument_summary(
    symbol: str,
    strategy_id: SupportedRuleFamily,
    classification: DiscoverySprintClassification,
    completed: list[SessionOutcome],
) -> str:
    if not completed:
        return f"{symbol} did not have enough completed examples for this idea."
    idea = strategy_by_id_or_slug(strategy_id.value)
    idea_name = idea.name if idea is not None else strategy_id.value
    return (
        f"{symbol} had {len(completed)} completed examples for {idea_name}. "
        f"{classification_label(classification)}."
    )


def _data_warnings(
    sessions: list[SessionBars],
    usable_sessions: list[SessionBars],
    completed: list[SessionOutcome],
    request: DiscoverySprintRequest,
) -> list[str]:
    warnings: list[str] = []
    if not sessions:
        warnings.append("No local sessions were found for this security.")
    if len(usable_sessions) < request.minimum_useful_sessions:
        warnings.append("There were not many usable first-hour sessions.")
    if len(completed) < request.minimum_examples:
        warnings.append("There were not enough completed examples for a fair first read.")
    if sum(session.quality_issue_count for session in sessions) > 0:
        warnings.append("Some local sessions had data warnings.")
    return warnings


def _tests_run_label(strategy_id: SupportedRuleFamily) -> str:
    if strategy_id == SupportedRuleFamily.FAILED_EARLY_MOVE:
        return "SPY/QQQ comparison, tested versions, checked later in the year"
    return "Simple fixed-rule scan, SPY/QQQ comparison, checked later in the year"


def _best_candidate(
    strategy_id: SupportedRuleFamily,
    classification: DiscoverySprintClassification,
) -> str:
    if strategy_id == SupportedRuleFamily.FAILED_EARLY_MOVE:
        return "Failed push from above and SPY/QQQ disagreement looked better at first."
    if classification in {
        DiscoverySprintClassification.WORTH_MORE_TESTING,
        DiscoverySprintClassification.HELD_UP_ON_LATER_CHECK,
        DiscoverySprintClassification.LOOKED_BETTER_AT_FIRST,
    }:
        idea = strategy_by_id_or_slug(strategy_id.value)
        return f"{idea.name if idea else strategy_id.value} had the clearest first read."
    return "No strong candidate yet."


def _current_conclusion(
    strategy_id: SupportedRuleFamily,
    classification: DiscoverySprintClassification,
) -> str:
    if strategy_id == SupportedRuleFamily.FAILED_EARLY_MOVE:
        return "Those candidates did not clearly hold up later in the year."
    return classification_label(classification)


def _status_label(classification: DiscoverySprintClassification) -> str:
    if classification == DiscoverySprintClassification.WORTH_MORE_TESTING:
        return "worth testing on more history"
    if classification == DiscoverySprintClassification.HELD_UP_ON_LATER_CHECK:
        return "held up later"
    if classification == DiscoverySprintClassification.DID_NOT_HOLD_UP_LATER:
        return "did not hold up later"
    if classification == DiscoverySprintClassification.NOT_ENOUGH_EXAMPLES:
        return "needs more examples"
    if classification == DiscoverySprintClassification.DATA_PROBLEM:
        return "data problem"
    if classification == DiscoverySprintClassification.REJECT_FOR_NOW:
        return "reject for now"
    return "no clear pattern"


def _strategy_next_action(classification: DiscoverySprintClassification) -> str:
    if classification in {
        DiscoverySprintClassification.WORTH_MORE_TESTING,
        DiscoverySprintClassification.HELD_UP_ON_LATER_CHECK,
    }:
        return "Test on more local history before trusting it."
    if classification == DiscoverySprintClassification.NOT_ENOUGH_EXAMPLES:
        return "Get more examples before judging this idea."
    if classification == DiscoverySprintClassification.DATA_PROBLEM:
        return "Review local data before rerunning this idea."
    if classification == DiscoverySprintClassification.REJECT_FOR_NOW:
        return "Reject for now and focus elsewhere."
    return "Keep it on the research board, but do not advance it yet."


def _bottom_line(ranked: list[StrategyDiscoveryResult]) -> str:
    if not ranked:
        return "No strategy idea clearly advanced in this local discovery sprint."
    return f"{ranked[0].strategy_name} is the clearest idea to test on more history."


def _what_found(results: list[StrategyDiscoveryResult]) -> str:
    worth = [
        result.strategy_name
        for result in results
        if result.classification == DiscoverySprintClassification.WORTH_MORE_TESTING
    ]
    if worth:
        return f"EdgeLab found {', '.join(worth)} worth testing on more history."
    return "Most ideas were mixed, thin, or did not advance after the later-year check."


def _worth_more_testing_summary(ranked: list[StrategyDiscoveryResult]) -> str:
    if not ranked:
        return "No idea earned a clear top spot for more history yet."
    return ", ".join(result.strategy_name for result in ranked[:3])


def _did_not_advance_summary(results: list[StrategyDiscoveryResult]) -> str:
    stalled = [
        result.strategy_name
        for result in results
        if result.classification
        in {
            DiscoverySprintClassification.NO_CLEAR_PATTERN,
            DiscoverySprintClassification.NOT_ENOUGH_EXAMPLES,
            DiscoverySprintClassification.DID_NOT_HOLD_UP_LATER,
            DiscoverySprintClassification.REJECT_FOR_NOW,
        }
    ]
    return ", ".join(stalled) if stalled else "No rejected ideas yet."


def _next_action(ranked: list[StrategyDiscoveryResult]) -> str:
    if ranked:
        return "Review the top shortlist, then decide whether more local history is worth buying."
    return "Add more local history or test a different simple idea family."


def _date_range_label(sessions_by_symbol: dict[str, list[SessionBars]]) -> str:
    dates = [
        session.session_date
        for sessions in sessions_by_symbol.values()
        for session in sessions
        if session.readiness == HistoricalIntradayReadiness.READY_FOR_REPLAY
    ]
    if not dates:
        return "No usable local date range"
    return f"{min(dates).isoformat()} through {max(dates).isoformat()}"


def _later_check_label(
    sessions_by_symbol: dict[str, list[SessionBars]],
    request: DiscoverySprintRequest,
) -> str:
    later_dates = [
        session.session_date
        for sessions in sessions_by_symbol.values()
        for session in sessions
        if session.session_date >= request.later_check_start_date
        and session.readiness == HistoricalIntradayReadiness.READY_FOR_REPLAY
    ]
    earlier_dates = [
        session.session_date
        for sessions in sessions_by_symbol.values()
        for session in sessions
        if session.session_date < request.later_check_start_date
        and session.readiness == HistoricalIntradayReadiness.READY_FOR_REPLAY
    ]
    if not later_dates or not earlier_dates:
        return "Later-year check needs more local history"
    return f"{min(later_dates).isoformat()} through {max(later_dates).isoformat()}"


def _regular_bars(bars: tuple[IntradayBar, ...]) -> list[IntradayBar]:
    return [bar for bar in bars if bar.session_type == IntradaySessionType.REGULAR_FIRST_HOUR]


def _historical_bar_to_intraday_bar(bar: HistoricalIntradayBar) -> IntradayBar:
    return IntradayBar(
        symbol=bar.symbol,
        timestamp=bar.timestamp_utc,
        interval=bar.interval,
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=bar.volume,
        session_type=bar.session_type,
        session_id=bar.session_id,
        source=bar.provider,
        ingested_at=bar.ingested_at,
    )


def _favorable_share(outcomes: list[SessionOutcome]) -> float | None:
    return _share(sum(outcome.moved_as_expected for outcome in outcomes), len(outcomes))


def _share(count: int, total: int) -> float | None:
    if total == 0:
        return None
    return count / total
