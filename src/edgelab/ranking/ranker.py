"""Local strategy metrics and ranking engine."""

from __future__ import annotations

from edgelab.backtesting.engine import BacktestEngine
from edgelab.backtesting.schema import BacktestRequest, BacktestResult, BacktestStatus
from edgelab.data.market_data import LocalFixtureMarketDataProvider
from edgelab.discovery.library import StrategyDiscoveryLibrary
from edgelab.discovery.schema import StrategyDiscoveryRecord, StrategyProvenance
from edgelab.ranking.baseline import (
    compare_backtest_to_placeholder_baseline,
    compare_discovery_to_required_baseline,
)
from edgelab.ranking.schema import (
    EvidenceStrength,
    RankingConclusion,
    RankingQualityIssue,
    RankingRequest,
    RankingResult,
    StrategyScorecard,
)
from edgelab.ranking.scoring import (
    score_backtest_dimensions,
    score_backtest_result,
    score_current_regime_fit,
    score_discovery_overall,
    score_discovery_record,
    score_overfitting_risk,
    score_simplicity,
)
from edgelab.strategies.registry import StrategyRegistry
from edgelab.strategies.schema import StrategySpec


class StrategyRankingEngine:
    """Deterministic local ranking engine for research evidence."""

    def __init__(
        self,
        strategy_registry: StrategyRegistry | None = None,
        discovery_library: StrategyDiscoveryLibrary | None = None,
        market_data_provider: LocalFixtureMarketDataProvider | None = None,
        backtest_engine: BacktestEngine | None = None,
    ) -> None:
        self.strategy_registry = strategy_registry or StrategyRegistry.with_samples()
        self.discovery_library = discovery_library or StrategyDiscoveryLibrary.with_samples()
        self.market_data_provider = market_data_provider or LocalFixtureMarketDataProvider()
        self.backtest_engine = backtest_engine or BacktestEngine()

    def rank(self, request: RankingRequest | None = None) -> RankingResult:
        """Return sorted scorecards from local sample evidence."""

        ranking_request = request or RankingRequest()
        scorecards: list[StrategyScorecard] = []
        if ranking_request.include_strategies:
            scorecards.extend(self._rank_strategies(ranking_request.symbol))
        if ranking_request.include_discovery_records:
            scorecards.extend(self._rank_discovery_records())

        sorted_scorecards = sorted(
            scorecards,
            key=lambda scorecard: scorecard.overall_score,
            reverse=True,
        )
        return RankingResult(
            request=ranking_request,
            scorecards=sorted_scorecards,
            top_research_candidates=self.top_research_candidates(sorted_scorecards),
            weak_candidates=self.weak_candidates(sorted_scorecards),
            quality_issues=[
                RankingQualityIssue(
                    code="synthetic_sample_data",
                    message="Rankings use local synthetic samples and scaffolded metadata only.",
                )
            ],
        )

    def top_research_candidates(
        self, scorecards: list[StrategyScorecard] | None = None
    ) -> list[StrategyScorecard]:
        """Return the highest-ranking research candidates."""

        cards = scorecards if scorecards is not None else self.rank().scorecards
        return [
            scorecard
            for scorecard in cards
            if scorecard.conclusion
            in {
                RankingConclusion.PROMISING_RESEARCH_CANDIDATE,
                RankingConclusion.BEATS_BASELINE_IN_SAMPLE,
                RankingConclusion.NEEDS_MORE_TESTING,
            }
        ][:5]

    def weak_candidates(
        self, scorecards: list[StrategyScorecard] | None = None
    ) -> list[StrategyScorecard]:
        """Return weak, rejected, unsupported, or insufficient candidates."""

        cards = scorecards if scorecards is not None else self.rank().scorecards
        weak_conclusions = {
            RankingConclusion.INSUFFICIENT_EVIDENCE,
            RankingConclusion.WEAK_EVIDENCE,
            RankingConclusion.REJECTED_FOR_NOW,
            RankingConclusion.UNSUPPORTED,
        }
        return [scorecard for scorecard in cards if scorecard.conclusion in weak_conclusions]

    def filter_by_evidence_strength(
        self, strength: EvidenceStrength, scorecards: list[StrategyScorecard] | None = None
    ) -> list[StrategyScorecard]:
        """Filter scorecards by evidence strength."""

        cards = scorecards if scorecards is not None else self.rank().scorecards
        return [scorecard for scorecard in cards if scorecard.evidence_strength == strength]

    def filter_by_conclusion(
        self, conclusion: RankingConclusion, scorecards: list[StrategyScorecard] | None = None
    ) -> list[StrategyScorecard]:
        """Filter scorecards by conclusion."""

        cards = scorecards if scorecards is not None else self.rank().scorecards
        return [scorecard for scorecard in cards if scorecard.conclusion == conclusion]

    def get_scorecard(self, scorecard_id: str) -> StrategyScorecard | None:
        """Return one generated sample scorecard."""

        for scorecard in self.rank().scorecards:
            if scorecard.scorecard_id == scorecard_id:
                return scorecard
        return None

    def _rank_strategies(self, symbol: str) -> list[StrategyScorecard]:
        return [
            self._score_strategy(strategy, symbol)
            for strategy in self.strategy_registry.list_strategies()
        ]

    def _score_strategy(self, strategy: StrategySpec, symbol: str) -> StrategyScorecard:
        data = self.market_data_provider.load_bars(symbol)
        result = self.backtest_engine.run(
            strategy,
            data.bars,
            BacktestRequest(strategy_id=strategy.strategy_id, symbol=symbol),
        )
        discovery = self._find_discovery_for_strategy(strategy.strategy_id)
        dimension_scores = score_backtest_dimensions(result)
        if discovery is not None:
            dimension_scores.extend(
                [
                    score_simplicity(discovery.complexity_score),
                    score_current_regime_fit(discovery),
                    score_overfitting_risk(discovery),
                ]
            )
        score = _blend_strategy_score(result, discovery)
        conclusion = _conclusion_for_strategy_result(result, score)
        evidence_strength = _evidence_strength_for_result(result, score)
        baseline = compare_backtest_to_placeholder_baseline(
            result,
            baseline_description=(
                discovery.baseline_to_beat.description
                if discovery is not None
                else "Simple hold-flat sample baseline"
            ),
        )
        quality_issues = [
            RankingQualityIssue(
                code=issue.code,
                message=issue.message,
                severity=issue.severity,
            )
            for issue in result.quality_issues
        ]
        return StrategyScorecard(
            scorecard_id=f"strategy-{strategy.strategy_id}",
            strategy_id=strategy.strategy_id,
            discovery_id=discovery.discovery_id if discovery is not None else None,
            title=strategy.name,
            evidence_strength=evidence_strength,
            conclusion=conclusion,
            overall_score=score,
            dimension_scores=dimension_scores,
            baseline_comparison=baseline,
            plain_english_summary=_summary_for_strategy_result(result, conclusion),
            why_it_ranked_this_way=_why_strategy_ranked(result, discovery),
            what_helped=_what_helped_strategy(result, discovery),
            what_hurt=_what_hurt_strategy(result),
            evidence_gaps=_strategy_evidence_gaps(result),
            caution="This is research triage from sample data, not real-money permission.",
            not_ready_reasons=[
                "Uses synthetic fixture data.",
                "Has not passed robustness or walk-forward testing.",
                "Real-money use remains blocked.",
            ],
            quality_issues=quality_issues,
        )

    def _rank_discovery_records(self) -> list[StrategyScorecard]:
        return [
            self._score_discovery_record(record) for record in self.discovery_library.list_records()
        ]

    def _score_discovery_record(self, record: StrategyDiscoveryRecord) -> StrategyScorecard:
        score = score_discovery_overall(record)
        conclusion = _conclusion_for_discovery(record, score)
        evidence_strength = _evidence_strength_for_discovery(record, score)
        return StrategyScorecard(
            scorecard_id=f"discovery-{record.discovery_id}",
            strategy_id=record.derived_strategy_id,
            discovery_id=record.discovery_id,
            title=record.title,
            evidence_strength=evidence_strength,
            conclusion=conclusion,
            overall_score=score,
            dimension_scores=score_discovery_record(record),
            baseline_comparison=compare_discovery_to_required_baseline(record),
            plain_english_summary=_summary_for_discovery(record, conclusion),
            why_it_ranked_this_way=[
                (
                    "Discovery records are ranked on evidence discipline, simplicity, "
                    "static environment fit, and curve-fit risk."
                ),
                "No discovery record is treated as proven in this phase.",
            ],
            what_helped=_what_helped_discovery(record),
            what_hurt=_what_hurt_discovery(record),
            evidence_gaps=[
                "Needs point-in-time historical testing.",
                "Needs a real baseline comparison before promotion.",
                "Needs robustness testing across regimes.",
            ],
            caution="This is an idea-ranking scaffold, not proof.",
            not_ready_reasons=[
                "No full historical evidence is attached yet.",
                "No paper or real-money eligibility is granted.",
            ],
        )

    def _find_discovery_for_strategy(self, strategy_id: str) -> StrategyDiscoveryRecord | None:
        for record in self.discovery_library.list_records():
            if record.derived_strategy_id == strategy_id:
                return record
        return None


