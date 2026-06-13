from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from edgelab.intraday.schema import (
    IntradayBar,
    IntradayBarInterval,
    IntradayInstrument,
    IntradayInstrumentType,
    IntradaySessionType,
    IntradaySetupCandidate,
    IntradaySetupDirection,
    IntradaySetupStatus,
    IntradaySetupType,
    IntradaySimulationAssumptions,
    OpeningBenchmarks,
)


def build_bar(**overrides: object) -> IntradayBar:
    data: dict[str, object] = {
        "symbol": "gen_syn",
        "timestamp": datetime(2024, 1, 16, 15, 30, tzinfo=UTC),
        "interval": IntradayBarInterval.ONE_MINUTE,
        "open": 100.0,
        "high": 101.0,
        "low": 99.5,
        "close": 100.5,
        "volume": 1000,
        "session_type": IntradaySessionType.REGULAR_FIRST_HOUR,
        "session_id": "generic-symbol-intraday-synthetic",
        "source": "synthetic_intraday_fixture",
        "ingested_at": datetime(2024, 1, 16, 15, 30, tzinfo=UTC),
    }
    data.update(overrides)
    return IntradayBar(**data)


def build_benchmarks() -> OpeningBenchmarks:
    return OpeningBenchmarks(
        symbol="GEN_SYN",
        session_id="generic-symbol-intraday-synthetic",
        session_date=date(2024, 1, 16),
        prior_regular_close=100,
        regular_open=100.5,
        opening_range_high=101,
        opening_range_low=99.5,
        first_hour_high=101.5,
        first_hour_low=99.5,
        plain_english_summary="Synthetic references only.",
    )


def test_intraday_bar_normalizes_symbol() -> None:
    bar = build_bar()

    assert bar.symbol == "GEN_SYN"


def test_intraday_bar_requires_positive_prices_and_valid_ohlc() -> None:
    with pytest.raises(ValidationError):
        build_bar(open=0)
    with pytest.raises(ValidationError, match="high"):
        build_bar(high=99)
    with pytest.raises(ValidationError, match="low"):
        build_bar(low=102)


def test_intraday_instrument_requires_positive_point_and_tick_values() -> None:
    with pytest.raises(ValidationError):
        IntradayInstrument(
            symbol="BAD",
            display_name="Bad Instrument",
            instrument_type=IntradayInstrumentType.OTHER,
            point_value=0,
            tick_size=0.01,
            tick_value=0.01,
            plain_english_description="Bad fixture.",
        )


def test_simulation_assumptions_require_positive_hold_and_contract_count() -> None:
    with pytest.raises(ValidationError):
        IntradaySimulationAssumptions(hold_minutes=0)
    with pytest.raises(ValidationError):
        IntradaySimulationAssumptions(contract_count=0)


def test_setup_allows_neutral_context_language_and_defaults_real_money_status() -> None:
    setup = IntradaySetupCandidate(
        setup_id="generic-symbol-intraday-synthetic-opening-range-breakout",
        symbol="gen_syn",
        session_id="generic-symbol-intraday-synthetic",
        session_date=date(2024, 1, 16),
        setup_type=IntradaySetupType.OPENING_RANGE_BREAKOUT,
        direction=IntradaySetupDirection.LONG_CONTEXT,
        status=IntradaySetupStatus.DETECTED,
        detected_at=datetime(2024, 1, 16, 15, 35, tzinfo=UTC),
        signal_bar_timestamp=datetime(2024, 1, 16, 15, 35, tzinfo=UTC),
        benchmark_context=build_benchmarks(),
        plain_english_summary="A long-context pattern appeared for research only.",
        why_it_appeared=["A measured opening range event appeared."],
        what_would_invalidate_it=["The reference levels stop holding."],
        what_is_missing=["Real historical intraday data."],
        why_edgelab_might_sit_out=["Synthetic data is not market evidence."],
    )

    assert setup.symbol == "GEN_SYN"
    assert setup.real_money_status == "Not allowed"


def test_setup_rejects_action_instruction_phrases() -> None:
    with pytest.raises(ValidationError, match="action instructions"):
        IntradaySetupCandidate(
            setup_id="bad-setup",
            symbol="GEN_SYN",
            session_id="generic-symbol-intraday-synthetic",
            session_date=date(2024, 1, 16),
            setup_type=IntradaySetupType.OPENING_RANGE_BREAKOUT,
            direction=IntradaySetupDirection.SHORT_CONTEXT,
            status=IntradaySetupStatus.DETECTED,
            detected_at=datetime(2024, 1, 16, 15, 35, tzinfo=UTC),
            signal_bar_timestamp=datetime(2024, 1, 16, 15, 35, tzinfo=UTC),
            benchmark_context=build_benchmarks(),
            plain_english_summary="short now",
            why_it_appeared=["A measured event appeared."],
            what_would_invalidate_it=["The reference levels stop holding."],
            what_is_missing=["Real historical intraday data."],
            why_edgelab_might_sit_out=["Synthetic data is not market evidence."],
        )
