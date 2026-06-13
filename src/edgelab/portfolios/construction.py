"""Local research-only model portfolio construction engine."""

from __future__ import annotations

from edgelab.candidates.schema import (
    CandidateEvidenceStrength,
    CandidateStatus,
    EquityCandidate,
)
from edgelab.candidates.screener import CandidateEquityScreener
from edgelab.portfolios.constraints import check_portfolio_constraints
from edgelab.portfolios.monitoring import build_monitoring_notes
from edgelab.portfolios.schema import (
    CashAllocation,
    ModelPortfolio,
    PortfolioConstructionRequest,
    PortfolioConstructionResult,
    PortfolioEvidenceStrength,
    PortfolioHolding,
    PortfolioHoldingRole,
    PortfolioMode,
    PortfolioQualityIssue,
    PortfolioRiskFlag,
    PortfolioRiskFlagType,
    PortfolioRiskLimits,
    PortfolioStatus,
    PortfolioStyle,
)


class ModelPortfolioEngine:
    """Construct local hypothetical research portfolios from candidates."""

    def __init__(self, candidate_screener: CandidateEquityScreener | None = None) -> None:
        self.candidate_screener = candidate_screener or CandidateEquityScreener()

    def construct(
        self,
        request: PortfolioConstructionRequest | None = None,
    ) -> PortfolioConstructionResult:
        """Construct local research-only model portfolios."""

        construction_request = request or PortfolioConstructionRequest()
        limits = PortfolioRiskLimits(
            initial_capital=construction_request.initial_capital,
            max_positions=construction_request.max_positions or PortfolioRiskLimits().max_positions,
        )
        candidates = self._usable_candidates(construction_request)
        portfolios = self._build_portfolios(candidates, limits, construction_request)
        if construction_request.style is not None:
            portfolios = [
                portfolio
                for portfolio in portfolios
                if portfolio.style == construction_request.style
            ]
        return PortfolioConstructionResult(
            initial_capital=construction_request.initial_capital,
            portfolio_count=len(portfolios),
            portfolios=portfolios,
            rejected_candidate_count=self._rejected_candidate_count(construction_request),
            quality_issues=[
                PortfolioQualityIssue(
                    code="fixture_only_model_portfolios",
                    message="Model portfolios use local synthetic fixture candidates only.",
                )
            ],
            plain_english_summary=(
                "EdgeLab assembled hypothetical model portfolios from local candidate evidence. "
                "They are research-only and not approved for real-money use."
            ),
        )

    def get_portfolio(self, portfolio_id: str) -> ModelPortfolio | None:
        """Return one generated model portfolio."""

        for portfolio in self.construct().portfolios:
            if portfolio.portfolio_id == portfolio_id:
                return portfolio
        return None

    def list_styles(self) -> list[str]:
        """Return available model portfolio styles."""

        return [style.value for style in PortfolioStyle]

    def monitoring_notes_for(self, portfolio_id: str) -> list[dict[str, object]] | None:
        """Return monitoring notes for one model portfolio."""

        portfolio = self.get_portfolio(portfolio_id)
        if portfolio is None:
            return None
        return [note.model_dump(mode="json") for note in portfolio.monitoring_notes]

    def _usable_candidates(self, request: PortfolioConstructionRequest) -> list[EquityCandidate]:
        result = self.candidate_screener.screen()
        candidates = [
            candidate
            for candidate in result.candidates
            if request.include_watchlist_only or candidate.status != CandidateStatus.WATCHLIST_ONLY
        ]
        if request.min_candidate_score is not None:
            candidates = [
                candidate
                for candidate in candidates
                if candidate.candidate_score >= request.min_candidate_score
            ]
        return sorted(candidates, key=lambda candidate: candidate.candidate_score, reverse=True)

    def _rejected_candidate_count(self, request: PortfolioConstructionRequest) -> int:
        all_candidates = self.candidate_screener.screen().candidates
        usable_ids = {candidate.candidate_id for candidate in self._usable_candidates(request)}
        return len(
            [candidate for candidate in all_candidates if candidate.candidate_id not in usable_ids]
        )

    def _build_portfolios(
        self,
        candidates: list[EquityCandidate],
        limits: PortfolioRiskLimits,
        request: PortfolioConstructionRequest,
    ) -> list[ModelPortfolio]:
        portfolios = [
            self._build_core(candidates, limits),
            self._build_defensive(candidates, limits),
            self._build_opportunistic(candidates, limits),
        ]
        if request.include_benchmark_portfolio:
            portfolios.append(self._build_benchmark(candidates, limits))
        return portfolios

    def _build_core(
        self, candidates: list[EquityCandidate], limits: PortfolioRiskLimits
    ) -> ModelPortfolio:
        weights = {"SPY": 25.0, "QQQ": 22.0, "AAPL": 8.0}
        return self._assemble_portfolio(
            portfolio_id="core-research-portfolio",
            name="EdgeLab Core Research Portfolio",
            style=PortfolioStyle.CORE_RESEARCH,
            status=PortfolioStatus.RESEARCH_MODEL,
            evidence_strength=PortfolioEvidenceStrength.WEAK,
            cash_weight=45.0,
            weights=weights,
            candidates=candidates,
            limits=limits,
            purpose=(
                "A balanced default model that keeps meaningful cash while spreading research "
                "attention across the available fixture candidates."
            ),
            summary=(
                "A cautious practice test built from sample candidates with cash as the largest "
                "part."
            ),
        )

    def _build_defensive(
        self, candidates: list[EquityCandidate], limits: PortfolioRiskLimits
    ) -> ModelPortfolio:
        weights = {"SPY": 30.0, "QQQ": 17.0, "AAPL": 8.0}
        return self._assemble_portfolio(
            portfolio_id="defensive-research-portfolio",
            name="EdgeLab Defensive Research Portfolio",
            style=PortfolioStyle.DEFENSIVE_RESEARCH,
            status=PortfolioStatus.RESEARCH_MODEL,
            evidence_strength=PortfolioEvidenceStrength.WEAK,
            cash_weight=45.0,
            weights=weights,
            candidates=candidates,
            limits=limits,
            purpose=(
                "A higher-cash model that treats broad-market fixture symbols as references and "
                "keeps any one company idea small."
            ),
            summary=(
                "A cautious practice test that favors cash and broad sample references over one "
                "company idea."
            ),
        )

    def _build_opportunistic(
        self, candidates: list[EquityCandidate], limits: PortfolioRiskLimits
    ) -> ModelPortfolio:
        weights = {"SPY": 34.0, "QQQ": 33.0, "AAPL": 8.0}
        return self._assemble_portfolio(
            portfolio_id="opportunistic-research-portfolio",
            name="EdgeLab Opportunistic Research Portfolio",
            style=PortfolioStyle.OPPORTUNISTIC_RESEARCH,
            status=PortfolioStatus.RESEARCH_MODEL,
            evidence_strength=PortfolioEvidenceStrength.WEAK,
            cash_weight=25.0,
            weights=weights,
            candidates=candidates,
            limits=limits,
            purpose=(
                "A practice test that uses more of the sample amount while still staying inside "
                "safety rules."
            ),
            summary=(
                "A less cautious practice test for studying whether stronger sample ideas still "
                "stay inside safety rules."
            ),
        )

    def _build_benchmark(
        self, candidates: list[EquityCandidate], limits: PortfolioRiskLimits
    ) -> ModelPortfolio:
        weights = {"SPY": 35.0, "QQQ": 35.0}
        return self._assemble_portfolio(
            portfolio_id="benchmark-comparison-portfolio",
            name="EdgeLab Benchmark Comparison Portfolio",
            style=PortfolioStyle.BENCHMARK_COMPARISON,
            status=PortfolioStatus.REFERENCE_ONLY,
            evidence_strength=PortfolioEvidenceStrength.INSUFFICIENT,
            cash_weight=30.0,
            weights=weights,
            candidates=candidates,
            limits=limits,
            purpose=(
                "A reference-only practice test for comparing other practice tests against broad "
                "sample symbols and cash."
            ),
            summary=(
                "A comparison-basket practice test. It exists to provide context, not a favorite "
                "choice."
            ),
        )

    def _assemble_portfolio(
        self,
        *,
        portfolio_id: str,
        name: str,
        style: PortfolioStyle,
        status: PortfolioStatus,
        evidence_strength: PortfolioEvidenceStrength,
        cash_weight: float,
        weights: dict[str, float],
        candidates: list[EquityCandidate],
        limits: PortfolioRiskLimits,
        purpose: str,
        summary: str,
    ) -> ModelPortfolio:
        candidate_by_symbol = {candidate.symbol: candidate for candidate in candidates}
        holdings = [
            self._holding_from_candidate(symbol, weight, candidate_by_symbol.get(symbol), limits)
            for symbol, weight in weights.items()
            if candidate_by_symbol.get(symbol) is not None or symbol in {"SPY", "QQQ"}
        ]
        cash = CashAllocation(
            target_weight_pct=cash_weight,
            target_value=_target_value(cash_weight, limits.initial_capital),
            plain_english_reason=(
                "Cash is intentional here. It keeps the model conservative while evidence is thin."
            ),
        )
        included_candidates = [
            candidate
            for candidate in candidate_by_symbol.values()
            if candidate.symbol in {holding.symbol for holding in holdings}
        ]
        constraint_issues = check_portfolio_constraints(
            holdings,
            cash.target_weight_pct,
            limits,
            included_candidates=included_candidates,
        )
        quality_issues = [
            PortfolioQualityIssue(
                code="synthetic_fixture_data",
                message="This model portfolio uses synthetic sample data only.",
            )
        ]
        portfolio = ModelPortfolio(
            portfolio_id=portfolio_id,
            name=name,
            style=style,
            mode=PortfolioMode.RESEARCH_ONLY,
            status=status,
            evidence_strength=evidence_strength,
            initial_capital=limits.initial_capital,
            target_equity_exposure_pct=sum(holding.target_weight_pct for holding in holdings),
            target_cash=cash,
            holdings=holdings,
            risk_limits=limits,
            constraint_issues=constraint_issues,
            quality_issues=quality_issues,
            plain_english_summary=summary,
            why_this_portfolio_exists=purpose,
            what_supports_it=_portfolio_supports(holdings),
            what_is_missing=_missing_evidence(),
            what_would_change_our_mind=_change_our_mind(),
        )
        portfolio.monitoring_notes = build_monitoring_notes(portfolio.portfolio_id, holdings)
        return portfolio

    def _holding_from_candidate(
        self,
        symbol: str,
        weight: float,
        candidate: EquityCandidate | None,
        limits: PortfolioRiskLimits,
    ) -> PortfolioHolding:
        if candidate is None:
            return _reference_holding(symbol, weight, limits)
        return PortfolioHolding(
            holding_id=f"{symbol.lower()}-model-holding",
            symbol=symbol,
            display_name=f"{symbol} Model Holding",
            role=_role_for_symbol(symbol, candidate),
            candidate_id=candidate.candidate_id,
            target_weight_pct=weight,
            target_value=_target_value(weight, limits.initial_capital),
            evidence_strength=_portfolio_evidence(candidate.evidence_strength),
            candidate_score=candidate.candidate_score,
            linked_strategy_ids=candidate.matched_strategy_ids,
            linked_discovery_ids=candidate.matched_discovery_ids,
            linked_scorecard_ids=candidate.matched_scorecard_ids,
            plain_english_reason=(
                f"{symbol} appears because it is available in the local candidate screen and "
                "has linked strategy or discovery context."
            ),
            why_included=[
                candidate.plain_english_summary,
                "It helps exercise portfolio construction and monitoring logic.",
            ],
            what_to_monitor=[
                "Candidate score and how much support EdgeLab has.",
                "Market mood context and mixed-signal warnings.",
                "Whether the pretend portfolio share stays inside safety rules.",
            ],
            what_would_make_us_reconsider=[
                "Candidate evidence weakens.",
                "Data quality becomes unreliable.",
                "The holding no longer matches the reason it was included.",
            ],
            risk_flags=[
                PortfolioRiskFlag(
                    flag_type=PortfolioRiskFlagType.SYNTHETIC_DATA_ONLY,
                    message="Uses synthetic fixture candidate evidence only.",
                ),
                PortfolioRiskFlag(
                    flag_type=PortfolioRiskFlagType.REAL_MONEY_NOT_ALLOWED,
                    message="Real-money use is not allowed.",
                ),
                *(_candidate_risk_flags(candidate)),
            ],
        )


