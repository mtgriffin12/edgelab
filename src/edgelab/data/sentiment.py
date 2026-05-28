"""Local-first sentiment provider interfaces and fixture implementation."""

from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from collections import Counter
from datetime import UTC, datetime
from math import pow
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from edgelab.data.sentiment_schema import (
    SentimentEvent,
    SentimentEventType,
    SentimentLabel,
    SentimentQualityIssue,
    SentimentSnapshot,
    SentimentSourceType,
    SentimentSummary,
)

REQUIRED_COLUMNS = {
    "event_id",
    "symbol",
    "timestamp",
    "source_type",
    "source_name",
    "event_type",
    "headline_or_summary",
    "sentiment_score",
    "sentiment_label",
    "relevance_score",
    "novelty_score",
    "confidence_score",
    "source_weight",
    "mention_count",
    "mention_velocity_zscore",
    "url_reference",
    "ingested_at",
}


class SentimentProvider(ABC):
    """Abstract read-only sentiment provider."""

    @abstractmethod
    def list_available_symbols(self) -> list[str]:
        """Return symbols available from the provider."""

    @abstractmethod
    def load_events(self, symbol: str) -> tuple[list[SentimentEvent], list[SentimentQualityIssue]]:
        """Load sentiment events and quality issues for a symbol."""

    @abstractmethod
    def summarize_symbol(self, symbol: str) -> SentimentSummary:
        """Summarize sentiment events for a symbol."""

    @abstractmethod
    def create_snapshot(
        self, symbol: str, as_of: datetime | None = None, half_life_hours: float = 72.0
    ) -> SentimentSnapshot:
        """Create a ticker-level sentiment snapshot."""

    @abstractmethod
    def validate_events(self, events: list[SentimentEvent]) -> list[SentimentQualityIssue]:
        """Validate loaded sentiment events."""


