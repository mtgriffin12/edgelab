"""Product-facing view models for intraday research pages."""

from __future__ import annotations

from dataclasses import dataclass

from edgelab.intraday.out_of_sample_gate_schema import (
    OutOfSampleGateConclusion,
    OutOfSampleGateResult,
)
from edgelab.research_runs.schema import (
    ResearchRunFreshness,
    ResearchRunFreshnessStatus,
    SavedResearchRun,
)


@dataclass(frozen=True)
class IntradayResearchIdeaRow:
    """One strategy idea in the Intraday Research list."""

    strategy_id: str
    strategy_name: str
    securities_tested: str
    tests_run: str
    best_current_pattern_candidate: str
    current_conclusion: str
    status: str
    next_research_action: str
    last_run_date: str


@dataclass(frozen=True)
class IntradaySecurityResearchRow:
    """One security tested for an intraday strategy idea."""

    symbol: str
    latest_saved_result: str
    data_status: str
    last_run_date: str


@dataclass(frozen=True)
class IntradayTestRunRow:
    """One research test shown inside a strategy detail page."""

    test_name: str
    securities: str
    result: str
    evidence_href: str


@dataclass(frozen=True)
class IntradayPatternCandidateRow:
    """One candidate pattern/version from existing intraday research."""

    candidate_name: str
    evidence_seen: str
    later_check: str
    conclusion: str


@dataclass(frozen=True)
class IntradayEvidenceLink:
    """Legacy evidence page link kept below the product summary."""

    label: str
    href: str
    description: str


@dataclass(frozen=True)
class FailedEarlyMoveResearchDetail:
    """Product-level summary for the first intraday strategy idea."""

    idea_name: str
    result_summary: str
    securities_tested: tuple[IntradaySecurityResearchRow, ...]
    tests_run: tuple[IntradayTestRunRow, ...]
    best_pattern_candidates: tuple[IntradayPatternCandidateRow, ...]
    current_conclusion: str
    next_research_action: str
    evidence_links: tuple[IntradayEvidenceLink, ...]
    safety_status: str


SavedState = tuple[SavedResearchRun | None, ResearchRunFreshness]


def build_intraday_research_rows(
    *,
    saved_states: dict[str, SavedState],
    out_of_sample_result: OutOfSampleGateResult | None = None,
) -> list[IntradayResearchIdeaRow]:
    """Return strategy-idea rows for the Intraday Research list."""

    detail = build_failed_early_move_detail(
        saved_states=saved_states,
        out_of_sample_result=out_of_sample_result,
    )
    return [
        IntradayResearchIdeaRow(
            strategy_id="failed-early-move",
            strategy_name=detail.idea_name,
            securities_tested="SPY, QQQ",
            tests_run=(
                "Past morning replay, SPY vs QQQ comparison, pattern-version test, "
                "later-period check"
            ),
            best_current_pattern_candidate=(
                "Failed push from above and SPY/QQQ disagreement looked somewhat interesting "
                "at first."
            ),
            current_conclusion=detail.current_conclusion,
            status=_status_for_detail(detail),
            next_research_action=detail.next_research_action,
            last_run_date=_latest_run_date(saved_states),
        )
    ]


def build_failed_early_move_detail(
    *,
    saved_states: dict[str, SavedState],
    out_of_sample_result: OutOfSampleGateResult | None = None,
) -> FailedEarlyMoveResearchDetail:
    """Build the product-level Failed Early Move research detail."""

    current_conclusion = _current_conclusion(out_of_sample_result)
    next_action = "Get more SPY/QQQ history or test a different pattern family."
    return FailedEarlyMoveResearchDetail(
        idea_name="Failed Early Move",
        result_summary=(
            "EdgeLab tested whether the first strong move of the morning failed often enough "
            "to become a useful research idea across SPY and QQQ."
        ),
        securities_tested=(
            _security_row("SPY", saved_states.get("SPY")),
            _security_row("QQQ", saved_states.get("QQQ")),
        ),
        tests_run=(
            IntradayTestRunRow(
                test_name="Historical data readiness",
                securities="SPY, QQQ",
                result=(
                    "Local files and saved results tell EdgeLab whether the evidence is current."
                ),
                evidence_href="/ui/intraday-lab/firstrate",
            ),
            IntradayTestRunRow(
                test_name="SPY vs QQQ comparison",
                securities="SPY, QQQ",
                result="SPY looked more interesting than QQQ in the first comparison.",
                evidence_href="/ui/intraday-lab/comparative-study/spy-qqq/opening-range-failure",
            ),
            IntradayTestRunRow(
                test_name="Tested versions of the idea",
                securities="SPY with QQQ context",
                result="Failed push from above and SPY/QQQ disagreement looked worth inspecting.",
                evidence_href="/ui/intraday-lab/variant-study/spy/early-move-failed",
            ),
            IntradayTestRunRow(
                test_name="Later-year check",
                securities="SPY with QQQ context",
                result=_later_period_result(out_of_sample_result),
                evidence_href="/ui/intraday-lab/out-of-sample/spy/early-move-failed",
            ),
        ),
        best_pattern_candidates=(
            IntradayPatternCandidateRow(
                candidate_name="Failed push from above",
                evidence_seen="Looked somewhat interesting at first.",
                later_check="Did not clearly hold up later in the year.",
                conclusion="No clear pattern to advance yet.",
            ),
            IntradayPatternCandidateRow(
                candidate_name="SPY/QQQ disagreement",
                evidence_seen="Looked somewhat interesting at first.",
                later_check="Did not clearly hold up later in the year.",
                conclusion="No clear pattern to advance yet.",
            ),
        ),
        current_conclusion=current_conclusion,
        next_research_action=next_action,
        evidence_links=_evidence_links(),
        safety_status="Research only · Not live · Real-money status: Not allowed",
    )