def _blend_strategy_score(
    result: BacktestResult,
    discovery: StrategyDiscoveryRecord | None,
) -> float:
    backtest_score = score_backtest_result(result)
    if discovery is None:
        return backtest_score
    discovery_score = score_discovery_overall(discovery)
    if result.status == BacktestStatus.UNSUPPORTED_STRATEGY:
        return min(backtest_score, 25.0)
    return round((backtest_score * 0.72) + (discovery_score * 0.28), 6)


def _evidence_strength_for_result(result: BacktestResult, score: float) -> EvidenceStrength:
    if result.status == BacktestStatus.UNSUPPORTED_STRATEGY or result.trade_count == 0:
        return EvidenceStrength.INSUFFICIENT
    if result.trade_count < 5:
        return EvidenceStrength.WEAK
    if score >= 72:
        return EvidenceStrength.MODERATE
    if score >= 55:
        return EvidenceStrength.MIXED
    return EvidenceStrength.WEAK


def _conclusion_for_strategy_result(result: BacktestResult, score: float) -> RankingConclusion:
    if result.status == BacktestStatus.UNSUPPORTED_STRATEGY:
        return RankingConclusion.UNSUPPORTED
    if result.trade_count == 0:
        return RankingConclusion.INSUFFICIENT_EVIDENCE
    if result.trade_count < 5:
        return RankingConclusion.NEEDS_MORE_TESTING
    if result.total_return_pct > 0 and result.max_drawdown_pct < 10 and score >= 60:
        return RankingConclusion.BEATS_BASELINE_IN_SAMPLE
    if result.max_drawdown_pct > 15:
        return RankingConclusion.INTERESTING_BUT_FRAGILE
    return RankingConclusion.NEEDS_MORE_TESTING


