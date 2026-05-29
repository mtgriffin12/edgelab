"""Deterministic scoring helpers for research-only rankings."""

from __future__ import annotations

from edgelab.backtesting.schema import BacktestResult, BacktestStatus
from edgelab.discovery.schema import StrategyDiscoveryRecord
from edgelab.ranking.schema import MetricScore, RankingDimension


def clamp_score(value: float) -> float:
    """Clamp a score to the 0-100 range."""

    return round(max(0.0, min(100.0, value)), 6)


def score_return_quality(total_return_pct: float) -> MetricScore:
    """Score return while keeping the result capped and conservative."""

    score = clamp_score(45.0 + (total_return_pct * 4.0))
    return MetricScore(
        dimension=RankingDimension.RETURN_QUALITY,
        score=score,
        plain_english_reason=(
            "Return helps, but it is capped so it cannot overpower risk and evidence quality."
        ),
    )


def score_worst_drop_control(max_drawdown_pct: float) -> MetricScore:
    """Score worst-drop control."""

    score = clamp_score(100.0 - (max_drawdown_pct * 5.0))
    return MetricScore(
        dimension=RankingDimension.WORST_DROP_CONTROL,
        score=score,
        plain_english_reason="Smaller worst drops rank better than fragile high-return paths.",
    )


def score_consistency(win_rate_pct: float) -> MetricScore:
    """Score a simple consistency proxy."""

    score = clamp_score(25.0 + (win_rate_pct * 0.75))
    return MetricScore(
        dimension=RankingDimension.CONSISTENCY,
        score=score,
        plain_english_reason="A steadier sample helps, but win rate is not treated as proof.",
    )


def score_trade_sample_size(trade_count: int) -> MetricScore:
    """Score whether the sample is large enough to take seriously."""

    if trade_count >= 30:
        score = 100.0
    elif trade_count >= 10:
        score = 75.0
    elif trade_count >= 5:
        score = 50.0
    elif trade_count >= 1:
        score = 25.0
    else:
        score = 0.0
    return MetricScore(
        dimension=RankingDimension.TRADE_SAMPLE_SIZE,
        score=score,
        plain_english_reason="Too few sample events make the evidence thin.",
    )


def score_profit_loss_balance(profit_factor: float | None, win_rate_pct: float) -> MetricScore:
    """Score profit/loss balance with capped profit factor influence."""

    if profit_factor is None:
        score = 40.0 if win_rate_pct > 0 else 10.0
    else:
        score = 30.0 + min(profit_factor, 3.0) * 20.0
    return MetricScore(
        dimension=RankingDimension.BASELINE_ADVANTAGE,
        score=clamp_score(score),
        plain_english_reason="Gain/loss balance helps, but extreme values are capped.",
    )


def score_cost_sensitivity(result: BacktestResult) -> MetricScore:
    """Score explicit cost assumptions and fixture limitation."""

    assumptions = result.assumptions_summary
    commission = _float_assumption(assumptions.get("commission_per_trade", 0.0))
    slippage_bps = _float_assumption(assumptions.get("slippage_bps", 0.0))
    score = 70.0 - (commission * 2.0) - (slippage_bps * 2.0)
    return MetricScore(
        dimension=RankingDimension.COST_SENSITIVITY,
        score=clamp_score(score),
        plain_english_reason=(
            "This phase has only simple cost assumptions, so cost confidence remains limited."
        ),
    )


def score_data_quality(issue_count: int) -> MetricScore:
    """Score quality issue count."""

    return MetricScore(
        dimension=RankingDimension.DATA_QUALITY,
        score=clamp_score(100.0 - (issue_count * 25.0)),
        plain_english_reason="More data or engine cautions lower the ranking.",
    )


def score_simplicity(complexity_score: int | None) -> MetricScore:
    """Score simplicity from discovery complexity metadata."""

    if complexity_score is None:
        score = 60.0
    else:
        score = 100.0 - (complexity_score * 8.0)
    return MetricScore(
        dimension=RankingDimension.SIMPLICITY,
        score=clamp_score(score),
        plain_english_reason="Complexity must earn its place with stronger evidence.",
    )


