"""In-memory strategy discovery library."""

from datetime import UTC, datetime

from edgelab.discovery.regime import make_regime_fit
from edgelab.discovery.schema import (
    BaselineRequirement,
    DiscoveryLane,
    EdgeBehaviorType,
    EdgeHypothesisStatus,
    StrategyDiscoveryRecord,
    StrategyProvenance,
)


class StrategyDiscoveryLibrary:
    """Simple in-memory registry for discovery records."""

    def __init__(self, records: list[StrategyDiscoveryRecord] | None = None) -> None:
        self._records: dict[str, StrategyDiscoveryRecord] = {}
        for record in records or []:
            self.add(record)

    def add(self, record: StrategyDiscoveryRecord) -> None:
        """Add a discovery record."""

        if record.discovery_id in self._records:
            raise ValueError(f"Duplicate discovery_id: {record.discovery_id}")
        self._records[record.discovery_id] = record

    def list_records(self) -> list[StrategyDiscoveryRecord]:
        """Return all discovery records."""

        return list(self._records.values())

    def get(self, discovery_id: str) -> StrategyDiscoveryRecord | None:
        """Return a discovery record by ID."""

        return self._records.get(discovery_id)

    def filter_by_lane(self, lane: DiscoveryLane) -> list[StrategyDiscoveryRecord]:
        """Return records in a discovery lane."""

        return [record for record in self.list_records() if record.lane == lane]

    def filter_by_provenance(self, provenance: StrategyProvenance) -> list[StrategyDiscoveryRecord]:
        """Return records by provenance."""

        return [record for record in self.list_records() if record.provenance == provenance]

    def filter_by_behavior_type(
        self, behavior_type: EdgeBehaviorType
    ) -> list[StrategyDiscoveryRecord]:
        """Return records by behavior type."""

        return [record for record in self.list_records() if record.behavior_type == behavior_type]

    def filter_by_status(self, status: EdgeHypothesisStatus) -> list[StrategyDiscoveryRecord]:
        """Return records by research status."""

        return [record for record in self.list_records() if record.status == status]

    def filter_by_min_regime_fit(self, minimum_score: int) -> list[StrategyDiscoveryRecord]:
        """Return records with a current-regime-fit score at or above a minimum."""

        return [
            record
            for record in self.list_records()
            if record.current_regime_fit.score >= minimum_score
        ]

    def lane_counts(self) -> dict[str, int]:
        """Return counts by discovery lane."""

        return {lane.value: len(self.filter_by_lane(lane)) for lane in DiscoveryLane}

    def export_all(self) -> list[dict[str, object]]:
        """Export all records as JSON-friendly dictionaries."""

        return [record.model_dump(mode="json") for record in self.list_records()]

    @classmethod
    def with_samples(cls) -> "StrategyDiscoveryLibrary":
        """Create a library loaded with sample discovery records."""

        return cls(list(SAMPLE_DISCOVERY_RECORDS))


def _baseline(
    description: str, must_beat: str, baseline_id: str | None = None
) -> BaselineRequirement:
    return BaselineRequirement(
        baseline_id=baseline_id,
        description=description,
        must_beat=must_beat,
    )


CREATED_AT = datetime(2026, 5, 28, tzinfo=UTC)