def _evidence_strength_for_discovery(
    record: StrategyDiscoveryRecord, score: float
) -> EvidenceStrength:
    if record.provenance == StrategyProvenance.NOVEL_HYPOTHESIS:
        return EvidenceStrength.WEAK
    if score >= 65:
        return EvidenceStrength.MIXED
    if score >= 45:
        return EvidenceStrength.WEAK
    return EvidenceStrength.INSUFFICIENT


def _conclusion_for_discovery(record: StrategyDiscoveryRecord, score: float) -> RankingConclusion:
    if record.provenance == StrategyProvenance.REJECTED:
        return RankingConclusion.REJECTED_FOR_NOW
    if record.current_regime_fit.score <= 3 or record.overfitting_risk_score >= 8:
        return RankingConclusion.WEAK_EVIDENCE
    if score >= 62 and record.provenance != StrategyProvenance.NOVEL_HYPOTHESIS:
        return RankingConclusion.PROMISING_RESEARCH_CANDIDATE
    if score >= 50:
        return RankingConclusion.NEEDS_MORE_TESTING
    return RankingConclusion.INSUFFICIENT_EVIDENCE


def _summary_for_strategy_result(result: BacktestResult, conclusion: RankingConclusion) -> str:
    if conclusion == RankingConclusion.UNSUPPORTED:
        return "Unsupported by the current placeholder historical-test engine."
    if result.trade_count == 0:
        return "Insufficient sample evidence; no completed sample events were available."
    return (
        f"Sample evidence shows {result.trade_count} events, "
        f"{result.total_return_pct:.2f}% return, and "
        f"{result.max_drawdown_pct:.2f}% worst drop."
    )