class LocalFixtureSentimentProvider(SentimentProvider):
    """Read-only provider backed by synthetic local CSV fixture files."""

    def __init__(self, fixture_dir: Path | None = None) -> None:
        self.fixture_dir = fixture_dir or _default_fixture_dir()

    def list_available_symbols(self) -> list[str]:
        """Return symbols with local sentiment fixture files."""

        if not self.fixture_dir.exists():
            return []
        return sorted(path.stem.upper() for path in self.fixture_dir.glob("*.csv"))

    def load_events(self, symbol: str) -> tuple[list[SentimentEvent], list[SentimentQualityIssue]]:
        """Load local CSV sentiment events for a symbol."""

        normalized_symbol = _normalize_symbol(symbol)
        path = self.fixture_dir / f"{normalized_symbol.lower()}.csv"
        if not path.exists():
            return [], [
                SentimentQualityIssue(
                    code="missing_symbol",
                    message=f"No local sentiment fixture found for symbol {normalized_symbol}",
                    symbol=normalized_symbol,
                )
            ]

        events: list[SentimentEvent] = []
        issues: list[SentimentQualityIssue] = []

        with path.open(newline="", encoding="utf-8") as fixture:
            reader = csv.DictReader(fixture)
            missing_columns = sorted(REQUIRED_COLUMNS - set(reader.fieldnames or []))
            if missing_columns:
                return [], [
                    SentimentQualityIssue(
                        code="missing_required_fields",
                        message=f"Missing required columns: {', '.join(missing_columns)}",
                        symbol=normalized_symbol,
                    )
                ]

            for row_number, row in enumerate(reader, start=2):
                row_issues = _row_missing_field_issues(row, row_number)
                row_issues.extend(_row_enum_issues(row, row_number))
                if row_issues:
                    issues.extend(row_issues)
                    continue

                try:
                    events.append(_event_from_row(row))
                except (ValueError, ValidationError) as error:
                    issues.append(
                        SentimentQualityIssue(
                            code=_validation_issue_code(str(error)),
                            message=str(error),
                            symbol=(row.get("symbol") or normalized_symbol).strip().upper(),
                            event_id=(row.get("event_id") or None),
                            row_number=row_number,
                        )
                    )

        issues.extend(self.validate_events(events))
        if not events:
            issues.append(
                SentimentQualityIssue(
                    code="empty_dataset",
                    message="No valid sentiment events were loaded",
                    symbol=normalized_symbol,
                )
            )

        return events, issues

    def summarize_symbol(self, symbol: str) -> SentimentSummary:
        """Build a summary for a local sentiment fixture symbol."""

        events, issues = self.load_events(symbol)
        scores = [event.sentiment_score for event in events]
        confidences = [event.confidence_score for event in events]
        timestamps = [event.timestamp for event in events]

        return SentimentSummary(
            symbol=_normalize_symbol(symbol),
            event_count=len(events),
            start_timestamp=min(timestamps) if timestamps else None,
            end_timestamp=max(timestamps) if timestamps else None,
            source_types=sorted({event.source_type for event in events}, key=str),
            event_types=sorted({event.event_type for event in events}, key=str),
            average_sentiment_score=_average(scores),
            average_confidence=_average(confidences),
            quality_issue_count=len(issues),
        )

    def create_snapshot(
        self, symbol: str, as_of: datetime | None = None, half_life_hours: float = 72.0
    ) -> SentimentSnapshot:
        """Create a ticker-level descriptive sentiment snapshot."""

        events, issues = self.load_events(symbol)
        normalized_symbol = _normalize_symbol(symbol)
        snapshot_as_of = as_of or _latest_timestamp(events) or datetime.now(UTC)
        usable_events = [event for event in events if event.timestamp <= snapshot_as_of]

        if not usable_events:
            return SentimentSnapshot(
                symbol=normalized_symbol,
                as_of=snapshot_as_of,
                event_count=0,
                weighted_sentiment_score=0.0,
                decayed_sentiment_score=0.0,
                dominant_event_type=None,
                average_relevance=None,
                average_confidence=None,
                average_novelty=None,
                mention_count_total=0,
                max_mention_velocity_zscore=None,
                sentiment_label=SentimentLabel.NEUTRAL,
                trade_bias_context="insufficient_data",
                divergence_flags=["insufficient_data"],
                quality_issue_count=len(issues),
            )

        weights = [_event_weight(event) for event in usable_events]
        weighted_score = _weighted_average(
            [event.sentiment_score for event in usable_events], weights
        )
        decayed_scores = [
            recency_decay(event.sentiment_score, event.timestamp, snapshot_as_of, half_life_hours)
            for event in usable_events
        ]
        decayed_score = _weighted_average(decayed_scores, weights)
        sentiment_label = classify_sentiment(decayed_score, usable_events)
        flags = detect_divergence_flags(usable_events)
        context = _trade_bias_context(sentiment_label, flags, len(usable_events))

        return SentimentSnapshot(
            symbol=normalized_symbol,
            as_of=snapshot_as_of,
            event_count=len(usable_events),
            weighted_sentiment_score=round(weighted_score, 6),
            decayed_sentiment_score=round(decayed_score, 6),
            dominant_event_type=_dominant_event_type(usable_events),
            average_relevance=_average([event.relevance_score for event in usable_events]),
            average_confidence=_average([event.confidence_score for event in usable_events]),
            average_novelty=_average([event.novelty_score for event in usable_events]),
            mention_count_total=sum(event.mention_count or 0 for event in usable_events),
            max_mention_velocity_zscore=_max_optional(
                [event.mention_velocity_zscore for event in usable_events]
            ),
            sentiment_label=sentiment_label,
            trade_bias_context=context,
            divergence_flags=flags,
            quality_issue_count=len(issues),
        )

    def validate_events(self, events: list[SentimentEvent]) -> list[SentimentQualityIssue]:
        """Validate duplicate IDs and timestamp ordering."""

        if not events:
            return [
                SentimentQualityIssue(
                    code="empty_dataset",
                    message="Dataset contains no sentiment events",
                )
            ]

        issues: list[SentimentQualityIssue] = []
        seen_event_ids: set[str] = set()
        previous_by_symbol: dict[str, datetime] = {}

        for index, event in enumerate(events, start=1):
            if event.event_id in seen_event_ids:
                issues.append(
                    SentimentQualityIssue(
                        code="duplicate_event_id",
                        message="Duplicate event_id row",
                        symbol=event.symbol,
                        event_id=event.event_id,
                        timestamp=event.timestamp,
                        row_number=index,
                    )
                )
            seen_event_ids.add(event.event_id)

            previous_timestamp = previous_by_symbol.get(event.symbol)
            if previous_timestamp is not None and event.timestamp < previous_timestamp:
                issues.append(
                    SentimentQualityIssue(
                        code="unsorted_timestamps",
                        message="Timestamps are not sorted ascending",
                        symbol=event.symbol,
                        event_id=event.event_id,
                        timestamp=event.timestamp,
                        row_number=index,
                    )
                )
            previous_by_symbol[event.symbol] = event.timestamp

        return issues


