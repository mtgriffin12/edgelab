"""Baseline comparison scaffolding for research rankings."""

from edgelab.backtesting.schema import BacktestResult, BacktestStatus
from edgelab.discovery.schema import StrategyDiscoveryRecord
from edgelab.ranking.schema import BaselineComparisonResult, EvidenceStrength


def compare_backtest_to_placeholder_baseline(
    result: BacktestResult,
    baseline_description: str,
    baseline_total_return_pct: float = 0.0,
) -> BaselineComparisonResult:
    """Compare a candidate backtest with a clearly labeled sample baseline."""

    did_beat = (
        result.status == BacktestStatus.COMPLETED
        and result.trade_count > 0
        and result.total_return_pct > baseline_total_return_pct
    )
    strength = EvidenceStrength.WEAK if did_beat else EvidenceStrength.INSUFFICIENT
    return BaselineComparisonResult(
        candidate_id=result.strategy_id,
        baseline_description=baseline_description,
        candidate_result_summary=(
            f"Sample result: {result.total_return_pct:.2f}% return, "
            f"{result.max_drawdown_pct:.2f}% worst drop, {result.trade_count} sample events."
        ),
        baseline_result_summary=(
            f"Placeholder baseline assumption: {baseline_total_return_pct:.2f}% sample return."
        ),
        did_candidate_beat_baseline=did_beat,
        improvement_summary=(
            "This idea looks better than its simpler comparison in the sample test, "
            "but the evidence is too thin to trust yet."
            if did_beat
            else "This idea has not beaten its simpler comparison in the current sample."
        ),
        caution="This is a placeholder comparison using synthetic sample data, not real proof.",
        evidence_strength=strength,
    )


def compare_discovery_to_required_baseline(
    record: StrategyDiscoveryRecord,
) -> BaselineComparisonResult:
    """Represent a discovery idea's required simpler comparison."""

    return BaselineComparisonResult(
        candidate_id=record.discovery_id,
        baseline_id=record.baseline_to_beat.baseline_id,
        baseline_description=record.baseline_to_beat.description,
        candidate_result_summary="Discovery idea only; no full evidence run has been completed.",
        baseline_result_summary=record.baseline_to_beat.must_beat,
        did_candidate_beat_baseline=False,
        improvement_summary=(
            "This idea has named the simpler comparison it must beat, but has not beaten it yet."
        ),
        caution="Baseline comparison is a requirement, not a success claim.",
        evidence_strength=EvidenceStrength.INSUFFICIENT,
    )
