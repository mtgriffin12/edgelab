"""Deterministic backtesting metric calculations."""

from edgelab.backtesting.schema import EquityCurvePoint, SimulatedTrade


def calculate_total_return_pct(initial_capital: float, final_equity: float) -> float:
    """Calculate total return percentage."""

    if initial_capital <= 0:
        return 0.0
    return ((final_equity / initial_capital) - 1.0) * 100.0


def calculate_max_drawdown_pct(equity_curve: list[EquityCurvePoint]) -> float:
    """Calculate max drawdown percentage from an equity curve."""

    if not equity_curve:
        return 0.0

    peak = equity_curve[0].equity
    max_drawdown = 0.0
    for point in equity_curve:
        peak = max(peak, point.equity)
        if peak > 0:
            drawdown = ((peak - point.equity) / peak) * 100.0
            max_drawdown = max(max_drawdown, drawdown)
    return max_drawdown


def winning_trades(trades: list[SimulatedTrade]) -> list[SimulatedTrade]:
    """Return profitable trades."""

    return [trade for trade in trades if trade.net_pnl > 0]


def losing_trades(trades: list[SimulatedTrade]) -> list[SimulatedTrade]:
    """Return losing trades."""

    return [trade for trade in trades if trade.net_pnl < 0]


def calculate_win_rate_pct(trades: list[SimulatedTrade]) -> float:
    """Calculate win rate percentage."""

    if not trades:
        return 0.0
    return (len(winning_trades(trades)) / len(trades)) * 100.0


def calculate_average_win_pct(trades: list[SimulatedTrade]) -> float | None:
    """Calculate average winning trade return percentage."""

    wins = winning_trades(trades)
    if not wins:
        return None
    return sum(trade.return_pct for trade in wins) / len(wins)


def calculate_average_loss_pct(trades: list[SimulatedTrade]) -> float | None:
    """Calculate average losing trade return percentage."""

    losses = losing_trades(trades)
    if not losses:
        return None
    return sum(trade.return_pct for trade in losses) / len(losses)


def calculate_profit_factor(trades: list[SimulatedTrade]) -> float | None:
    """Calculate profit factor with explicit edge-case handling."""

    gross_profit = sum(trade.net_pnl for trade in trades if trade.net_pnl > 0)
    gross_loss = abs(sum(trade.net_pnl for trade in trades if trade.net_pnl < 0))

    if gross_profit == 0 and gross_loss == 0:
        return None
    if gross_loss == 0:
        return None
    return gross_profit / gross_loss


def calculate_exposure_pct(equity_curve: list[EquityCurvePoint]) -> float:
    """Calculate percentage of points with open exposure."""

    if not equity_curve:
        return 0.0
    exposed_points = [point for point in equity_curve if point.position_quantity > 0]
    return (len(exposed_points) / len(equity_curve)) * 100.0