SAMPLE_DISCOVERY_RECORDS: tuple[StrategyDiscoveryRecord, ...] = (
    StrategyDiscoveryRecord(
        discovery_id="relative-strength-pullback",
        title="Relative Strength Pullback",
        lane=DiscoveryLane.KNOWN_STRATEGY_LIBRARY,
        provenance=StrategyProvenance.CANONICAL,
        behavior_type=EdgeBehaviorType.QUALITY_PULLBACK,
        plain_english_summary=(
            "Look for strong names that pause without obvious damage, then test whether strength "
            "returns after the pause."
        ),
        market_behavior="Durable leaders sometimes resume after orderly pullbacks.",
        why_it_might_work="Persistent demand can return after weak holders are shaken out.",
        why_it_might_work_now="The static sample assumes a stable broad tape and liquid symbols.",
        why_others_might_miss_it="Simple screens may treat every pullback as weakness.",
        baseline_to_beat=_baseline(
            "Plain momentum continuation",
            "Show better risk-adjusted evidence than holding the strongest recent names without "
            "waiting for a pullback.",
        ),
        evidence_needed=[
            "Historical test against a plain momentum baseline",
            "Worst-drop comparison after costs",
            "Robustness across calm and stressed regimes",
        ],
        disproof_conditions=[
            "Pullback entries do not improve results versus plain momentum",
            "Losses cluster during broad weakness",
        ],
        best_market_conditions=["stable market mood", "orderly pullbacks", "healthy liquidity"],
        worst_market_conditions=["broad stress", "gap-heavy selling", "stale data"],
        data_needed=["daily OHLCV bars", "relative strength benchmark", "liquidity checks"],
        complexity_score=3,
        novelty_score=2,
        overfitting_risk_score=4,
        current_regime_fit=make_regime_fit(
            7,
            "Static sample conditions look possible for an orderly-pullback idea.",
            ["liquid sample symbols", "daily horizon"],
            ["real regime data", "real liquidity data"],
        ),
        derived_strategy_id="relative-strength-pullback",
        status=EdgeHypothesisStatus.NEEDS_BACKTEST,
        created_at=CREATED_AT,
    ),
    StrategyDiscoveryRecord(
        discovery_id="earnings-drift-with-confirmation",
        title="Earnings Drift With Confirmation",
        lane=DiscoveryLane.KNOWN_STRATEGY_LIBRARY,
        provenance=StrategyProvenance.ADAPTIVE_CANONICAL,
        behavior_type=EdgeBehaviorType.EARNINGS_DRIFT,
        plain_english_summary=(
            "Start from the classic post-earnings drift idea, but require later confirmation "
            "instead of trusting the first reaction."
        ),
        market_behavior="Post-event repricing can continue after strong earnings reactions.",
        why_it_might_work="Large investors may adjust positions over several sessions.",
        why_it_might_work_now="The idea may fit when event reactions are not immediately reversed.",
        why_others_might_miss_it=(
            "Headline-only approaches may ignore whether price confirms the event."
        ),
        baseline_to_beat=_baseline(
            "Plain post-earnings drift",
            "Beat the same idea without delayed confirmation.",
        ),
        evidence_needed=[
            "Point-in-time event timestamps",
            "Comparison against plain post-event drift",
            "Sensitivity to gap and cost assumptions",
        ],
        disproof_conditions=[
            "Delayed confirmation removes the edge",
            "Event gaps dominate later returns",
        ],
        best_market_conditions=["orderly event reactions", "stable broad market"],
        worst_market_conditions=["event shock reversals", "market-wide stress"],
        data_needed=["earnings timestamps", "daily bars", "event reaction labels"],
        complexity_score=5,
        novelty_score=4,
        overfitting_risk_score=5,
        current_regime_fit=make_regime_fit(
            5,
            "Static sample lacks real earnings events, so the fit is only weakly knowable.",
            ["daily horizon"],
            ["real event data", "surprise data"],
        ),
        parent_discovery_id=None,
        derived_strategy_id="earnings-drift-with-confirmation",
        status=EdgeHypothesisStatus.BASELINE_REQUIRED,
        adaptation_notes="Adds delayed price/volume confirmation to the canonical drift idea.",
        created_at=CREATED_AT,
    ),
    StrategyDiscoveryRecord(
        discovery_id="etf-risk-on-risk-off-rotation",
        title="ETF Risk-On/Risk-Off Rotation",
        lane=DiscoveryLane.KNOWN_STRATEGY_LIBRARY,
        provenance=StrategyProvenance.CANONICAL,
        behavior_type=EdgeBehaviorType.SECTOR_ROTATION,
        plain_english_summary=(
            "Compare broad ETF groups and study whether the portfolio should prefer stronger, "
            "defensive, or cash-like exposure in different environments."
        ),
        market_behavior="Large capital flows can rotate between risk-seeking and defensive assets.",
        why_it_might_work="Broad allocation shifts can persist longer than one session.",
        why_it_might_work_now=(
            "It may fit when risk appetite is clearly changing across ETF groups."
        ),
        why_others_might_miss_it="Single-name research can miss broad allocation pressure.",
        baseline_to_beat=_baseline(
            "Static broad ETF exposure",
            "Improve worst-drop behavior versus always holding the broad benchmark.",
        ),
        evidence_needed=[
            "Benchmark comparison versus SPY",
            "Regime split across stress and calm periods",
        ],
        disproof_conditions=[
            "Rotation lags cause late switches",
            "Defensive moves reduce return without reducing risk",
        ],
        best_market_conditions=["clear regime transitions", "liquid ETF leadership"],
        worst_market_conditions=["sideways noisy markets", "rapid whipsaws"],
        data_needed=["daily ETF bars", "regime labels", "cost assumptions"],
        complexity_score=4,
        novelty_score=2,
        overfitting_risk_score=4,
        current_regime_fit=make_regime_fit(
            6,
            "Static sample can show broad ETF behavior but cannot prove current rotation pressure.",
            ["ETF symbols available"],
            ["live regime context"],
        ),
        derived_strategy_id="etf-risk-on-risk-off-rotation",
        status=EdgeHypothesisStatus.NEEDS_BACKTEST,
        created_at=CREATED_AT,
    ),
    StrategyDiscoveryRecord(
        discovery_id="breakout-with-volume-confirmation",
        title="Breakout With Volume Confirmation",
        lane=DiscoveryLane.KNOWN_STRATEGY_LIBRARY,
        provenance=StrategyProvenance.ADAPTIVE_CANONICAL,
        behavior_type=EdgeBehaviorType.VOLATILITY_EXPANSION,
        plain_english_summary=(
            "Study whether range breaks are more useful when the move has enough participation "
            "behind it."
        ),
        market_behavior="Quiet ranges can expand when new demand appears.",
        why_it_might_work="Volume may help separate real participation from a thin move.",
        why_it_might_work_now="It may fit if range compression and volume expansion are visible.",
        why_others_might_miss_it="Price-only breakouts can ignore participation quality.",
        baseline_to_beat=_baseline(
            "Plain breakout",
            "Beat a price-only breakout rule after costs and false-breakout checks.",
        ),
        evidence_needed=[
            "Comparison to price-only breakout",
            "False-breakout rate",
            "Cost sensitivity",
        ],
        disproof_conditions=[
            "Volume confirmation does not reduce false breaks",
            "Confirmed entries arrive too late",
        ],
        best_market_conditions=["range compression", "volume expansion", "stable broad market"],
        worst_market_conditions=["thin liquidity", "news-driven gaps"],
        data_needed=["daily bars", "volume baselines", "range definitions"],
        complexity_score=4,
        novelty_score=3,
        overfitting_risk_score=5,
        current_regime_fit=make_regime_fit(
            6,
            "Static bars can support a basic breakout shape, but real confirmation is unproven.",
            ["daily bars", "volume fields"],
            ["robust range definitions"],
        ),
        derived_strategy_id="breakout-with-volume-confirmation",
        status=EdgeHypothesisStatus.BASELINE_REQUIRED,
        adaptation_notes="Adds participation confirmation to a canonical breakout family.",
        created_at=CREATED_AT,
    ),
    StrategyDiscoveryRecord(
        discovery_id="broad-fear-company-calm-pullback",
        title="Broad Fear / Company Calm Pullback",
        lane=DiscoveryLane.EDGE_INNOVATION_LAB,
        provenance=StrategyProvenance.ADAPTIVE_CANONICAL,
        behavior_type=EdgeBehaviorType.SENTIMENT_DISAGREEMENT,
        plain_english_summary=(
            "Look for broad market fear while company-specific mood remains calm, then test "
            "whether quality pullbacks recover better than ordinary pullbacks."
        ),
        market_behavior=(
            "Market-wide fear can pressure good names even when company context is stable."
        ),
        why_it_might_work=(
            "Forced selling may create temporary dislocations in otherwise healthy names."
        ),
        why_it_might_work_now=(
            "The static mood fixtures include broad fear and company-specific context."
        ),
        why_others_might_miss_it=(
            "Single-source mood checks may confuse broad fear with company damage."
        ),
        baseline_to_beat=_baseline(
            "Ordinary relative strength pullback",
            "Beat the same pullback idea without broad/company mood separation.",
            "relative-strength-pullback",
        ),
        evidence_needed=[
            "Point-in-time broad and company mood separation",
            "Comparison against ordinary pullback",
            "Worst-drop improvement in stressed periods",
        ],
        disproof_conditions=[
            "Broad fear pullbacks keep falling",
            "Company calm labels do not improve outcomes",
        ],
        best_market_conditions=["broad fear", "company mood stability", "healthy liquidity"],
        worst_market_conditions=["company-specific bad news", "liquidity stress"],
        data_needed=["daily bars", "broad mood events", "company mood events"],
        complexity_score=7,
        novelty_score=6,
        overfitting_risk_score=7,
        current_regime_fit=make_regime_fit(
            5,
            "Static fixtures can illustrate mood separation but cannot prove current fit.",
            ["synthetic broad mood"],
            ["real company news", "real broad risk state"],
        ),
        parent_discovery_id="relative-strength-pullback",
        status=EdgeHypothesisStatus.BASELINE_REQUIRED,
        adaptation_notes=(
            "Adds broad-versus-company mood separation to relative strength pullbacks."
        ),
        created_at=CREATED_AT,
    ),
    StrategyDiscoveryRecord(
        discovery_id="good-news-weak-price-warning",
        title="Good News / Weak Price Warning",
        lane=DiscoveryLane.EDGE_INNOVATION_LAB,
        provenance=StrategyProvenance.NOVEL_HYPOTHESIS,
        behavior_type=EdgeBehaviorType.SENTIMENT_DISAGREEMENT,
        plain_english_summary=(
            "Study cases where news looks positive but price does not confirm, treating that "
            "mismatch as a reason to demand more evidence."
        ),
        market_behavior=(
            "Positive headlines can fail when informed sellers disagree with the story."
        ),
        why_it_might_work="Price weakness after good news may reveal hidden concern.",
        why_it_might_work_now="Synthetic fixtures include disagreement-style mood events.",
        why_others_might_miss_it=(
            "Headline scoring may overvalue good news without checking price response."
        ),
        baseline_to_beat=_baseline(
            "Positive news confirmation",
            "Improve caution signals versus simply trusting positive news labels.",
        ),
        evidence_needed=[
            "Point-in-time positive news labels",
            "Same-window price response",
            "Comparison to headline-only confirmation",
        ],
        disproof_conditions=[
            "Weak initial price response has no predictive value",
            "The warning filters out too many later winners",
        ],
        best_market_conditions=["clear positive news", "weak price response", "normal liquidity"],
        worst_market_conditions=["stale news", "market-wide shock", "thin symbols"],
        data_needed=["sentiment events", "daily bars", "event windows"],
        complexity_score=6,
        novelty_score=7,
        overfitting_risk_score=7,
        current_regime_fit=make_regime_fit(
            4,
            "Current static fixtures are enough to describe the mismatch, not validate it.",
            ["synthetic disagreement events"],
            ["real price/news joins"],
        ),
        status=EdgeHypothesisStatus.IDEA,
        created_at=CREATED_AT,
    ),
    StrategyDiscoveryRecord(
        discovery_id="social-euphoria-without-price-confirmation",
        title="Social Euphoria Without Price Confirmation",
        lane=DiscoveryLane.EDGE_INNOVATION_LAB,
        provenance=StrategyProvenance.NOVEL_HYPOTHESIS,
        behavior_type=EdgeBehaviorType.CROWDING_RISK,
        plain_english_summary=(
            "Study whether crowd excitement without price confirmation marks fragile interest "
            "rather than durable demand."
        ),
        market_behavior="Crowd attention can spike without real follow-through.",
        why_it_might_work=(
            "Excitement without confirmation may reflect crowded attention, not demand."
        ),
        why_it_might_work_now="Synthetic mood fixtures include social euphoria style warnings.",
        why_others_might_miss_it=(
            "Volume or social counts can look impressive without useful follow-through."
        ),
        baseline_to_beat=_baseline(
            "Simple momentum avoidance",
            "Reduce false enthusiasm better than avoiding all high-attention names.",
        ),
        evidence_needed=[
            "Social mood timestamps",
            "Price confirmation window",
            "Baseline comparison to simple momentum avoidance",
        ],
        disproof_conditions=[
            "Social euphoria still predicts durable continuation",
            "The filter removes too many useful ideas",
        ],
        best_market_conditions=["crowded attention", "weak confirmation", "normal spread"],
        worst_market_conditions=["true breakout demand", "missing social context"],
        data_needed=["social mood events", "daily bars", "volume baselines"],
        complexity_score=7,
        novelty_score=8,
        overfitting_risk_score=8,
        current_regime_fit=make_regime_fit(
            4,
            "Static fixtures can show the idea but cannot validate social crowding.",
            ["synthetic social mood"],
            ["real social data", "real confirmation windows"],
        ),
        status=EdgeHypothesisStatus.IDEA,
        created_at=CREATED_AT,
    ),
    StrategyDiscoveryRecord(
        discovery_id="analyst-downgrade-ignored-by-price",
        title="Analyst Downgrade Ignored By Price",
        lane=DiscoveryLane.EDGE_INNOVATION_LAB,
        provenance=StrategyProvenance.ADAPTIVE_CANONICAL,
        behavior_type=EdgeBehaviorType.SENTIMENT_DISAGREEMENT,
        plain_english_summary=(
            "Study whether a negative analyst event matters less when price refuses to weaken."
        ),
        market_behavior="Price can sometimes ignore negative external opinions.",
        why_it_might_work=(
            "Resilient price behavior may show that the downgrade was already priced in."
        ),
        why_it_might_work_now="Synthetic sentiment fixtures include analyst downgrade events.",
        why_others_might_miss_it="News-only systems may overreact to the downgrade label.",
        baseline_to_beat=_baseline(
            "Analyst downgrade avoidance",
            "Improve results versus avoiding every downgraded name.",
        ),
        evidence_needed=[
            "Timestamped downgrade events",
            "Price resilience definition",
            "Comparison to downgrade avoidance",
        ],
        disproof_conditions=[
            "Ignored downgrades still lead to weak outcomes",
            "Price resilience definition is fragile",
        ],
        best_market_conditions=["stable broad market", "liquid symbols", "contained reaction"],
        worst_market_conditions=["fresh fundamental damage", "broad market stress"],
        data_needed=["analyst events", "daily bars", "broad regime context"],
        complexity_score=6,
        novelty_score=6,
        overfitting_risk_score=7,
        current_regime_fit=make_regime_fit(
            5,
            "Static analyst-style events exist, but real event validation is missing.",
            ["synthetic analyst event"],
            ["real analyst data", "real event windows"],
        ),
        parent_discovery_id="good-news-weak-price-warning",
        status=EdgeHypothesisStatus.BASELINE_REQUIRED,
        adaptation_notes=(
            "Uses the same disagreement lens but flips the setup to negative news "
            "with resilient price."
        ),
        created_at=CREATED_AT,
    ),
    StrategyDiscoveryRecord(
        discovery_id="guidance-cut-mean-reversion-veto",
        title="Guidance Cut Mean-Reversion Veto",
        lane=DiscoveryLane.EDGE_INNOVATION_LAB,
        provenance=StrategyProvenance.ADAPTIVE_CANONICAL,
        behavior_type=EdgeBehaviorType.MEAN_REVERSION,
        plain_english_summary=(
            "Study whether oversold mean-reversion ideas should be blocked when guidance cuts "
            "suggest the weakness may be deserved."
        ),
        market_behavior="Some oversold moves bounce, but some reflect real business deterioration.",
        why_it_might_work="A guidance-cut veto may avoid fragile rebounds with poor context.",
        why_it_might_work_now=(
            "Synthetic event taxonomy includes guidance cuts as a caution category."
        ),
        why_others_might_miss_it="Pure price mean reversion can ignore why the drop happened.",
        baseline_to_beat=_baseline(
            "Plain oversold mean reversion",
            "Improve risk-adjusted evidence versus price-only oversold entries.",
        ),
        evidence_needed=[
            "Timestamped guidance-cut events",
            "Price-only mean reversion baseline",
            "Out-of-sample event validation",
        ],
        disproof_conditions=[
            "Guidance-cut veto does not reduce bad rebounds",
            "The veto removes too many useful reversals",
        ],
        best_market_conditions=["clear event taxonomy", "normal liquidity", "stable broad market"],
        worst_market_conditions=["late or missing event labels", "panic selloffs"],
        data_needed=["guidance events", "daily bars", "baseline reversion rules"],
        complexity_score=6,
        novelty_score=5,
        overfitting_risk_score=6,
        current_regime_fit=make_regime_fit(
            3,
            "Static fixtures do not yet include enough guidance-cut examples.",
            [],
            ["real guidance-cut events", "larger event history"],
        ),
        parent_discovery_id="relative-strength-pullback",
        status=EdgeHypothesisStatus.NEEDS_BACKTEST,
        adaptation_notes="Adds an event-based veto to simple price mean-reversion research.",
        created_at=CREATED_AT,
    ),
)
