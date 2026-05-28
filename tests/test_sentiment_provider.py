from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from edgelab.data.sentiment import (
    LocalFixtureSentimentProvider,
    classify_sentiment,
    recency_decay,
)
from edgelab.data.sentiment_schema import SentimentLabel


def write_fixture(fixture_dir: Path, symbol: str, rows: list[str]) -> None:
    fixture_dir.mkdir(parents=True, exist_ok=True)
    header = (
        "event_id,symbol,timestamp,source_type,source_name,event_type,"
        "headline_or_summary,sentiment_score,sentiment_label,relevance_score,"
        "novelty_score,confidence_score,source_weight,mention_count,"
        "mention_velocity_zscore,url_reference,ingested_at"
    )
    (fixture_dir / f"{symbol.lower()}.csv").write_text(
        "\n".join([header, *rows]) + "\n",
        encoding="utf-8",
    )


def test_sentiment_provider_lists_available_symbols() -> None:
    provider = LocalFixtureSentimentProvider()

    assert provider.list_available_symbols() == ["AAPL", "QQQ", "SPY"]


def test_sentiment_provider_loads_events() -> None:
    provider = LocalFixtureSentimentProvider()

    events, issues = provider.load_events("spy")

    assert len(events) == 3
    assert events[0].symbol == "SPY"
    assert issues == []


def test_sentiment_provider_reports_missing_symbol() -> None:
    provider = LocalFixtureSentimentProvider()

    events, issues = provider.load_events("missing")

    assert events == []
    assert issues[0].code == "missing_symbol"


def test_sentiment_provider_detects_duplicate_event_id(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "dup",
        [
            "same,DUP,2024-01-02T00:00:00Z,financial_news,synthetic_fixture,"
            "earnings_beat,Synthetic row,0.4,bullish,0.8,0.7,0.8,0.8,5,0.5,,"
            "2024-01-02T00:05:00Z",
            "same,DUP,2024-01-03T00:00:00Z,financial_news,synthetic_fixture,"
            "earnings_beat,Synthetic row,0.3,bullish,0.7,0.6,0.7,0.7,4,0.2,,"
            "2024-01-03T00:05:00Z",
        ],
    )
    provider = LocalFixtureSentimentProvider(tmp_path)

    _, issues = provider.load_events("dup")

    assert any(issue.code == "duplicate_event_id" for issue in issues)


def test_sentiment_provider_detects_unsorted_timestamps(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "sort",
        [
            "sort-2,SORT,2024-01-03T00:00:00Z,financial_news,synthetic_fixture,"
            "earnings_beat,Synthetic row,0.4,bullish,0.8,0.7,0.8,0.8,5,0.5,,"
            "2024-01-03T00:05:00Z",
            "sort-1,SORT,2024-01-02T00:00:00Z,financial_news,synthetic_fixture,"
            "earnings_beat,Synthetic row,0.3,bullish,0.7,0.6,0.7,0.7,4,0.2,,"
            "2024-01-02T00:05:00Z",
        ],
    )
    provider = LocalFixtureSentimentProvider(tmp_path)

    _, issues = provider.load_events("sort")

    assert any(issue.code == "unsorted_timestamps" for issue in issues)


def test_sentiment_provider_detects_unknown_source_and_event_type(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "bad",
        [
            "bad-1,BAD,2024-01-02T00:00:00Z,unknown_source,synthetic_fixture,"
            "unknown_event,Synthetic row,0.4,bullish,0.8,0.7,0.8,0.8,5,0.5,,"
            "2024-01-02T00:05:00Z"
        ],
    )
    provider = LocalFixtureSentimentProvider(tmp_path)

    _, issues = provider.load_events("bad")

    assert any(issue.code == "unknown_source_type" for issue in issues)
    assert any(issue.code == "unknown_event_type" for issue in issues)


def test_sentiment_provider_detects_invalid_score_and_future_timestamp(
    tmp_path: Path,
) -> None:
    future_time = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    write_fixture(
        tmp_path,
        "bad",
        [
            "bad-1,BAD,2024-01-02T00:00:00Z,financial_news,synthetic_fixture,"
            "earnings_beat,Synthetic row,1.4,bullish,0.8,0.7,0.8,0.8,5,0.5,,"
            "2024-01-02T00:05:00Z",
            f"bad-2,BAD,{future_time},financial_news,synthetic_fixture,"
            "earnings_beat,Synthetic row,0.4,bullish,0.8,0.7,0.8,0.8,5,0.5,,"
            "2024-01-02T00:05:00Z",
        ],
    )
    provider = LocalFixtureSentimentProvider(tmp_path)

    _, issues = provider.load_events("bad")

    assert any(issue.code == "invalid_score_range" for issue in issues)
    assert any(issue.code == "future_timestamp" for issue in issues)


def test_recency_decay_preserves_fresh_score_and_decays_old_score() -> None:
    as_of = datetime(2024, 1, 2, 12, tzinfo=UTC)
    fresh = recency_decay(0.8, as_of - timedelta(hours=1), as_of, 24)
    old = recency_decay(0.8, as_of - timedelta(hours=72), as_of, 24)

    assert fresh > 0.75
    assert 0 < old < fresh


def test_negative_sentiment_decays_toward_zero() -> None:
    as_of = datetime(2024, 1, 2, 12, tzinfo=UTC)
    decayed = recency_decay(-0.8, as_of - timedelta(hours=72), as_of, 24)

    assert -0.8 < decayed < 0


def test_recency_decay_rejects_future_event_without_test_override() -> None:
    as_of = datetime(2024, 1, 2, 12, tzinfo=UTC)

    with pytest.raises(ValueError, match="after as_of"):
        recency_decay(0.4, as_of + timedelta(hours=1), as_of, 24)


def test_snapshot_creation_is_descriptive_only() -> None:
    provider = LocalFixtureSentimentProvider()

    snapshot = provider.create_snapshot(
        "qqq",
        as_of=datetime(2024, 1, 4, 14, 30, tzinfo=UTC),
        half_life_hours=72,
    )

    assert snapshot.symbol == "QQQ"
    assert snapshot.event_count == 3
    assert snapshot.sentiment_label in {
        SentimentLabel.BULLISH,
        SentimentLabel.MIXED,
        SentimentLabel.NEUTRAL,
    }
    assert "news_positive_price_volume_negative" in snapshot.divergence_flags
    assert snapshot.trade_bias_context in {
        "bullish_context",
        "mixed_context",
        "neutral_context",
        "crowding_risk",
    }
    forbidden_terms = {"buy", "sell", "short", "trade"}
    assert not any(term in snapshot.trade_bias_context for term in forbidden_terms)


def test_sentiment_label_classification() -> None:
    assert classify_sentiment(0.3) == SentimentLabel.BULLISH
    assert classify_sentiment(-0.3) == SentimentLabel.BEARISH
    assert classify_sentiment(0.0) == SentimentLabel.NEUTRAL


def test_summary_generation() -> None:
    provider = LocalFixtureSentimentProvider()

    summary = provider.summarize_symbol("aapl")

    assert summary.symbol == "AAPL"
    assert summary.event_count == 3
    assert summary.quality_issue_count == 0
    assert summary.average_confidence is not None
