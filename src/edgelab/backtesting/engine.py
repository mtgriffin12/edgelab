"""Local fixture-based backtesting engine."""

from __future__ import annotations

from edgelab.backtesting.metrics import (
    calculate_average_loss_pct,
    calculate_average_win_pct,
    calculate_exposure_pct,
    calculate_max_drawdown_pct,
    calculate_profit_factor,
    calculate_total_return_pct,
    calculate_win_rate_pct,
    losing_trades,
    winning_trades,
)
from edgelab.backtesting.schema import (
    BacktestQualityIssue,
    BacktestRequest,
    BacktestResult,
    BacktestStatus,
    EquityCurvePoint,
    ExecutionAssumptions,
    OrderSide,
    SimulatedFill,
    SimulatedOrderType,
    SimulatedTrade,
)
from edgelab.data.schema import OHLCVBar
from edgelab.strategies.schema import StrategySpec

SUPPORTED_STRATEGY_IDS = {"relative-strength-pullback"}
DEFAULT_HOLDING_PERIOD_BARS = 2


class BacktestEngine:
    """Simple deterministic engine for Phase 4 research evidence."""

    def run(
        self,
        strategy: StrategySpec,
        bars: list[OHLCVBar],
        request: BacktestRequest,
    ) -> BacktestResult:
        """Run a local fixture backtest without external data or orders."""

        assumptions = request.execution_assumptions.model_copy(
            update={"initial_capital": request.initial_capital}
        )
        filtered_bars = _filter_bars(bars, request)

        if strategy.strategy_id not in SUPPORTED_STRATEGY_IDS:
            return _empty_result(
                strategy_id=strategy.strategy_id,
                symbol=request.symbol,
                assumptions=assumptions,
                status=BacktestStatus.UNSUPPORTED_STRATEGY,
                issues=[
                    BacktestQualityIssue(
                        code="unsupported_strategy",
                        message=(
                            "Phase 4 engine supports only the placeholder "
                            "relative-strength-pullback rule."
                        ),
                    )
                ],
            )

        if len(filtered_bars) < 2:
            return _empty_result(
                strategy_id=strategy.strategy_id,
                symbol=request.symbol,
                assumptions=assumptions,
                status=BacktestStatus.NO_DATA,
                issues=[
                    BacktestQualityIssue(
                        code="insufficient_bars",
                        message=(
                            "At least two bars are required for point-in-time signal evaluation."
                        ),
                    )
                ],
            )

        return self._run_close_above_prior_close(strategy, filtered_bars, assumptions)

    def _run_close_above_prior_close(
        self,
        strategy: StrategySpec,
        bars: list[OHLCVBar],
        assumptions: ExecutionAssumptions,
    ) -> BacktestResult:
        cash = assumptions.initial_capital
        quantity = 0.0
        entry_fill: SimulatedFill | None = None
        entry_index: int | None = None
        trades: list[SimulatedTrade] = []
        equity_curve: list[EquityCurvePoint] = []
        pending_entry = False
        pending_exit_reason: str | None = None

        for index, bar in enumerate(bars):
            if (
                pending_exit_reason
                and quantity > 0
                and entry_fill is not None
                and entry_index is not None
            ):
                exit_fill = _create_fill(bar, OrderSide.SELL, quantity, assumptions)
                cash += (exit_fill.quantity * exit_fill.price) - exit_fill.commission
                trades.append(
                    _create_trade(
                        strategy_id=strategy.strategy_id,
                        symbol=bar.symbol,
                        entry_fill=entry_fill,
                        exit_fill=exit_fill,
                        holding_period_bars=index - entry_index,
                        exit_reason=pending_exit_reason,
                    )
                )
                quantity = 0.0
                entry_fill = None
                entry_index = None
                pending_exit_reason = None

            if pending_entry and quantity == 0:
                entry_fill = _create_entry_fill(bar, cash, assumptions)
                if entry_fill.quantity > 0:
                    quantity = entry_fill.quantity
                    cash -= (entry_fill.quantity * entry_fill.price) + entry_fill.commission
                    entry_index = index
                pending_entry = False

            equity_curve.append(_equity_point(bar, cash, quantity))

            if index == 0:
                continue

            previous_bar = bars[index - 1]
            if quantity == 0 and _entry_signal(previous_bar, bar):
                pending_entry = True
            elif quantity > 0 and entry_index is not None:
                held_bars = index - entry_index
                if held_bars >= DEFAULT_HOLDING_PERIOD_BARS:
                    pending_exit_reason = "fixed_holding_period"
                elif _exit_signal(previous_bar, bar):
                    pending_exit_reason = "close_below_prior_close"

        if quantity > 0 and entry_fill is not None and entry_index is not None:
            final_bar = bars[-1]
            exit_fill = _create_fill(final_bar, OrderSide.SELL, quantity, assumptions)
            cash += (exit_fill.quantity * exit_fill.price) - exit_fill.commission
            trades.append(
                _create_trade(
                    strategy_id=strategy.strategy_id,
                    symbol=final_bar.symbol,
                    entry_fill=entry_fill,
                    exit_fill=exit_fill,
                    holding_period_bars=len(bars) - 1 - entry_index,
                    exit_reason="end_of_fixture",
                )
            )
            quantity = 0.0
            equity_curve[-1] = _equity_point(final_bar, cash, quantity)

        return _result_from_records(
            strategy.strategy_id, bars[0].symbol, assumptions, trades, equity_curve
        )


def _filter_bars(bars: list[OHLCVBar], request: BacktestRequest) -> list[OHLCVBar]:
    filtered = [
        bar
        for bar in bars
        if bar.symbol == request.symbol
        and (request.start_timestamp is None or bar.timestamp >= request.start_timestamp)
        and (request.end_timestamp is None or bar.timestamp <= request.end_timestamp)
    ]
    return sorted(filtered, key=lambda bar: bar.timestamp)


