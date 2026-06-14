from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from edgelab.intraday.historical_schema import (
    HistoricalIntradayAdjustmentMode,
    HistoricalIntradayBar,
    HistoricalIntradayDataSource,
    HistoricalIntradayProviderType,
)
from edgelab.intraday.schema import IntradayBarInterval, IntradaySessionType


def build_bar(**overrides: object) -> HistoricalIntradayBar:
    data: dict[str, object] = {
        "symbol": "spy",
        "timestamp_utc": datetime(2024, 1, 2, 14, 30),
        "raw_timestamp": "2024-01-02T09:30:00",
        "source_timezone": "America/New_York",
        "interval": IntradayBarInterval.ONE_MINUTE,
        "open": 470.0,
        "high": 470.2,
        "low": 469.9,
        "close": 470.1,
        "volume": 1000,
        "session_type": IntradaySessionType.REGULAR_FIRST_HOUR,
        "session_id": "spy-2024-01-02-historical",
        "provider": "local_csv_sample",
        "dataset_id": "spy_historical_sample",
        "adjustment_mode": HistoricalIntradayAdjustmentMode.UNADJUSTED,
        "ingested_at": datetime(2024, 1, 2, 15, 0, tzinfo=UTC),
    }
    data.update(overrides)
    return HistoricalIntradayBar(**data)


def test_historical_bar_normalizes_symbol_and_timestamp() -> None:
    bar = build_bar()

    assert bar.symbol == "SPY"
    assert bar.timestamp_utc.tzinfo is not None
    assert bar.timestamp_utc.utcoffset().total_seconds() == 0


def test_historical_bar_requires_positive_prices_and_valid_ohlc() -> None:
    with pytest.raises(ValidationError):
        build_bar(open=-1)

    with pytest.raises(ValidationError):
        build_bar(high=469.0)

    with pytest.raises(ValidationError):
        build_bar(low=471.0)


def test_historical_bar_requires_adjustment_mode() -> None:
    data = build_bar().model_dump()
    data.pop("adjustment_mode")

    with pytest.raises(ValidationError):
        HistoricalIntradayBar(**data)


def test_historical_data_source_defaults_to_not_allowed() -> None:
    source = HistoricalIntradayDataSource(
        source_id="local-csv-historical-intraday",
        provider_name="Local CSV Historical Intraday Provider",
        provider_type=HistoricalIntradayProviderType.LOCAL_CSV,
        dataset_id="local_csv_historical_intraday",
        imported_at=datetime(2024, 1, 2, 15, 0),
        row_count=1,
        source_timezone="America/New_York",
        adjustment_mode=HistoricalIntradayAdjustmentMode.UNADJUSTED,
        license_note="Local research sample.",
    )

    assert source.real_money_status == "Not allowed"
    assert source.imported_at.tzinfo is not None


def test_historical_data_source_rejects_real_money_status_change() -> None:
    with pytest.raises(ValidationError):
        HistoricalIntradayDataSource(
            source_id="local-csv-historical-intraday",
            provider_name="Local CSV Historical Intraday Provider",
            provider_type=HistoricalIntradayProviderType.LOCAL_CSV,
            dataset_id="local_csv_historical_intraday",
            imported_at=datetime(2024, 1, 2, 15, 0),
            row_count=1,
            source_timezone="America/New_York",
            adjustment_mode=HistoricalIntradayAdjustmentMode.UNADJUSTED,
            license_note="Local research sample.",
            real_money_status="Allowed",
        )