def _security_row(symbol: str, state: SavedState | None) -> IntradaySecurityResearchRow:
    if state is None:
        return IntradaySecurityResearchRow(
            symbol=symbol,
            latest_saved_result="No saved result found.",
            data_status="Needs local analysis.",
            last_run_date="No saved result yet",
        )
    run, freshness = state
    if run is None:
        return IntradaySecurityResearchRow(
            symbol=symbol,
            latest_saved_result="No saved result found.",
            data_status=_freshness_label(freshness),
            last_run_date="No saved result yet",
        )
    return IntradaySecurityResearchRow(
        symbol=symbol,
        latest_saved_result=run.plain_english_bottom_line,
        data_status=_freshness_label(freshness),
        last_run_date=run.completed_at.date().isoformat(),
    )


def _current_conclusion(result: OutOfSampleGateResult | None) -> str:
    if result is None:
        return "No clear pattern to advance yet."
    if result.gate_conclusion == OutOfSampleGateConclusion.HELD_UP_IN_FIRST_CHECK:
        return "One candidate stayed interesting later, but it still needs more testing."
    if result.gate_conclusion == OutOfSampleGateConclusion.BLOCKED_BY_DATA_QUALITY:
        return "Local data needs review before EdgeLab can judge the idea."
    if result.gate_conclusion in {
        OutOfSampleGateConclusion.NOT_ENOUGH_HOLDOUT_EXAMPLES,
        OutOfSampleGateConclusion.NEEDS_MORE_DATA,
    }:
        return "EdgeLab needs more examples before advancing this idea."
    return "The leading candidates did not clearly hold up later in the year."


def _later_period_result(result: OutOfSampleGateResult | None) -> str:
    if result is None:
        return "Not run on this page yet."
    return result.gate_conclusion_translation


def _freshness_label(freshness: ResearchRunFreshness) -> str:
    if freshness.status == ResearchRunFreshnessStatus.FRESH:
        return "Current for the local file"
    if freshness.status == ResearchRunFreshnessStatus.NOT_FOUND:
        return "Needs local analysis"
    return "Needs review"


def _status_for_detail(detail: FailedEarlyMoveResearchDetail) -> str:
    if "needs more" in detail.current_conclusion.lower():
        return "needs more data"
    if "stayed interesting" in detail.current_conclusion.lower():
        return "worth more testing"
    if "data needs review" in detail.current_conclusion.lower():
        return "needs more data"
    return "no clear pattern"


def _latest_run_date(saved_states: dict[str, SavedState]) -> str:
    dates = [
        run.completed_at.date().isoformat()
        for run, _freshness in saved_states.values()
        if run is not None
    ]
    return max(dates) if dates else "No saved result yet"


def _evidence_links() -> tuple[IntradayEvidenceLink, ...]:
    return (
        IntradayEvidenceLink(
            label="Historical data readiness",
            href="/ui/intraday-lab/firstrate",
            description="Detailed local file and first-hour quality evidence.",
        ),
        IntradayEvidenceLink(
            label="SPY vs QQQ comparison",
            href="/ui/intraday-lab/comparative-study/spy-qqq/opening-range-failure",
            description="Detailed comparison for the failed early move idea.",
        ),
        IntradayEvidenceLink(
            label="Tested pattern versions",
            href="/ui/intraday-lab/variant-study/spy/early-move-failed",
            description="Detailed fixed-version test for SPY.",
        ),
        IntradayEvidenceLink(
            label="Later-year check",
            href="/ui/intraday-lab/out-of-sample/spy/early-move-failed",
            description="Detailed holdout-style check.",
        ),
        IntradayEvidenceLink(
            label="Saved results",
            href="/ui/intraday-lab/research-runs",
            description="Local saved research results used as current context.",
        ),
    )