def _summary_for_discovery(
    record: StrategyDiscoveryRecord,
    conclusion: RankingConclusion,
) -> str:
    return (
        f"{record.plain_english_summary} Current ranking conclusion: "
        f"{conclusion.value.replace('_', ' ')}."
    )


def _why_strategy_ranked(
    result: BacktestResult,
    discovery: StrategyDiscoveryRecord | None,
) -> list[str]:
    reasons = [
        "Worst drop, event count, gain/loss balance, and data cautions all affect the score.",
        "Total return is capped so it cannot dominate the ranking.",
    ]
    if result.status == BacktestStatus.UNSUPPORTED_STRATEGY:
        reasons.append("The Phase 4 engine does not support this strategy behavior yet.")
    if discovery is not None:
        reasons.append("Discovery metadata adds simplicity and static environment-fit context.")
    return reasons


def _what_helped_strategy(
    result: BacktestResult,
    discovery: StrategyDiscoveryRecord | None,
) -> list[str]:
    helped: list[str] = []
    if result.total_return_pct > 0:
        helped.append("Positive sample return helped.")
    if result.max_drawdown_pct < 5:
        helped.append("Worst drop was small in the sample.")
    if discovery is not None and discovery.current_regime_fit.score >= 6:
        helped.append("Static environment fit was possible or better.")
    return helped or ["Nothing strong enough to call out yet."]


def _what_hurt_strategy(result: BacktestResult) -> list[str]:
    hurt: list[str] = []
    if result.trade_count < 5:
        hurt.append("Too few sample events.")
    if result.status == BacktestStatus.UNSUPPORTED_STRATEGY:
        hurt.append("Unsupported placeholder strategy behavior.")
    if result.quality_issues:
        hurt.append("Quality issues were reported.")
    return hurt or ["Evidence remains thin because it uses synthetic sample data."]


def _strategy_evidence_gaps(result: BacktestResult) -> list[str]:
    gaps = [
        "Needs real point-in-time market data later.",
        "Needs baseline and robustness tests.",
    ]
    if result.trade_count < 30:
        gaps.append("Needs a larger sample size.")
    return gaps


def _what_helped_discovery(record: StrategyDiscoveryRecord) -> list[str]:
    helped = ["It names the simpler comparison it must beat."]
    if record.current_regime_fit.score >= 6:
        helped.append("Static environment fit is possible or better.")
    if record.complexity_score <= 4:
        helped.append("The idea is relatively simple.")
    return helped


def _what_hurt_discovery(record: StrategyDiscoveryRecord) -> list[str]:
    hurt = ["No full historical evidence is attached yet."]
    if record.overfitting_risk_score >= 7:
        hurt.append("Curve-fit risk is high.")
    if record.provenance == StrategyProvenance.NOVEL_HYPOTHESIS:
        hurt.append("Novel ideas require stricter evidence.")
    if record.current_regime_fit.score <= 4:
        hurt.append("Static environment fit is weak or poor.")
    return hurt