def recency_decay(
    raw_sentiment_score: float,
    event_timestamp: datetime,
    as_of: datetime,
    half_life_hours: float,
    *,
    allow_future_timestamp: bool = False,
) -> float:
    """Decay a sentiment score toward zero using a deterministic half-life."""

    if half_life_hours <= 0:
        raise ValueError("half_life_hours must be positive")

    event_time = _ensure_aware(event_timestamp)
    as_of_time = _ensure_aware(as_of)
    if event_time > as_of_time and not allow_future_timestamp:
        raise ValueError("event timestamp cannot be after as_of")

    age_hours = max((as_of_time - event_time).total_seconds() / 3600, 0.0)
    decay_factor = pow(0.5, age_hours / half_life_hours)
    return raw_sentiment_score * decay_factor


def classify_sentiment(score: float, events: list[SentimentEvent] | None = None) -> SentimentLabel:
    """Classify sentiment score into a descriptive label."""

    if events:
        has_positive = any(event.sentiment_score > 0.25 for event in events)
        has_negative = any(event.sentiment_score < -0.25 for event in events)
        if has_positive and has_negative and abs(score) < 0.25:
            return SentimentLabel.MIXED

    if score >= 0.15:
        return SentimentLabel.BULLISH
    if score <= -0.15:
        return SentimentLabel.BEARISH
    return SentimentLabel.NEUTRAL


def detect_divergence_flags(events: list[SentimentEvent]) -> list[str]:
    """Detect simple deterministic disagreement flags from sentiment fixtures only."""

    flags: list[str] = []
    news_positive = any(
        event.source_type == SentimentSourceType.FINANCIAL_NEWS and event.sentiment_score > 0.25
        for event in events
    )
    news_negative = any(
        event.source_type == SentimentSourceType.FINANCIAL_NEWS and event.sentiment_score < -0.25
        for event in events
    )
    price_volume_negative = any(
        event.source_type == SentimentSourceType.PRICE_VOLUME_IMPLIED
        and event.sentiment_score < -0.25
        for event in events
    )
    price_volume_positive = any(
        event.source_type == SentimentSourceType.PRICE_VOLUME_IMPLIED
        and event.sentiment_score > 0.25
        for event in events
    )
    social_euphoria = any(
        event.event_type == SentimentEventType.SOCIAL_MANIA and event.sentiment_score > 0.5
        for event in events
    )
    broad_risk_off = any(
        event.source_type == SentimentSourceType.MACRO_MARKET and event.sentiment_score < -0.25
        for event in events
    )

    if news_positive and price_volume_negative:
        flags.append("news_positive_price_volume_negative")
    if news_negative and price_volume_positive:
        flags.append("news_negative_price_volume_positive")
    if social_euphoria and not price_volume_positive:
        flags.append("social_euphoria_without_confirmation")
    if broad_risk_off:
        flags.append("broad_risk_off_context")
    if not events:
        flags.append("insufficient_data")

    return flags


def _default_fixture_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "sentiment"


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("symbol must be non-empty")
    return normalized


