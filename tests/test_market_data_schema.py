from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from edgelab.data.schema import BarInterval, OHLCVBar


def build_bar(**overrides: object) -> OHLCVBar:
    data: dict[str, object] = {
        "symbol": "spy",
        "timestamp": datetime(2024, 1, 2, tzinfo=UTC),
        "interval": BarInterval.DAILY,
        "open": 470.0,
        "high": 475.0,
        "low": 468.5,
        "close": 472.25,
        "volume": 72_000_000,
        "adjusted_close": 472.25,
        "source": "synthetic_fixture",
        "ingested_at": datetime(2024, 1, 3, tzinfo=UTC),
    }
    data.update(overrides)
    return OHLCVBar(**data)


def test_ohlcv_bar_normalizes_symbol() -> None:
    bar = build_bar(symbol=" spy ")

    assert bar.symbol == "SPY"


def test_ohlcv_bar_rejects_invalid_high_low_relationships() -> None:
    with pytest.raises(ValidationError, match="high must be"):
        build_bar(high=469.0)

    with pytest.raises(ValidationError, match="low must be"):
        build_bar(low=473.0)


def test_ohlcv_bar_rejects_negative_prices_and_volume() -> None:
    with pytest.raises(ValidationError):
        build_bar(open=-1.0)

    with pytest.raises(ValidationError):
        build_bar(volume=-1)


def test_ohlcv_bar_rejects_future_timestamps_by_default() -> None:
    with pytest.raises(ValidationError, match="future"):
        build_bar(timestamp=datetime.now(UTC) + timedelta(days=1))


def test_ohlcv_bar_can_allow_future_timestamps_for_tests() -> None:
    bar = build_bar(
        timestamp=datetime.now(UTC) + timedelta(days=1),
        allow_future_timestamp=True,
    )

    assert bar.allow_future_timestamp is True