def _reference_holding(symbol: str, weight: float, limits: PortfolioRiskLimits) -> PortfolioHolding:
    role = (
        PortfolioHoldingRole.BROAD_MARKET_REFERENCE
        if symbol == "SPY"
        else PortfolioHoldingRole.GROWTH_REFERENCE
    )
    return PortfolioHolding(
        holding_id=f"{symbol.lower()}-reference-holding",
        symbol=symbol,
        display_name=f"{symbol} Reference Holding",
        role=role,
        target_weight_pct=weight,
        target_value=_target_value(weight, limits.initial_capital),
        evidence_strength=PortfolioEvidenceStrength.INSUFFICIENT,
        plain_english_reason=(
            f"{symbol} is included as a fixture-backed reference symbol for comparison."
        ),
        why_included=["It provides a broad reference point for portfolio construction tests."],
        what_to_monitor=["Whether fixture data remains available and internally consistent."],
        what_would_make_us_reconsider=["The fixture symbol is removed or data quality fails."],
        risk_flags=[
            PortfolioRiskFlag(
                flag_type=PortfolioRiskFlagType.FIXTURE_ONLY_PRICING,
                message="Reference pricing is fixture-only.",
            ),
            PortfolioRiskFlag(
                flag_type=PortfolioRiskFlagType.REAL_MONEY_NOT_ALLOWED,
                message="Real-money use is not allowed.",
            ),
        ],
    )


