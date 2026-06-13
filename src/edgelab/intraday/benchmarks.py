"""Opening benchmark calculations for synthetic intraday bars."""

from __future__ import annotations

from datetime import date

from edgelab.intraday.schema import (
    IntradayBar,
    IntradayQualityIssue,
    IntradaySessionType,
    OpeningBenchmarks,
)


def calculate_opening_benchmarks(bars: list[IntradayBar]) -> OpeningBenchmarks:
    """Calculate opening reference levels from one synthetic fixture session."""

    if not bars:
        raise ValueError("bars must include at least one intraday bar")

    sorted_bars = sorted(bars, key=lambda bar: bar.timestamp)
    symbol = sorted_bars[0].symbol
    session_id = sorted_bars[0].session_id
    regular_first_hour = [
        bar for bar in sorted_bars if bar.session_type == IntradaySessionType.REGULAR_FIRST_HOUR
    ]
    session_date = _session_date(sorted_bars, regular_first_hour)
    issues: list[IntradayQualityIssue] = []

    overnight_bars = [
        bar
        for bar in sorted_bars
        if bar.session_type == IntradaySessionType.OVERNIGHT
        and bar.timestamp.date() <= session_date
    ]
    premarket_bars = [
        bar
        for bar in sorted_bars
        if bar.session_type == IntradaySessionType.PREMARKET
        and bar.timestamp.date() <= session_date
    ]
    prior_regular_bars = [
        bar
        for bar in sorted_bars
        if bar.session_type == IntradaySessionType.REGULAR_SESSION
        and bar.timestamp.date() < session_date
    ]

    prior_regular_close = _prior_regular_close(
        prior_regular_bars, overnight_bars, issues, symbol, session_id
    )
    overnight_high = _max_high(overnight_bars, "missing_overnight_high", issues, symbol, session_id)
    overnight_low = _min_low(overnight_bars, "missing_overnight_low", issues, symbol, session_id)
    premarket_high = _max_high(premarket_bars, "missing_premarket_high", issues, symbol, session_id)
    premarket_low = _min_low(premarket_bars, "missing_premarket_low", issues, symbol, session_id)
    regular_open = regular_first_hour[0].open if regular_first_hour else None
    if regular_open is None:
        issues.append(
            IntradayQualityIssue(
                code="missing_regular_open",
                message="No first-hour regular-session bar is available for the regular open.",
                symbol=symbol,
                session_id=session_id,
            )
        )

    opening_range_bars = [bar for bar in regular_first_hour if bar.interval.value == "one_minute"][
        :5
    ]
    opening_range_high = max((bar.high for bar in opening_range_bars), default=None)
    opening_range_low = min((bar.low for bar in opening_range_bars), default=None)
    if len(opening_range_bars) < 5:
        issues.append(
            IntradayQualityIssue(
                code="insufficient_opening_range_bars",
                message="Opening range needs at least five one-minute first-hour bars.",
                symbol=symbol,
                session_id=session_id,
            )
        )

    opening_gap_pct = None
    if prior_regular_close is not None and regular_open is not None:
        opening_gap_pct = (regular_open - prior_regular_close) / prior_regular_close * 100
    else:
        issues.append(
            IntradayQualityIssue(
                code="missing_opening_gap_pct",
                message="Opening gap percentage needs a prior close and regular open.",
                symbol=symbol,
                session_id=session_id,
            )
        )

    first_hour_high = max((bar.high for bar in regular_first_hour), default=None)
    first_hour_low = min((bar.low for bar in regular_first_hour), default=None)
    if not regular_first_hour:
        issues.append(
            IntradayQualityIssue(
                code="missing_first_hour_bars",
                message="No first-hour bars are available for first-hour high and low.",
                symbol=symbol,
                session_id=session_id,
            )
        )

    summary = (
        f"{symbol} synthetic opening references use local fixture bars only. "
        "They describe levels to compare against; they are not live signals."
    )
    return OpeningBenchmarks(
        symbol=symbol,
        session_id=session_id,
        session_date=session_date,
        prior_regular_close=prior_regular_close,
        overnight_high=overnight_high,
        overnight_low=overnight_low,
        premarket_high=premarket_high,
        premarket_low=premarket_low,
        regular_open=regular_open,
        opening_range_high=opening_range_high,
        opening_range_low=opening_range_low,
        opening_gap_pct=opening_gap_pct,
        first_hour_high=first_hour_high,
        first_hour_low=first_hour_low,
        plain_english_summary=summary,
        quality_issues=issues,
    )


def _session_date(bars: list[IntradayBar], first_hour_bars: list[IntradayBar]) -> date:
    if first_hour_bars:
        return first_hour_bars[0].timestamp.date()
    return bars[-1].timestamp.date()


def _prior_regular_close(
    prior_regular_bars: list[IntradayBar],
    overnight_bars: list[IntradayBar],
    issues: list[IntradayQualityIssue],
    symbol: str,
    session_id: str,
) -> float | None:
    if prior_regular_bars:
        return sorted(prior_regular_bars, key=lambda bar: bar.timestamp)[-1].close
    if overnight_bars:
        return sorted(overnight_bars, key=lambda bar: bar.timestamp)[0].open
    issues.append(
        IntradayQualityIssue(
            code="missing_prior_regular_close",
            message="No prior regular close or overnight fallback is available.",
            symbol=symbol,
            session_id=session_id,
        )
    )
    return None


def _max_high(
    bars: list[IntradayBar],
    code: str,
    issues: list[IntradayQualityIssue],
    symbol: str,
    session_id: str,
) -> float | None:
    if bars:
        return max(bar.high for bar in bars)
    issues.append(
        IntradayQualityIssue(
            code=code,
            message=f"{code.replace('_', ' ')} cannot be calculated without matching bars.",
            symbol=symbol,
            session_id=session_id,
        )
    )
    return None


def _min_low(
    bars: list[IntradayBar],
    code: str,
    issues: list[IntradayQualityIssue],
    symbol: str,
    session_id: str,
) -> float | None:
    if bars:
        return min(bar.low for bar in bars)
    issues.append(
        IntradayQualityIssue(
            code=code,
            message=f"{code.replace('_', ' ')} cannot be calculated without matching bars.",
            symbol=symbol,
            session_id=session_id,
        )
    )
    return None
