"""In-memory sample strategy specifications for Phase 1."""

from edgelab.strategies.schema import (
    AssetClass,
    EntryRule,
    ExitRule,
    MarketRegimeFilter,
    PositionSizingRule,
    RiskRule,
    SignalType,
    StrategyDirection,
    StrategyEvidenceRequirement,
    StrategySignal,
    StrategySpec,
    StrategyStatus,
    StrategyUniverse,
    TradingHorizon,
)


def _evidence_requirements(*items: tuple[str, str, str]) -> list[StrategyEvidenceRequirement]:
    return [
        StrategyEvidenceRequirement(name=name, description=description, minimum_threshold=threshold)
        for name, description, threshold in items
    ]


SAMPLE_STRATEGIES: tuple[StrategySpec, ...] = (
    StrategySpec(
        strategy_id="relative-strength-pullback",
        name="Relative Strength Pullback",
        description="Long-only pullback candidate in stocks or ETFs with persistent strength.",
        thesis=(
            "Leaders that pull back in orderly fashion may resume trend when broad risk "
            "is stable."
        ),
        asset_class=AssetClass.US_EQUITIES_AND_ETFS,
        direction=StrategyDirection.LONG_ONLY,
        horizon=TradingHorizon.MULTI_DAY_SWING,
        universe=StrategyUniverse(
            description="Liquid US equities and ETFs with above-benchmark medium-term momentum.",
            filters=[
                "average dollar volume above research threshold",
                "price above long trend filter",
            ],
        ),
        signals=[
            StrategySignal(
                name="Relative strength",
                description="Candidate has outperformed its benchmark over the lookback window.",
                signal_type=SignalType.PRICE,
                inputs=["symbol return", "benchmark return"],
                rule="symbol relative return is positive over the research lookback",
            ),
            StrategySignal(
                name="Orderly pullback",
                description="Price has pulled back without a volatility or liquidity breakdown.",
                signal_type=SignalType.PRICE,
                inputs=["close", "average true range", "volume"],
                rule="pullback remains inside the predefined risk envelope",
            ),
        ],
        entry_rules=[
            EntryRule(
                name="Pullback recovery",
                description="Enter after price confirms recovery from the pullback.",
                rule="close recovers above the short-term trigger level after pullback",
            )
        ],
        exit_rules=[
            ExitRule(
                name="Trend failure",
                description="Exit when recovery fails or the holding period expires.",
                rule="exit on risk stop, trend failure, or maximum holding period",
            )
        ],
        position_sizing=PositionSizingRule(
            method="fixed_fractional_research",
            description="Use fixed fractional placeholder sizing for research comparisons.",
            max_position_size="to be defined by risk governance",
        ),
        risk_rules=[
            RiskRule(
                name="Drawdown guard",
                description="Reject signals when portfolio drawdown breaches the research limit.",
                veto_condition="portfolio drawdown exceeds configured tolerance",
            ),
            RiskRule(
                name="Liquidity guard",
                description="Reject stale or thinly traded candidates.",
                veto_condition="liquidity or data freshness is insufficient",
            ),
        ],
        holding_period="3 to 15 trading days",
        market_regime_filter=MarketRegimeFilter(
            description="Prefer stable or risk-on broad market regimes.",
            allowed_regimes=["risk_on", "neutral"],
            blocked_regimes=["risk_off"],
        ),
        expected_edge="Potential continuation after low-stress pullbacks in relative leaders.",
        failure_conditions=[
            "Relative strength reverses before entry.",
            "Pullbacks become gap-driven rather than orderly.",
            "Broad market regime turns risk-off.",
        ],
        evidence_required=_evidence_requirements(
            (
                "Out-of-sample behavior",
                "Verify performance outside the development window.",
                "positive risk-adjusted return after costs",
            ),
            (
                "Benchmark comparison",
                "Compare against buy-and-hold benchmark behavior.",
                "improves drawdown-adjusted return",
            ),
        ),
        status=StrategyStatus.RESEARCH_CANDIDATE,
    ),
    StrategySpec(
        strategy_id="earnings-drift-with-confirmation",
        name="Earnings Drift With Confirmation",
        description="Research candidate for post-earnings drift after confirmed positive reaction.",
        thesis=(
            "Some positive earnings surprises continue drifting when price confirms "
            "institutional demand."
        ),
        asset_class=AssetClass.US_EQUITIES,
        direction=StrategyDirection.LONG_ONLY,
        horizon=TradingHorizon.MULTI_DAY_SWING,
        universe=StrategyUniverse(
            description="Liquid US equities with recent earnings events.",
            filters=["recent earnings event", "minimum liquidity", "no unresolved data gaps"],
        ),
        signals=[
            StrategySignal(
                name="Earnings reaction",
                description="Price reaction confirms constructive interpretation of the event.",
                signal_type=SignalType.FUNDAMENTAL,
                inputs=["earnings event", "post-event close"],
                rule="post-event price action remains above the event confirmation level",
            ),
            StrategySignal(
                name="Volume confirmation",
                description="Participation supports the move.",
                signal_type=SignalType.VOLUME,
                inputs=["event volume", "average volume"],
                rule="event volume exceeds research threshold",
            ),
        ],
        entry_rules=[
            EntryRule(
                name="Delayed confirmation",
                description="Avoid same-day reaction chasing.",
                rule="enter only after confirmation on a later daily close",
            )
        ],
        exit_rules=[
            ExitRule(
                name="Drift exhaustion",
                description="Exit when the drift weakens or the planned window ends.",
                rule="exit on reversal, risk stop, or holding-period limit",
            )
        ],
        position_sizing=PositionSizingRule(
            method="event_risk_research",
            description="Use conservative placeholder sizing for event-driven candidates.",
            max_position_size="to be defined after event-risk tests",
        ),
        risk_rules=[
            RiskRule(
                name="Event gap guard",
                description="Reject candidates with excessive gap risk after the event.",
                veto_condition="post-event volatility exceeds research envelope",
            )
        ],
        holding_period="2 to 20 trading days",
        market_regime_filter=MarketRegimeFilter(
            description="Avoid broad risk-off conditions that overpower single-name events.",
            allowed_regimes=["risk_on", "neutral"],
            blocked_regimes=["risk_off"],
        ),
        expected_edge=(
            "Potential post-event continuation when price and volume confirm the surprise."
        ),
        failure_conditions=[
            "Earnings reaction is fully mean-reverted before entry.",
            "Guidance details contradict headline results.",
            "Broad market weakness dominates the event.",
        ],
        evidence_required=_evidence_requirements(
            (
                "Point-in-time event data",
                "Confirm event timing and surprise labels do not leak future revisions.",
                "all events timestamped before simulated entry",
            ),
            (
                "Cost sensitivity",
                "Compare returns before and after slippage and spread assumptions.",
                "edge remains positive after costs",
            ),
        ),
    ),
    StrategySpec(
        strategy_id="breakout-with-volume-confirmation",
        name="Breakout With Volume Confirmation",
        description="Long-only breakout candidate requiring price and participation confirmation.",
        thesis="Breakouts from well-defined ranges may persist when volume confirms demand.",
        asset_class=AssetClass.US_EQUITIES_AND_ETFS,
        direction=StrategyDirection.LONG_ONLY,
        horizon=TradingHorizon.MULTI_DAY_SWING,
        universe=StrategyUniverse(
            description="Liquid US equities and ETFs with compact prior ranges.",
            filters=["range compression", "minimum liquidity", "no stale data"],
        ),
        signals=[
            StrategySignal(
                name="Range breakout",
                description="Price closes above a prior range boundary.",
                signal_type=SignalType.PRICE,
                inputs=["close", "range high"],
                rule="close exceeds the prior range high",
            ),
            StrategySignal(
                name="Volume expansion",
                description="Breakout has higher participation than recent baseline.",
                signal_type=SignalType.VOLUME,
                inputs=["volume", "average volume"],
                rule="volume exceeds confirmation threshold",
            ),
        ],
        entry_rules=[
            EntryRule(
                name="Confirmed breakout",
                description="Enter only after a confirmed daily breakout close.",
                rule="daily close above range high with volume confirmation",
            )
        ],
        exit_rules=[
            ExitRule(
                name="Failed breakout",
                description="Exit if price falls back into the prior range.",
                rule="exit on failed breakout, stop, or planned time exit",
            )
        ],
        position_sizing=PositionSizingRule(
            method="range_risk_research",
            description="Size by placeholder range risk for comparable research results.",
            max_position_size="to be defined after risk calibration",
        ),
        risk_rules=[
            RiskRule(
                name="False breakout guard",
                description="Reject when breakout distance creates poor reward-to-risk.",
                veto_condition="entry is too extended from the invalidation level",
            )
        ],
        holding_period="3 to 25 trading days",
        market_regime_filter=MarketRegimeFilter(
            description="Prefer regimes where breakouts have historically followed through.",
            allowed_regimes=["risk_on"],
            blocked_regimes=["risk_off", "high_volatility"],
        ),
        expected_edge="Potential trend expansion after range compression and volume confirmation.",
        failure_conditions=[
            "Breakouts fail quickly after entry.",
            "Volume confirmation does not improve outcomes.",
            "Strategy is too sensitive to range lookback length.",
        ],
        evidence_required=_evidence_requirements(
            (
                "Parameter robustness",
                "Test range lookbacks and volume thresholds for fragility.",
                "performance remains stable across nearby parameters",
            ),
            (
                "Market regime split",
                "Compare risk-on and risk-off behavior separately.",
                "risk-off veto improves drawdown behavior",
            ),
        ),
    ),
    StrategySpec(
        strategy_id="oversold-mean-reversion-with-news-veto",
        name="Oversold Mean Reversion With News Veto",
        description="Long-only oversold bounce candidate with a sentiment/news veto layer.",
        thesis=(
            "Liquid names can revert after short-term stress, but negative news should be "
            "able to veto."
        ),
        asset_class=AssetClass.US_EQUITIES_AND_ETFS,
        direction=StrategyDirection.LONG_ONLY,
        horizon=TradingHorizon.DAILY,
        universe=StrategyUniverse(
            description="Liquid US equities and ETFs with short-term oversold readings.",
            filters=["minimum liquidity", "short-term oversold state", "data freshness confirmed"],
        ),
        signals=[
            StrategySignal(
                name="Oversold condition",
                description="Price is stretched below a short-term reference level.",
                signal_type=SignalType.PRICE,
                inputs=["close", "short-term moving average", "volatility"],
                rule="price stretch exceeds research threshold",
            ),
            StrategySignal(
                name="News veto",
                description="Timestamped negative event context can block the trade.",
                signal_type=SignalType.SENTIMENT,
                inputs=["timestamped news event", "event severity"],
                rule="negative high-severity event vetoes entry",
            ),
        ],
        entry_rules=[
            EntryRule(
                name="Oversold reversal",
                description="Enter only after an oversold condition begins to reverse.",
                rule="enter after a daily reversal trigger and no active news veto",
            )
        ],
        exit_rules=[
            ExitRule(
                name="Mean reversion target",
                description="Exit at target, stop, or time limit.",
                rule="exit on mean-reversion target, stop, or maximum holding period",
            )
        ],
        position_sizing=PositionSizingRule(
            method="volatility_adjusted_research",
            description="Use placeholder volatility-adjusted sizing for research comparisons.",
            max_position_size="to be defined by risk governance",
        ),
        risk_rules=[
            RiskRule(
                name="Stale data veto",
                description="Reject if price or sentiment data is stale.",
                veto_condition="required data timestamp is stale at decision time",
            ),
            RiskRule(
                name="News severity veto",
                description="Reject if severe negative event context is active.",
                veto_condition="active severe negative sentiment event exists",
            ),
        ],
        holding_period="1 to 7 trading days",
        market_regime_filter=MarketRegimeFilter(
            description="Avoid stress regimes where oversold can become more oversold.",
            allowed_regimes=["neutral", "risk_on"],
            blocked_regimes=["risk_off", "liquidity_stress"],
        ),
        expected_edge=(
            "Potential short-term reversion when stress is technical rather than fundamental."
        ),
        failure_conditions=[
            "Negative news veto removes most profitable trades.",
            "Oversold entries continue falling in high-volatility regimes.",
            "Point-in-time sentiment data is unavailable or unreliable.",
        ],
        evidence_required=_evidence_requirements(
            (
                "Sentiment comparison",
                "Compare the same strategy with and without the news veto.",
                "veto improves drawdown or tail-risk behavior",
            ),
            (
                "Timestamp integrity",
                "Verify news timestamps are available before simulated decisions.",
                "no future event leakage",
            ),
        ),
    ),
    StrategySpec(
        strategy_id="etf-risk-on-risk-off-rotation",
        name="ETF Risk-On/Risk-Off Rotation",
        description="ETF rotation candidate that can recommend cash when evidence is weak.",
        thesis=(
            "Broad ETF rotation may improve risk-adjusted exposure by moving between "
            "risk-on, defensive, and cash states."
        ),
        asset_class=AssetClass.ETFS,
        direction=StrategyDirection.LONG_ONLY,
        horizon=TradingHorizon.MULTI_DAY_SWING,
        universe=StrategyUniverse(
            description=(
                "Broad liquid ETFs representing risk-on, defensive, and cash-like exposures."
            ),
            symbols=["SPY", "QQQ", "TLT", "SHY"],
            filters=["high liquidity", "broad exposure", "daily data available"],
        ),
        signals=[
            StrategySignal(
                name="Risk appetite",
                description="Compares risk-on ETF behavior against defensive ETF behavior.",
                signal_type=SignalType.MARKET_REGIME,
                inputs=["risk ETF returns", "defensive ETF returns"],
                rule="risk-on exposure is allowed only when relative regime score is constructive",
            ),
            StrategySignal(
                name="Cash fallback",
                description="No-trade/cash is selected when evidence is weak.",
                signal_type=SignalType.RISK,
                inputs=["regime score", "drawdown state"],
                rule="cash is valid when regime confidence is below threshold",
            ),
        ],
        entry_rules=[
            EntryRule(
                name="Rotation selection",
                description="Select the highest-ranked eligible ETF or cash.",
                rule="enter selected ETF only when regime and risk gates allow exposure",
            )
        ],
        exit_rules=[
            ExitRule(
                name="Rotation change",
                description="Exit or rotate when regime score changes.",
                rule="exit current exposure when rank changes or risk gate selects cash",
            )
        ],
        position_sizing=PositionSizingRule(
            method="single_position_research",
            description="Hold one selected ETF or cash placeholder for transparent comparison.",
            max_position_size="to be defined after drawdown tests",
        ),
        risk_rules=[
            RiskRule(
                name="Cash is valid",
                description="Risk engine may select no trade instead of forcing exposure.",
                veto_condition="regime confidence is weak or drawdown state blocks exposure",
            )
        ],
        holding_period="5 to 40 trading days",
        market_regime_filter=MarketRegimeFilter(
            description="Strategy explicitly models regime state and may choose cash.",
            allowed_regimes=["risk_on", "defensive", "cash"],
            blocked_regimes=["data_stale"],
        ),
        expected_edge="Potential drawdown reduction through simple broad-market regime rotation.",
        failure_conditions=[
            "Rotation lags major market turns.",
            "Defensive assets fail during correlated selloffs.",
            "Cash recommendations reduce return without improving risk-adjusted outcomes.",
        ],
        evidence_required=_evidence_requirements(
            (
                "Cash comparison",
                "Measure whether cash/no-trade improves drawdown-adjusted behavior.",
                "cash state improves risk-adjusted results",
            ),
            (
                "Regime robustness",
                "Validate across bull, bear, sideways, and high-rate regimes.",
                "no single regime explains all performance",
            ),
        ),
    ),
)
