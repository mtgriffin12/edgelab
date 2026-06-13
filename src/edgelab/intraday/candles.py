"""Deterministic intraday candle classification."""

from __future__ import annotations

from dataclasses import dataclass

from edgelab.intraday.schema import CandleDirection, CandleShape, IntradayBar


@dataclass(frozen=True)
class CandleClassification:
    """Calculated candle dimensions and shape."""

    direction: CandleDirection
    shape: CandleShape
    body_size: float
    upper_wick_size: float
    lower_wick_size: float
    range_size: float
    body_pct: float


def classify_candle(bar: IntradayBar) -> CandleClassification:
    """Classify a single OHLC bar with explicit formulas."""

    range_size = bar.high - bar.low
    if range_size <= 0:
        return CandleClassification(
            direction=CandleDirection.FLAT,
            shape=CandleShape.INVALID,
            body_size=0,
            upper_wick_size=0,
            lower_wick_size=0,
            range_size=range_size,
            body_pct=0,
        )

    body_size = abs(bar.close - bar.open)
    upper_wick_size = bar.high - max(bar.open, bar.close)
    lower_wick_size = min(bar.open, bar.close) - bar.low
    body_pct = body_size / range_size
    direction = candle_direction(bar)

    if _is_strong_up(bar, direction, body_pct, range_size):
        shape = CandleShape.STRONG_UP
    elif _is_strong_down(bar, direction, body_pct, range_size):
        shape = CandleShape.STRONG_DOWN
    elif body_pct <= 0.25:
        shape = CandleShape.INDECISION
    elif _is_reversal_like(bar, upper_wick_size, lower_wick_size, range_size):
        shape = CandleShape.REVERSAL_LIKE
    else:
        shape = CandleShape.ORDINARY

    return CandleClassification(
        direction=direction,
        shape=shape,
        body_size=body_size,
        upper_wick_size=upper_wick_size,
        lower_wick_size=lower_wick_size,
        range_size=range_size,
        body_pct=body_pct,
    )


def candle_direction(bar: IntradayBar) -> CandleDirection:
    """Return candle direction based on close versus open."""

    if bar.close > bar.open:
        return CandleDirection.UP
    if bar.close < bar.open:
        return CandleDirection.DOWN
    return CandleDirection.FLAT


def is_strong_up_candle(bar: IntradayBar) -> bool:
    """Return whether a bar is a strong up candle."""

    return classify_candle(bar).shape == CandleShape.STRONG_UP


def is_strong_down_candle(bar: IntradayBar) -> bool:
    """Return whether a bar is a strong down candle."""

    return classify_candle(bar).shape == CandleShape.STRONG_DOWN


def is_indecision_candle(bar: IntradayBar) -> bool:
    """Return whether a bar is an indecision candle."""

    return classify_candle(bar).shape == CandleShape.INDECISION


def is_reversal_like_candle(bar: IntradayBar) -> bool:
    """Return whether a bar has reversal-like wick behavior."""

    return classify_candle(bar).shape == CandleShape.REVERSAL_LIKE


def _is_strong_up(
    bar: IntradayBar,
    direction: CandleDirection,
    body_pct: float,
    range_size: float,
) -> bool:
    return (
        direction == CandleDirection.UP
        and body_pct >= 0.60
        and (bar.high - bar.close) / range_size <= 0.25
    )


def _is_strong_down(
    bar: IntradayBar,
    direction: CandleDirection,
    body_pct: float,
    range_size: float,
) -> bool:
    return (
        direction == CandleDirection.DOWN
        and body_pct >= 0.60
        and (bar.close - bar.low) / range_size <= 0.25
    )


def _is_reversal_like(
    bar: IntradayBar,
    upper_wick_size: float,
    lower_wick_size: float,
    range_size: float,
) -> bool:
    long_upper = upper_wick_size / range_size >= 0.50 and bar.close < (bar.low + range_size * 0.5)
    long_lower = lower_wick_size / range_size >= 0.50 and bar.close > (bar.low + range_size * 0.5)
    return long_upper or long_lower