def _row_missing_field_issues(
    row: dict[str, str | None], row_number: int
) -> list[SentimentQualityIssue]:
    issues: list[SentimentQualityIssue] = []
    for column in sorted(REQUIRED_COLUMNS):
        value = row.get(column)
        if value is None or value == "":
            if column in {"mention_count", "mention_velocity_zscore", "url_reference"}:
                continue
            issues.append(
                SentimentQualityIssue(
                    code="missing_required_field",
                    message=f"Missing required field: {column}",
                    symbol=(row.get("symbol") or "").strip().upper() or None,
                    event_id=row.get("event_id") or None,
                    row_number=row_number,
                )
            )
    return issues


def _row_enum_issues(row: dict[str, str | None], row_number: int) -> list[SentimentQualityIssue]:
    issues: list[SentimentQualityIssue] = []
    source_type = row.get("source_type") or ""
    event_type = row.get("event_type") or ""
    if source_type and source_type not in {item.value for item in SentimentSourceType}:
        issues.append(
            SentimentQualityIssue(
                code="unknown_source_type",
                message=f"Unknown source_type: {source_type}",
                symbol=(row.get("symbol") or "").strip().upper() or None,
                event_id=row.get("event_id") or None,
                row_number=row_number,
            )
        )
    if event_type and event_type not in {item.value for item in SentimentEventType}:
        issues.append(
            SentimentQualityIssue(
                code="unknown_event_type",
                message=f"Unknown event_type: {event_type}",
                symbol=(row.get("symbol") or "").strip().upper() or None,
                event_id=row.get("event_id") or None,
                row_number=row_number,
            )
        )
    return issues


def _event_from_row(row: dict[str, str | None]) -> SentimentEvent:
    mention_count = row["mention_count"]
    mention_velocity = row["mention_velocity_zscore"]
    data: dict[str, Any] = {
        "event_id": row["event_id"],
        "symbol": row["symbol"],
        "timestamp": row["timestamp"],
        "source_type": row["source_type"],
        "source_name": row["source_name"],
        "event_type": row["event_type"],
        "headline_or_summary": row["headline_or_summary"],
        "sentiment_score": float(row["sentiment_score"] or 0),
        "sentiment_label": row["sentiment_label"],
        "relevance_score": float(row["relevance_score"] or 0),
        "novelty_score": float(row["novelty_score"] or 0),
        "confidence_score": float(row["confidence_score"] or 0),
        "source_weight": float(row["source_weight"] or 0),
        "mention_count": int(mention_count) if mention_count else None,
        "mention_velocity_zscore": float(mention_velocity) if mention_velocity else None,
        "url_reference": row["url_reference"] or None,
        "ingested_at": row["ingested_at"],
    }
    return SentimentEvent(**data)


def _validation_issue_code(error_text: str) -> str:
    if "timestamp cannot be in the future" in error_text:
        return "future_timestamp"
    if "greater than or equal" in error_text or "less than or equal" in error_text:
        return "invalid_score_range"
    return "invalid_event"


def _ensure_aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _event_weight(event: SentimentEvent) -> float:
    return event.relevance_score * event.confidence_score * event.source_weight


def _weighted_average(values: list[float], weights: list[float]) -> float:
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    return sum(value * weight for value, weight in zip(values, weights, strict=True)) / total_weight


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _max_optional(values: list[float | None]) -> float | None:
    present_values = [value for value in values if value is not None]
    return max(present_values) if present_values else None


def _latest_timestamp(events: list[SentimentEvent]) -> datetime | None:
    if not events:
        return None
    return max(event.timestamp for event in events)


def _dominant_event_type(events: list[SentimentEvent]) -> SentimentEventType | None:
    if not events:
        return None
    return Counter(event.event_type for event in events).most_common(1)[0][0]


def _trade_bias_context(label: SentimentLabel, flags: list[str], event_count: int) -> str:
    if event_count == 0:
        return "insufficient_data"
    if "social_euphoria_without_confirmation" in flags:
        return "crowding_risk"
    if label == SentimentLabel.BULLISH:
        return "bullish_context"
    if label == SentimentLabel.BEARISH:
        return "bearish_context"
    if label == SentimentLabel.MIXED:
        return "mixed_context"
    return "neutral_context"
