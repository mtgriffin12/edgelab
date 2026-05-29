"""Local fixture-backed candidate equity screener."""

from __future__ import annotations

from collections.abc import Iterable

from edgelab.candidates.schema import (
    CandidateMarketSnapshot,
    CandidateQualityIssue,
    CandidateReason,
    CandidateRiskFlag,
    CandidateRiskFlagType,
    CandidateScreeningRequest,
    CandidateScreeningResult,
    CandidateSentimentSnapshot,
    CandidateSource,
    CandidateStatus,
    EquityCandidate,
)
from edgelab.candidates.scoring import (
    evidence_strength_for_score,
    score_candidate,
    status_for_candidate,
)
from edgelab.data.market_data import LocalFixtureMarketDataProvider
from edgelab.data.sentiment import LocalFixtureSentimentProvider
from edgelab.discovery.library import StrategyDiscoveryLibrary
from edgelab.ranking.ranker import StrategyRankingEngine
from edgelab.ranking.schema import RankingConclusion, StrategyScorecard
from edgelab.strategies.registry import StrategyRegistry


class CandidateEquityScreener:
    """Generate local research-only equity candidates from fixture evidence."""

    def __init__(
        self,
        market_data_provider: LocalFixtureMarketDataProvider | None = None,
        sentiment_provider: LocalFixtureSentimentProvider | None = None,
        strategy_registry: StrategyRegistry | None = None,
        discovery_library: StrategyDiscoveryLibrary | None = None,
        ranking_engine: StrategyRankingEngine | None = None,
    ) -> None:
        self.market_data_provider = market_data_provider or LocalFixtureMarketDataProvider()
        self.sentiment_provider = sentiment_provider or LocalFixtureSentimentProvider()
        self.strategy_registry = strategy_registry or StrategyRegistry.with_samples()
        self.discovery_library = discovery_library or StrategyDiscoveryLibrary.with_samples()
        self.ranking_engine = ranking_engine or StrategyRankingEngine(
            strategy_registry=self.strategy_registry,
            discovery_library=self.discovery_library,
            market_data_provider=self.market_data_provider,
        )

    def screen(self, request: CandidateScreeningRequest | None = None) -> CandidateScreeningResult:
        """Screen the local fixture universe and return sorted candidates."""

        screening_request = request or CandidateScreeningRequest()
        universe = self._candidate_symbols(screening_request.symbols)
        scorecards = self.ranking_engine.rank().scorecards
        all_candidates = [self._build_candidate(symbol, scorecards) for symbol in universe]
        candidates = [
            candidate
            for candidate in all_candidates
            if candidate.candidate_score >= screening_request.min_score
            and (
                screening_request.include_watchlist_only
                or candidate.status != CandidateStatus.WATCHLIST_ONLY
            )
            and (
                screening_request.include_rejected
                or candidate.status != CandidateStatus.REJECTED_FOR_NOW
            )
        ]
        candidates.sort(key=lambda candidate: candidate.candidate_score, reverse=True)
        return CandidateScreeningResult(
            universe_size=len(universe),
            candidate_count=len(candidates),
            candidates=candidates,
            rejected_count=len(all_candidates) - len(candidates),
            quality_issues=[
                CandidateQualityIssue(
                    code="synthetic_fixture_universe",
                    message="The candidate universe is limited to local synthetic fixture symbols.",
                )
            ],
            plain_english_summary=(
                "EdgeLab surfaced local research candidates from built-in sample data, "
                "sample strategy ideas, and ranking scorecards. Nothing is approved for "
                "real-money use."
            ),
        )

    def get_candidate(self, candidate_id: str) -> EquityCandidate | None:
        """Return one generated candidate by ID."""

        for candidate in self.screen().candidates:
            if candidate.candidate_id == candidate_id:
                return candidate
        return None

    def list_symbols(self) -> list[str]:
        """Return the local candidate fixture symbols."""

        return self._candidate_symbols(None)

    def research_watchlist(self) -> list[EquityCandidate]:
        """Return candidates worth keeping visible for deeper research."""

        statuses = {
            CandidateStatus.RESEARCH_CANDIDATE,
            CandidateStatus.INTERESTING_BUT_INCOMPLETE,
            CandidateStatus.WATCHLIST_ONLY,
        }
        return [candidate for candidate in self.screen().candidates if candidate.status in statuses]

    def _candidate_symbols(self, requested_symbols: list[str] | None) -> list[str]:
        market_symbols = set(self.market_data_provider.list_available_symbols())
        sentiment_symbols = set(self.sentiment_provider.list_available_symbols())
        symbols = sorted(market_symbols | sentiment_symbols)
        if requested_symbols is None:
            return symbols
        requested = set(requested_symbols)
        return [symbol for symbol in symbols if symbol in requested]

    def _build_candidate(self, symbol: str, scorecards: list[StrategyScorecard]) -> EquityCandidate:
        market_snapshot, market_issues = self._market_snapshot(symbol)
        sentiment_snapshot, sentiment_issues = self._sentiment_snapshot(symbol)
        matched_strategies = self._matched_strategies(symbol)
        matched_discoveries = self._matched_discovery_ids(symbol)
        matched_scorecards = self._matched_scorecards(
            matched_strategies, matched_discoveries, scorecards
        )
        supports = self._support_reasons(
            symbol, matched_strategies, matched_discoveries, matched_scorecards
        )
        risk_flags = self._risk_flags(market_snapshot, sentiment_snapshot, matched_scorecards)
        quality_issues = market_issues + sentiment_issues
        highest_score = max((card.overall_score for card in matched_scorecards), default=0.0)
        score = score_candidate(
            highest_ranking_score=highest_score,
            support_count=len(supports),
            market_quality_issue_count=market_snapshot.quality_issue_count
            if market_snapshot
            else 1,
            sentiment_quality_issue_count=(
                sentiment_snapshot.quality_issue_count if sentiment_snapshot else 1
            ),
            risk_flag_count=len(risk_flags),
            sentiment_event_count=sentiment_snapshot.event_count if sentiment_snapshot else 0,
        )
        has_unsupported = bool(matched_scorecards) and all(
            card.conclusion == RankingConclusion.UNSUPPORTED for card in matched_scorecards
        )
        evidence_strength = evidence_strength_for_score(
            score,
            support_count=len(supports),
            quality_issue_count=len(quality_issues),
            has_unsupported_logic=has_unsupported,
        )
        status = status_for_candidate(
            score,
            evidence_strength,
            quality_issue_count=len(quality_issues),
            has_blocking_risk=has_unsupported and not matched_scorecards,
        )
        return EquityCandidate(
            candidate_id=f"{symbol.lower()}-research-candidate",
            symbol=symbol,
            title=f"{symbol} Research Candidate",
            status=status,
            evidence_strength=evidence_strength,
            candidate_score=score,
            plain_english_summary=_summary(symbol, status),
            what_supports_it=supports,
            what_is_missing=_missing_evidence(),
            what_would_change_our_mind=_change_our_mind(),
            matched_strategy_ids=matched_strategies,
            matched_discovery_ids=matched_discoveries,
            matched_scorecard_ids=[card.scorecard_id for card in matched_scorecards],
            market_snapshot=market_snapshot,
            sentiment_snapshot=sentiment_snapshot,
            risk_flags=risk_flags,
            quality_issues=quality_issues,
        )

    def _market_snapshot(
        self, symbol: str
    ) -> tuple[CandidateMarketSnapshot | None, list[CandidateQualityIssue]]:
        data = self.market_data_provider.load_bars(symbol)
        summary = self.market_data_provider.summarize_symbol(symbol)
        latest_close = data.bars[-1].close if data.bars else None
        issues = [
            CandidateQualityIssue(code=issue.code, message=issue.message, severity=issue.severity)
            for issue in data.quality_issues
        ]
        if not data.bars:
            return None, issues
        return (
            CandidateMarketSnapshot(
                symbol=symbol,
                row_count=summary.row_count,
                start_timestamp=summary.start_timestamp,
                end_timestamp=summary.end_timestamp,
                latest_close=latest_close,
                min_close=summary.min_close,
                max_close=summary.max_close,
                total_volume=summary.total_volume,
                quality_issue_count=summary.quality_issue_count,
            ),
            issues,
        )

    def _sentiment_snapshot(
        self, symbol: str
    ) -> tuple[CandidateSentimentSnapshot | None, list[CandidateQualityIssue]]:
        events, issues = self.sentiment_provider.load_events(symbol)
        if not events:
            return None, [
                CandidateQualityIssue(
                    code=issue.code, message=issue.message, severity=issue.severity
                )
                for issue in issues
            ]
        snapshot = self.sentiment_provider.create_snapshot(symbol)
        return (
            CandidateSentimentSnapshot(
                symbol=symbol,
                event_count=snapshot.event_count,
                weighted_sentiment_score=snapshot.weighted_sentiment_score,
                decayed_sentiment_score=snapshot.decayed_sentiment_score,
                sentiment_label=snapshot.sentiment_label.value,
                trade_bias_context=snapshot.trade_bias_context,
                divergence_flags=snapshot.divergence_flags,
                quality_issue_count=snapshot.quality_issue_count,
            ),
            [
                CandidateQualityIssue(
                    code=issue.code, message=issue.message, severity=issue.severity
                )
                for issue in issues
            ],
        )

    def _matched_strategies(self, symbol: str) -> list[str]:
        strategy_map = {
            "AAPL": ["relative-strength-pullback", "earnings-drift-with-confirmation"],
            "QQQ": ["breakout-with-volume-confirmation", "etf-risk-on-risk-off-rotation"],
            "SPY": ["etf-risk-on-risk-off-rotation", "relative-strength-pullback"],
        }
        available = {strategy.strategy_id for strategy in self.strategy_registry.list_strategies()}
        return [
            strategy_id for strategy_id in strategy_map.get(symbol, []) if strategy_id in available
        ]

    def _matched_discovery_ids(self, symbol: str) -> list[str]:
        discovery_map = {
            "AAPL": [
                "relative-strength-pullback",
                "earnings-drift-with-confirmation",
                "broad-fear-company-calm-pullback",
                "analyst-downgrade-ignored-by-price",
            ],
            "QQQ": [
                "breakout-with-volume-confirmation",
                "social-euphoria-without-price-confirmation",
                "good-news-weak-price-warning",
            ],
            "SPY": [
                "etf-risk-on-risk-off-rotation",
                "relative-strength-pullback",
                "broad-fear-company-calm-pullback",
            ],
        }
        available = {record.discovery_id for record in self.discovery_library.list_records()}
        return [
            discovery_id
            for discovery_id in discovery_map.get(symbol, [])
            if discovery_id in available
        ]

    def _matched_scorecards(
        self,
        strategy_ids: list[str],
        discovery_ids: list[str],
        scorecards: list[StrategyScorecard],
    ) -> list[StrategyScorecard]:
        return [
            scorecard
            for scorecard in scorecards
            if scorecard.strategy_id in strategy_ids or scorecard.discovery_id in discovery_ids
        ]

    def _support_reasons(
        self,
        symbol: str,
        strategy_ids: list[str],
        discovery_ids: list[str],
        scorecards: list[StrategyScorecard],
    ) -> list[CandidateReason]:
        reasons = [
            CandidateReason(
                source=CandidateSource.MARKET_DATA_FIXTURE,
                summary=(
                    f"{symbol} has local built-in market sample rows for repeatable inspection."
                ),
                related_id=symbol,
                weight=0.6,
            ),
            CandidateReason(
                source=CandidateSource.SENTIMENT_FIXTURE,
                summary=f"{symbol} has local market mood sample events for descriptive context.",
                related_id=symbol,
                weight=0.5,
            ),
        ]
        reasons.extend(
            CandidateReason(
                source=CandidateSource.STRATEGY_MATCH,
                summary=f"Matches sample strategy idea {strategy_id}.",
                related_id=strategy_id,
                weight=0.7,
            )
            for strategy_id in strategy_ids
        )
        reasons.extend(
            CandidateReason(
                source=CandidateSource.DISCOVERY_IDEA_MATCH,
                summary=f"Matches discovery idea {discovery_id}.",
                related_id=discovery_id,
                weight=0.7,
            )
            for discovery_id in discovery_ids
        )
        best_scorecards = sorted(scorecards, key=lambda card: card.overall_score, reverse=True)[:2]
        reasons.extend(
            CandidateReason(
                source=CandidateSource.RANKING_MATCH,
                summary=(
                    f"Related research scorecard {scorecard.title} scored "
                    f"{scorecard.overall_score:.1f}/100."
                ),
                related_id=scorecard.scorecard_id,
                weight=0.8,
            )
            for scorecard in best_scorecards
        )
        return reasons

    def _risk_flags(
        self,
        market_snapshot: CandidateMarketSnapshot | None,
        sentiment_snapshot: CandidateSentimentSnapshot | None,
        scorecards: Iterable[StrategyScorecard],
    ) -> list[CandidateRiskFlag]:
        flags = [
            CandidateRiskFlag(
                flag_type=CandidateRiskFlagType.SYNTHETIC_DATA_ONLY,
                message="Uses built-in synthetic sample data only.",
            ),
            CandidateRiskFlag(
                flag_type=CandidateRiskFlagType.NO_BASELINE_PROOF,
                message="No full real-data baseline proof exists yet.",
            ),
            CandidateRiskFlag(
                flag_type=CandidateRiskFlagType.REAL_MONEY_NOT_ALLOWED,
                message="Real-money use is not allowed.",
            ),
        ]
        scorecard_list = list(scorecards)
        if any(card.conclusion == RankingConclusion.UNSUPPORTED for card in scorecard_list):
            flags.append(
                CandidateRiskFlag(
                    flag_type=CandidateRiskFlagType.UNSUPPORTED_STRATEGY_LOGIC,
                    message=(
                        "At least one related idea is not testable by the simple local engine yet."
                    ),
                )
            )
        if any(
            "too few completed examples" in " ".join(card.evidence_gaps).lower()
            for card in scorecard_list
        ):
            flags.append(
                CandidateRiskFlag(
                    flag_type=CandidateRiskFlagType.LOW_TRADE_SAMPLE,
                    message="Related sample evidence may have too few completed examples.",
                )
            )
        if market_snapshot is None or market_snapshot.row_count < 10:
            flags.append(
                CandidateRiskFlag(
                    flag_type=CandidateRiskFlagType.INSUFFICIENT_HISTORY,
                    message="Market sample history is too small for confidence.",
                )
            )
        if market_snapshot is not None and market_snapshot.quality_issue_count > 0:
            flags.append(
                CandidateRiskFlag(
                    flag_type=CandidateRiskFlagType.POOR_MARKET_DATA_QUALITY,
                    message="Market sample data has quality issues.",
                )
            )
        if sentiment_snapshot is None or sentiment_snapshot.event_count < 2:
            flags.append(
                CandidateRiskFlag(
                    flag_type=CandidateRiskFlagType.WEAK_SENTIMENT_CONTEXT,
                    message="Market mood context is thin.",
                )
            )
        if sentiment_snapshot is not None and sentiment_snapshot.divergence_flags:
            meaningful_flags = [
                flag for flag in sentiment_snapshot.divergence_flags if flag != "insufficient_data"
            ]
            if meaningful_flags:
                flags.append(
                    CandidateRiskFlag(
                        flag_type=CandidateRiskFlagType.CONFLICTING_SENTIMENT_CONTEXT,
                        message="Market mood sample contains mixed-signal warnings.",
                    )
                )
        return flags


def _summary(symbol: str, status: CandidateStatus) -> str:
    status_text = status.value.replace("_", " ")
    return (
        f"{symbol} is surfaced as {status_text} from local sample evidence only. "
        "It belongs on a research screen, not a real-money decision list."
    )


def _missing_evidence() -> list[str]:
    return [
        "Real historical market data from approved providers.",
        "A larger point-in-time sample across market regimes.",
        "A true baseline comparison for the exact symbol and idea.",
        "Robustness and walk-forward testing.",
        "Risk approval for any later phase.",
    ]


def _change_our_mind() -> list[str]:
    return [
        "Data quality problems appear in the underlying sample.",
        "The related strategy fails a simple baseline comparison.",
        "Worst-drop behavior exceeds the risk tolerance.",
        "Evidence remains thin after broader historical testing.",
        "Risk rules veto further promotion.",
    ]
