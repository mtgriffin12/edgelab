from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from edgelab.data.sentiment_schema import (
    SentimentEvent,
    SentimentEventType,
    SentimentLabel,
    SentimentSourceType,
)


def build_event(**overrides: object) -> SentimentEvent:
    data: dict[str, object] = {
        "event_id": "sent-001",
        "symbol": "spy",
        "timestamp": datetime(2024, 1, 2, 14, 30, tzinfo=UTC),
        "source_type": SentimentSourceType.FINANCIAL_NEWS,
        "source_name": "synthetic_fixture",
        "event_type": SentimentEventType.EARNINGS_BEAT,
        "headline_or_summary": "Synthetic positive event.",
        "sentiment_score": 0.5,
        "sentiment_label": SentimentLabel.BULLISH,
        "relevance_score": 0.8,
        "novelty_score": 0.7,
        "confidence_score": 0.75,
        "source_weight": 0.8,
        "mention_count": 5,
        "mention_velocity_zscore": 1.2,
        "url_reference": None,
        "ingested_at": datetime(2024, 1, 2, 14, 35, tzinfo=UTC),
    }
    data.update(overrides)
    return SentimentEvent(**data)


def test_sentiment_event_normalizes_symbol() -> None:
    event = build_event(symbol=" spy ")

    assert event.symbol == "SPY"


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("event_id", ""),
        ("source_name", ""),
        ("headline_or_summary", ""),
    ],
)
def test_sentiment_event_requires_non_empty_text(field_name: str, value: str) -> None:
    with pytest.raises(ValidationError):
        build_event(**{field_name: value})


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("sentiment_score", 1.5),
        ("sentiment_score", -1.5),
        ("relevance_score", 1.1),
        ("novelty_score", -0.1),
        ("confidence_score", 1.1),
        ("source_weight", -0.1),
        ("mention_count", -1),
    ],
)
def test_sentiment_event_rejects_invalid_score_ranges(field_name: str, value: float) -> None:
    with pytest.raises(ValidationError):
        build_event(**{field_name: value})


def test_sentiment_event_rejects_future_timestamps_by_default() -> None:
    with pytest.raises(ValidationError, match="future"):
        build_event(timestamp=datetime.now(UTC) + timedelta(days=1))


def test_sentiment_event_can_allow_future_timestamps_for_tests() -> None:
    event = build_event(
        timestamp=datetime.now(UTC) + timedelta(days=1),
        allow_future_timestamp=True,
    )

    assert event.allow_future_timestamp is True
