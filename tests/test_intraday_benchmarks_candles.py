from edgelab.intraday.benchmarks import calculate_opening_benchmarks
from edgelab.intraday.candles import classify_candle
from edgelab.intraday.fixtures import LocalIntradayFixtureProvider
from edgelab.intraday.schema import CandleDirection, CandleShape


def test_opening_benchmark_calculation() -> None:
    provider = LocalIntradayFixtureProvider()
    bars, issues = provider.load_bars("GEN_SYN", "generic-symbol-intraday-synthetic")

    benchmarks = calculate_opening_benchmarks(bars)

    assert issues == []
    assert benchmarks.prior_regular_close == 100
    assert benchmarks.overnight_high == 100.5
    assert benchmarks.premarket_high == 100.7
    assert benchmarks.regular_open == 100.5
    assert benchmarks.opening_range_high == 100.94
    assert benchmarks.opening_range_low == 100.2
    assert benchmarks.first_hour_high == 101.72
    assert benchmarks.opening_gap_pct is not None


def test_candle_classification_formulas_and_shapes() -> None:
    provider = LocalIntradayFixtureProvider()
    bars, _issues = provider.load_bars("GEN_SYN", "generic-symbol-intraday-synthetic")
    strong = classify_candle(bars[10])
    ordinary = classify_candle(bars[5])

    assert strong.direction == CandleDirection.UP
    assert strong.shape == CandleShape.STRONG_UP
    assert strong.body_size > 0
    assert strong.upper_wick_size >= 0
    assert strong.lower_wick_size >= 0
    assert strong.range_size > 0
    assert ordinary.shape in {
        CandleShape.INDECISION,
        CandleShape.ORDINARY,
        CandleShape.STRONG_UP,
    }


def test_candle_classifies_indecision_and_reversal_like() -> None:
    provider = LocalIntradayFixtureProvider()
    bars, _issues = provider.load_bars("ES_SYN", "es-choppy-no-trade-synthetic")

    shapes = {classify_candle(bar).shape for bar in bars}

    assert CandleShape.INDECISION in shapes or CandleShape.REVERSAL_LIKE in shapes
