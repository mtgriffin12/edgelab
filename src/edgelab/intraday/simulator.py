"""Research-only intraday simulation."""

from __future__ import annotations

from datetime import date, timedelta

from edgelab.intraday.benchmarks import calculate_opening_benchmarks
from edgelab.intraday.fixtures import LocalIntradayFixtureProvider
from edgelab.intraday.schema import (
    IntradayBar,
    IntradayHypotheticalTrade,
    IntradayQualityIssue,
    IntradaySetupCandidate,
    IntradaySetupDirection,
    IntradaySetupType,
    IntradaySimulationAssumptions,
    IntradaySimulationResult,
    IntradaySpikeVerdict,
)
from edgelab.intraday.setups import IntradaySetupDetector


class IntradaySimulator:
    """Simulate one local hypothetical first-hour setup from fixture bars."""

    def __init__(
        self,
        fixture_provider: LocalIntradayFixtureProvider | None = None,
        setup_detector: IntradaySetupDetector | None = None,
    ) -> None:
        self.fixture_provider = fixture_provider or LocalIntradayFixtureProvider()
        self.setup_detector = setup_detector or IntradaySetupDetector()

    def run(
        self,
        bars: list[IntradayBar],
        assumptions: IntradaySimulationAssumptions | None = None,
    ) -> IntradaySimulationResult:
        """Run a fixture-backed hypothetical simulation."""

        active_assumptions = assumptions or IntradaySimulationAssumptions()
        if not bars:
            return _empty_result(active_assumptions)

        sorted_bars = sorted(bars, key=lambda bar: bar.timestamp)
        instrument = self.fixture_provider.get_instrument(sorted_bars[0].symbol)
        benchmarks = calculate_opening_benchmarks(sorted_bars)
        setup_candidates = self.setup_detector.detect_setups(
            sorted_bars,
            benchmarks,
            max_one_setup_per_day=active_assumptions.max_one_setup_per_day,
        )
        quality_issues = list(benchmarks.quality_issues)
        hypothetical_trades: list[IntradayHypotheticalTrade] = []

        for setup in setup_candidates:
            if setup.setup_type == IntradaySetupType.NO_TRADE:
                continue
            if (
                setup.direction == IntradaySetupDirection.SHORT_CONTEXT
                and not active_assumptions.allow_short_context
            ):
                quality_issues.append(
                    IntradayQualityIssue(
                        code="short_context_disabled",
                        message="Short-context simulation is disabled by assumptions.",
                        symbol=setup.symbol,
                        session_id=setup.session_id,
                    )
                )
                continue
            trade = _simulate_trade(
                sorted_bars, setup, active_assumptions, instrument.point_value, instrument.tick_size
            )
            if trade is None:
                quality_issues.append(
                    IntradayQualityIssue(
                        code="insufficient_exit_data",
                        message="No later fixture bar is available for the requested hold period.",
                        symbol=setup.symbol,
                        session_id=setup.session_id,
                        timestamp=setup.signal_bar_timestamp,
                    )
                )
                continue
            hypothetical_trades.append(trade)
            if active_assumptions.max_one_setup_per_day:
                break

        total_net_pnl = sum(trade.net_pnl for trade in hypothetical_trades)
        trade_count = len(hypothetical_trades)
        average_net_pnl = total_net_pnl / trade_count if trade_count else 0
        best_trade_net_pnl = max((trade.net_pnl for trade in hypothetical_trades), default=0)
        worst_trade_net_pnl = min((trade.net_pnl for trade in hypothetical_trades), default=0)
        win_rate_pct = (
            len([trade for trade in hypothetical_trades if trade.net_pnl > 0]) / trade_count * 100
            if trade_count
            else 0
        )
        no_trade_reason_count = sum(
            len(candidate.no_trade_reasons) for candidate in setup_candidates
        )
        spike_verdict = _spike_verdict(setup_candidates, hypothetical_trades, quality_issues)
        summary = _summary_text(setup_candidates, hypothetical_trades)
        conclusion = (
            "This synthetic workflow can be inspected for deeper research, but it is not proof "
            "of an edge or permission for real-money use."
        )

        return IntradaySimulationResult(
            result_id=f"{benchmarks.symbol.lower()}-{benchmarks.session_id}-intraday-simulation",
            symbol=benchmarks.symbol,
            session_id=benchmarks.session_id,
            session_date=benchmarks.session_date,
            setup_count=len(setup_candidates),
            simulated_trade_count=trade_count,
            no_trade_reason_count=no_trade_reason_count,
            total_net_pnl=round(total_net_pnl, 2),
            average_net_pnl=round(average_net_pnl, 2),
            best_trade_net_pnl=round(best_trade_net_pnl, 2),
            worst_trade_net_pnl=round(worst_trade_net_pnl, 2),
            win_rate_pct=round(win_rate_pct, 2),
            spike_verdict=spike_verdict,
            setup_candidates=setup_candidates,
            hypothetical_trades=hypothetical_trades,
            quality_issues=quality_issues,
            plain_english_summary=summary,
            conclusion=conclusion,
        )