def _role_for_symbol(
    symbol: str,
    candidate: EquityCandidate,
) -> PortfolioHoldingRole:
    if symbol == "SPY":
        return PortfolioHoldingRole.BROAD_MARKET_REFERENCE
    if symbol == "QQQ":
        return PortfolioHoldingRole.GROWTH_REFERENCE
    if candidate.status == CandidateStatus.WATCHLIST_ONLY:
        return PortfolioHoldingRole.WATCHLIST_ONLY
    if candidate.candidate_score >= 50:
        return PortfolioHoldingRole.CORE_CANDIDATE
    return PortfolioHoldingRole.SUPPORTING_CANDIDATE


def _portfolio_evidence(
    candidate_strength: CandidateEvidenceStrength,
) -> PortfolioEvidenceStrength:
    return PortfolioEvidenceStrength(candidate_strength.value)


def _candidate_risk_flags(candidate: EquityCandidate) -> list[PortfolioRiskFlag]:
    flags: list[PortfolioRiskFlag] = []
    if candidate.evidence_strength in {
        CandidateEvidenceStrength.INSUFFICIENT,
        CandidateEvidenceStrength.WEAK,
    }:
        flags.append(
            PortfolioRiskFlag(
                flag_type=PortfolioRiskFlagType.WEAK_CANDIDATE_EVIDENCE,
                message="Candidate evidence is still weak.",
            )
        )
    if candidate.status in {
        CandidateStatus.BLOCKED_BY_RISK,
        CandidateStatus.BLOCKED_BY_DATA_QUALITY,
        CandidateStatus.REJECTED_FOR_NOW,
    }:
        flags.append(
            PortfolioRiskFlag(
                flag_type=PortfolioRiskFlagType.BLOCKED_CANDIDATE,
                message="Candidate is blocked or rejected by the candidate screen.",
                severity="error",
            )
        )
    if any(flag.flag_type.value == "unsupported_strategy_logic" for flag in candidate.risk_flags):
        flags.append(
            PortfolioRiskFlag(
                flag_type=PortfolioRiskFlagType.UNSUPPORTED_STRATEGY_LOGIC,
                message="One linked strategy idea is not fully supported by the local engine.",
            )
        )
    if candidate.market_snapshot is None or candidate.market_snapshot.row_count < 10:
        flags.append(
            PortfolioRiskFlag(
                flag_type=PortfolioRiskFlagType.INSUFFICIENT_HISTORY,
                message="Fixture market history is too small for trust.",
            )
        )
    return flags


def _portfolio_supports(holdings: list[PortfolioHolding]) -> list[str]:
    return [
        "Built from Phase 7A local research candidates.",
        "Includes cash instead of pretending every dollar must be used.",
        f"Includes {len(holdings)} practice ideas for portfolio construction tests.",
    ]


def _missing_evidence() -> list[str]:
    return [
        "Real historical provider data.",
        "Paper portfolio simulation.",
        "Walk-forward portfolio behavior.",
        "Human review of safety rules.",
        "Any future approval gate for paper or real-money phases.",
    ]


def _change_our_mind() -> list[str]:
    return [
        "A candidate becomes blocked by risk or data quality.",
        "A practice holding grows beyond its maximum safe size.",
        "Cash falls below the minimum safely unused amount.",
        "The portfolio no longer explains why each holding appears.",
        "Fixture evidence fails validation.",
    ]


def _target_value(weight_pct: float, initial_capital: float) -> float:
    return round(initial_capital * (weight_pct / 100.0), 2)