def _entry_signal(previous_bar: OHLCVBar, current_bar: OHLCVBar) -> bool:
    return current_bar.close > previous_bar.close


def _exit_signal(previous_bar: OHLCVBar, current_bar: OHLCVBar) -> bool:
    return current_bar.close < previous_bar.close


def _execution_price(bar: OHLCVBar, side: OrderSide, assumptions: ExecutionAssumptions) -> float:
    base_price = bar.open if assumptions.execution_timing == "next_open" else bar.close
    slippage_multiplier = assumptions.slippage_bps / 10_000
    if side == OrderSide.BUY:
        return base_price * (1 + slippage_multiplier)
    return base_price * (1 - slippage_multiplier)


def _create_entry_fill(
    bar: OHLCVBar, cash: float, assumptions: ExecutionAssumptions
) -> SimulatedFill:
    price = _execution_price(bar, OrderSide.BUY, assumptions)
    budget = min(cash, assumptions.initial_capital * assumptions.max_position_pct)
    quantity = budget / price if assumptions.allow_fractional_shares else int(budget // price)
    if quantity <= 0:
        quantity = 0.0
    return SimulatedFill(
        timestamp=bar.timestamp,
        side=OrderSide.BUY,
        order_type=SimulatedOrderType.MARKET,
        quantity=quantity,
        price=price,
        commission=assumptions.commission_per_trade,
        slippage_bps=assumptions.slippage_bps,
    )


def _create_fill(
    bar: OHLCVBar,
    side: OrderSide,
    quantity: float,
    assumptions: ExecutionAssumptions,
) -> SimulatedFill:
    return SimulatedFill(
        timestamp=bar.timestamp,
        side=side,
        order_type=SimulatedOrderType.MARKET,
        quantity=quantity,
        price=_execution_price(bar, side, assumptions),
        commission=assumptions.commission_per_trade,
        slippage_bps=assumptions.slippage_bps,
    )


def _create_trade(
    strategy_id: str,
    symbol: str,
    entry_fill: SimulatedFill,
    exit_fill: SimulatedFill,
    holding_period_bars: int,
    exit_reason: str,
) -> SimulatedTrade:
    gross_pnl = (exit_fill.price - entry_fill.price) * entry_fill.quantity
    net_pnl = gross_pnl - entry_fill.commission - exit_fill.commission
    cost_basis = entry_fill.price * entry_fill.quantity
    return_pct = (net_pnl / cost_basis) * 100 if cost_basis > 0 else 0.0
    return SimulatedTrade(
        strategy_id=strategy_id,
        symbol=symbol,
        entry_fill=entry_fill,
        exit_fill=exit_fill,
        quantity=entry_fill.quantity,
        gross_pnl=gross_pnl,
        net_pnl=net_pnl,
        return_pct=return_pct,
        holding_period_bars=holding_period_bars,
        exit_reason=exit_reason,
    )


def _equity_point(bar: OHLCVBar, cash: float, quantity: float) -> EquityCurvePoint:
    market_value = quantity * bar.close
    return EquityCurvePoint(
        timestamp=bar.timestamp,
        cash=cash,
        position_quantity=quantity,
        position_market_value=market_value,
        equity=cash + market_value,
    )


def _result_from_records(
    strategy_id: str,
    symbol: str,
    assumptions: ExecutionAssumptions,
    trades: list[SimulatedTrade],
    equity_curve: list[EquityCurvePoint],
) -> BacktestResult:
    final_equity = equity_curve[-1].equity if equity_curve else assumptions.initial_capital
    wins = winning_trades(trades)
    losses = losing_trades(trades)
    return BacktestResult(
        strategy_id=strategy_id,
        symbol=symbol,
        status=BacktestStatus.COMPLETED,
        initial_capital=assumptions.initial_capital,
        final_equity=round(final_equity, 6),
        total_return_pct=round(
            calculate_total_return_pct(assumptions.initial_capital, final_equity), 6
        ),
        max_drawdown_pct=round(calculate_max_drawdown_pct(equity_curve), 6),
        trade_count=len(trades),
        winning_trade_count=len(wins),
        losing_trade_count=len(losses),
        win_rate_pct=round(calculate_win_rate_pct(trades), 6),
        average_win_pct=_round_optional(calculate_average_win_pct(trades)),
        average_loss_pct=_round_optional(calculate_average_loss_pct(trades)),
        profit_factor=_round_optional(calculate_profit_factor(trades)),
        exposure_pct=round(calculate_exposure_pct(equity_curve), 6),
        trades=trades,
        equity_curve=equity_curve,
        quality_issues=[],
        assumptions_summary=assumptions.model_dump(mode="json"),
        conclusion="research_only" if trades else "insufficient_evidence",
    )


def _empty_result(
    strategy_id: str,
    symbol: str,
    assumptions: ExecutionAssumptions,
    status: BacktestStatus,
    issues: list[BacktestQualityIssue],
) -> BacktestResult:
    return BacktestResult(
        strategy_id=strategy_id,
        symbol=symbol,
        status=status,
        initial_capital=assumptions.initial_capital,
        final_equity=assumptions.initial_capital,
        total_return_pct=0.0,
        max_drawdown_pct=0.0,
        trade_count=0,
        winning_trade_count=0,
        losing_trade_count=0,
        win_rate_pct=0.0,
        average_win_pct=None,
        average_loss_pct=None,
        profit_factor=None,
        exposure_pct=0.0,
        quality_issues=issues,
        assumptions_summary=assumptions.model_dump(mode="json"),
        conclusion="insufficient_evidence",
    )


def _round_optional(value: float | None) -> float | None:
    return round(value, 6) if value is not None else None