def score_current_regime_fit(record: StrategyDiscoveryRecord | None) -> MetricScore:
    """Score static current-regime-fit scaffolding."""

    score = 35.0 if record is None else record.current_regime_fit.score * 10.0
    return MetricScore(
        dimension=RankingDimension.CURRENT_REGIME_FIT,
        score=clamp_score(score),
        plain_english_reason=(
            "Static environment fit helps only a little until real regime data exists."
        ),
    )


def _float_assumption(value: object) -> float:
    if isinstance(value, int | float | str):
        return float(value)
    return 0.0


def score_overfitting_risk(record: StrategyDiscoveryRecord | None) -> MetricScore:
    """Score lower curve-fit risk higher."""

    score = 50.0 if record is None else 100.0 - (record.overfitting_risk_score * 10.0)
    return MetricScore(
        dimension=RankingDimension.OVERFITTING_RISK,
        score=clamp_score(score),
        plain_english_reason="Higher curve-fit risk lowers confidence.",
    )


def score_backtest_dimensions(result: BacktestResult) -> list[MetricScore]:
    """Build metric scores from a backtest result."""

    issue_count = len(result.quality_issues)
    if result.status == BacktestStatus.UNSUPPORTED_STRATEGY:
        issue_count += 2
    return [
        score_return_quality(result.total_return_pct),
        score_worst_drop_control(result.max_drawdown_pct),
        score_consistency(result.win_rate_pct),
        score_trade_sample_size(result.trade_count),
        score_profit_loss_balance(result.profit_factor, result.win_rate_pct),
        score_cost_sensitivity(result),
        score_data_quality(issue_count),
    ]


def weighted_score(scores: list[MetricScore], weights: dict[RankingDimension, float]) -> float:
    """Calculate a weighted score."""

    if not scores:
        return 0.0
    score_by_dimension = {score.dimension: score.score for score in scores}
    total_weight = 0.0
    weighted_total = 0.0
    for dimension, weight in weights.items():
        if dimension in score_by_dimension:
            total_weight += weight
            weighted_total += score_by_dimension[dimension] * weight
    if total_weight <= 0:
        return 0.0
    return clamp_score(weighted_total / total_weight)


def score_backtest_result(result: BacktestResult) -> float:
    """Score a backtest result conservatively."""

    scores = score_backtest_dimensions(result)
    raw_score = weighted_score(
        scores,
        {
            RankingDimension.RETURN_QUALITY: 0.16,
            RankingDimension.WORST_DROP_CONTROL: 0.24,
            RankingDimension.CONSISTENCY: 0.12,
            RankingDimension.TRADE_SAMPLE_SIZE: 0.18,
            RankingDimension.BASELINE_ADVANTAGE: 0.10,
            RankingDimension.COST_SENSITIVITY: 0.08,
            RankingDimension.DATA_QUALITY: 0.12,
        },
    )
    if result.status == BacktestStatus.UNSUPPORTED_STRATEGY:
        return min(raw_score, 20.0)
    if result.trade_count < 2:
        return min(raw_score, 45.0)
    return raw_score


def score_discovery_record(record: StrategyDiscoveryRecord) -> list[MetricScore]:
    """Score discovery metadata without pretending it is proof."""

    baseline_score = 55.0 if record.baseline_to_beat.must_beat else 15.0
    sentiment_score = 55.0 if "sentiment" in record.behavior_type.value else 40.0
    return [
        MetricScore(
            dimension=RankingDimension.BASELINE_ADVANTAGE,
            score=baseline_score,
            plain_english_reason="A named simpler comparison improves research discipline.",
        ),
        score_simplicity(record.complexity_score),
        score_current_regime_fit(record),
        score_overfitting_risk(record),
        MetricScore(
            dimension=RankingDimension.SENTIMENT_CONTEXT,
            score=sentiment_score,
            plain_english_reason="Sentiment-aware ideas remain context only in this phase.",
        ),
        score_data_quality(0),
    ]


def score_discovery_overall(record: StrategyDiscoveryRecord) -> float:
    """Score a discovery record conservatively."""

    return weighted_score(
        score_discovery_record(record),
        {
            RankingDimension.BASELINE_ADVANTAGE: 0.18,
            RankingDimension.SIMPLICITY: 0.20,
            RankingDimension.CURRENT_REGIME_FIT: 0.18,
            RankingDimension.OVERFITTING_RISK: 0.24,
            RankingDimension.SENTIMENT_CONTEXT: 0.08,
            RankingDimension.DATA_QUALITY: 0.12,
        },
    )