def _simulate_trade(
    bars: list[IntradayBar],
    setup: IntradaySetupCandidate,
    assumptions: IntradaySimulationAssumptions,
    point_value: float,
    tick_size: float,
) -> IntradayHypotheticalTrade | None:
    signal_index = next(
        (index for index, bar in enumerate(bars) if bar.timestamp == setup.signal_bar_timestamp),
        None,
    )
    if signal_index is None or signal_index + 1 >= len(bars):
        return None
    entry_bar = bars[signal_index + 1]
    exit_time = entry_bar.timestamp + timedelta(minutes=assumptions.hold_minutes)
    exit_bar = next((bar for bar in bars if bar.timestamp >= exit_time), None)
    if exit_bar is None:
        return None

    slippage = assumptions.slippage_ticks * tick_size
    if setup.direction == IntradaySetupDirection.LONG_CONTEXT:
        entry_price = entry_bar.open + slippage
        exit_price = exit_bar.open - slippage
        gross_points = exit_price - entry_price
    elif setup.direction == IntradaySetupDirection.SHORT_CONTEXT:
        entry_price = entry_bar.open - slippage
        exit_price = exit_bar.open + slippage
        gross_points = entry_price - exit_price
    else:
        return None

    gross_pnl = gross_points * point_value * assumptions.contract_count
    estimated_costs = assumptions.commission_per_contract * assumptions.contract_count * 2
    net_pnl = gross_pnl - estimated_costs
    result_label = "positive" if net_pnl > 0 else "negative" if net_pnl < 0 else "flat"
    context_label = setup.direction.value.replace("_", "-")

    return IntradayHypotheticalTrade(
        trade_id=f"{setup.setup_id}-hypothetical",
        setup_id=setup.setup_id,
        symbol=setup.symbol,
        direction=setup.direction,
        signal_time=setup.signal_bar_timestamp,
        entry_time=entry_bar.timestamp,
        entry_price=round(entry_price, 4),
        exit_time=exit_bar.timestamp,
        exit_price=round(exit_price, 4),
        contract_count=assumptions.contract_count,
        gross_points=round(gross_points, 4),
        gross_pnl=round(gross_pnl, 2),
        estimated_costs=round(estimated_costs, 2),
        net_pnl=round(net_pnl, 2),
        result_label=result_label,
        plain_english_reason=(
            f"The {context_label} pattern was tested from the next fixture bar open "
            f"for {assumptions.hold_minutes} minutes."
        ),
    )


def _spike_verdict(
    setup_candidates: list[IntradaySetupCandidate],
    hypothetical_trades: list[IntradayHypotheticalTrade],
    quality_issues: list[IntradayQualityIssue],
) -> IntradaySpikeVerdict:
    if quality_issues and not setup_candidates:
        return IntradaySpikeVerdict.INSUFFICIENT_FIXTURE_COVERAGE
    if hypothetical_trades or setup_candidates:
        return IntradaySpikeVerdict.WORKFLOW_SUPPORTED
    return IntradaySpikeVerdict.NEEDS_RULE_REFINEMENT


def _summary_text(
    setup_candidates: list[IntradaySetupCandidate],
    hypothetical_trades: list[IntradayHypotheticalTrade],
) -> str:
    if not setup_candidates:
        return "No setup was available in the synthetic fixture."
    if setup_candidates[0].setup_type == IntradaySetupType.NO_TRADE:
        return "EdgeLab produced a synthetic sit-out result rather than forcing a setup."
    if hypothetical_trades:
        return "EdgeLab represented one synthetic setup and calculated a hypothetical result."
    return "EdgeLab represented a synthetic setup but could not calculate an exit."


def _empty_result(assumptions: IntradaySimulationAssumptions) -> IntradaySimulationResult:
    _ = assumptions
    return IntradaySimulationResult(
        result_id="empty-intraday-simulation",
        symbol="EMPTY",
        session_id="empty",
        session_date=date.today(),
        setup_count=0,
        simulated_trade_count=0,
        no_trade_reason_count=0,
        total_net_pnl=0,
        average_net_pnl=0,
        best_trade_net_pnl=0,
        worst_trade_net_pnl=0,
        win_rate_pct=0,
        spike_verdict=IntradaySpikeVerdict.INSUFFICIENT_FIXTURE_COVERAGE,
        quality_issues=[
            IntradayQualityIssue(
                code="empty_dataset",
                message="No intraday bars were provided for simulation.",
            )
        ],
        plain_english_summary="No synthetic intraday bars were available to simulate.",
        conclusion="No result can be inferred without local fixture bars.",
    )
