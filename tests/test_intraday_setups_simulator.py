from edgelab.intraday.benchmarks import calculate_opening_benchmarks
from edgelab.intraday.fixtures import LocalIntradayFixtureProvider
from edgelab.intraday.schema import (
    IntradayEventType,
    IntradaySetupDirection,
    IntradaySetupType,
)
from edgelab.intraday.setups import IntradaySetupDetector, compare_paired_symbol_context
from edgelab.intraday.simulator import IntradaySimulator


def load_session(symbol: str, session_id: str):
    provider = LocalIntradayFixtureProvider()
    bars, issues = provider.load_bars(symbol, session_id)
    assert issues == []
    return bars


def test_event_detection_covers_required_event_types() -> None:
    detector = IntradaySetupDetector()
    session_expectations = {
        ("NQ_SYN", "nq-first-hour-synthetic"): {
            IntradayEventType.OPENING_GAP_UP,
            IntradayEventType.OPENING_RANGE_BREAKOUT,
            IntradayEventType.MOMENTUM_CONTINUATION,
        },
        ("ES_SYN", "es-opening-failure-short-context-synthetic"): {
            IntradayEventType.FAILED_OPENING_PUSH,
            IntradayEventType.OPENING_RANGE_FAILURE,
            IntradayEventType.OVERNIGHT_HIGH_SWEEP,
        },
        ("ES_SYN", "es-choppy-no-trade-synthetic"): {
            IntradayEventType.NO_TRADE_CHOPPY_OPEN,
            IntradayEventType.NO_TRADE_LOW_RANGE,
        },
    }

    for (symbol, session_id), expected_events in session_expectations.items():
        bars = load_session(symbol, session_id)
        benchmarks = calculate_opening_benchmarks(bars)
        events = detector.detect_events(bars, benchmarks)
        event_types = {event.event_type for event in events}
        assert expected_events.issubset(event_types)


def test_setup_detector_supports_required_setup_types() -> None:
    detector = IntradaySetupDetector()
    expectations = {
        ("ES_SYN", "es-first-hour-synthetic"): IntradaySetupType.OPENING_RANGE_BREAKOUT,
        (
            "ES_SYN",
            "es-opening-failure-short-context-synthetic",
        ): IntradaySetupType.FAILED_OPENING_PUSH,
        ("NQ_SYN", "nq-gap-fade-synthetic"): IntradaySetupType.GAP_FADE,
        ("ES_SYN", "es-choppy-no-trade-synthetic"): IntradaySetupType.NO_TRADE,
    }

    for (symbol, session_id), expected_setup in expectations.items():
        bars = load_session(symbol, session_id)
        setups = detector.detect_setups(bars, calculate_opening_benchmarks(bars))
        assert len(setups) == 1
        assert setups[0].setup_type == expected_setup
        assert setups[0].real_money_status == "Not allowed"


def test_no_trade_filters_override_setup_detection() -> None:
    bars = load_session("ES_SYN", "es-choppy-no-trade-synthetic")
    setups = IntradaySetupDetector().detect_setups(bars, calculate_opening_benchmarks(bars))

    assert setups[0].setup_type == IntradaySetupType.NO_TRADE
    assert setups[0].no_trade_reasons


def test_long_and_short_context_are_descriptive_only() -> None:
    bars = load_session("ES_SYN", "es-opening-failure-short-context-synthetic")
    setup = IntradaySetupDetector().detect_setups(bars, calculate_opening_benchmarks(bars))[0]

    assert setup.direction == IntradaySetupDirection.SHORT_CONTEXT
    assert "short-context pattern" in setup.plain_english_summary


def test_simulator_creates_hypothetical_trade_with_next_bar_entry() -> None:
    bars = load_session("GEN_SYN", "generic-symbol-intraday-synthetic")
    result = IntradaySimulator().run(bars)
    trade = result.hypothetical_trades[0]

    assert result.simulated_trade_count == 1
    assert trade.entry_time > trade.signal_time
    assert trade.net_pnl != 0
    assert result.real_money_status == "Not allowed"
    assert result.spike_verdict.value == "workflow_supported"


def test_simulator_supports_no_trade_day() -> None:
    bars = load_session("ES_SYN", "es-choppy-no-trade-synthetic")
    result = IntradaySimulator().run(bars)

    assert result.simulated_trade_count == 0
    assert result.no_trade_reason_count > 0
    assert result.total_net_pnl == 0


def test_simulator_short_context_pnl_math_and_status() -> None:
    bars = load_session("ES_SYN", "es-opening-failure-short-context-synthetic")
    result = IntradaySimulator().run(bars)

    assert result.hypothetical_trades[0].direction == IntradaySetupDirection.SHORT_CONTEXT
    assert result.hypothetical_trades[0].net_pnl > 0
    assert result.hypothetical_trades[0].real_money_status == "Not allowed"


def test_paired_instrument_comparison_is_optional() -> None:
    bars = load_session("GEN_SYN", "generic-symbol-intraday-synthetic")

    events, issues = compare_paired_symbol_context(bars, None)

    assert events == []
    assert issues[0].code == "paired_symbol_data_unavailable"
    assert IntradaySimulator().run(bars).simulated_trade_count == 1
