"""Local-first market data provider interfaces and fixture implementation."""

from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from edgelab.data.schema import (
    BarInterval,
    MarketDataQualityIssue,
    MarketDataSet,
    MarketDataSummary,
    OHLCVBar,
)

REQUIRED_COLUMNS = {
    "symbol",
    "timestamp",
    "interval",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "adjusted_close",
    "source",
}


class MarketDataProvider(ABC):
    """Abstract read-only market data provider."""

    @abstractmethod
    def list_available_symbols(self) -> list[str]:
        """Return symbols available from the provider."""

    @abstractmethod
    def load_bars(self, symbol: str) -> MarketDataSet:
        """Load bars for a symbol."""

    @abstractmethod
    def summarize_symbol(self, symbol: str) -> MarketDataSummary:
        """Summarize bars for a symbol."""

    @abstractmethod
    def validate_bars(self, bars: list[OHLCVBar]) -> list[MarketDataQualityIssue]:
        """Validate loaded bars."""


class LocalFixtureMarketDataProvider(MarketDataProvider):
    """Read-only provider backed by synthetic local CSV fixture files."""

    def __init__(self, fixture_dir: Path | None = None) -> None:
        self.fixture_dir = fixture_dir or _default_fixture_dir()

    def list_available_symbols(self) -> list[str]:
        """Return symbols with local fixture files."""

        if not self.fixture_dir.exists():
            return []

        return sorted(path.stem.upper() for path in self.fixture_dir.glob("*.csv"))

    def load_bars(self, symbol: str) -> MarketDataSet:
        """Load local CSV bars for a symbol and return structured quality issues."""

        normalized_symbol = _normalize_symbol(symbol)
        path = self.fixture_dir / f"{normalized_symbol.lower()}.csv"
        if not path.exists():
            return MarketDataSet(
                symbol=normalized_symbol,
                quality_issues=[
                    MarketDataQualityIssue(
                        code="missing_symbol",
                        message=f"No local fixture found for symbol {normalized_symbol}",
                        symbol=normalized_symbol,
                    )
                ],
            )

        bars: list[OHLCVBar] = []
        issues: list[MarketDataQualityIssue] = []
        ingested_at = datetime.now(UTC)

        with path.open(newline="", encoding="utf-8") as fixture:
            reader = csv.DictReader(fixture)
            missing_columns = sorted(REQUIRED_COLUMNS - set(reader.fieldnames or []))
            if missing_columns:
                return MarketDataSet(
                    symbol=normalized_symbol,
                    quality_issues=[
                        MarketDataQualityIssue(
                            code="missing_required_fields",
                            message=f"Missing required columns: {', '.join(missing_columns)}",
                            symbol=normalized_symbol,
                        )
                    ],
                )

            for row_number, row in enumerate(reader, start=2):
                row_issues = _row_missing_field_issues(row, row_number)
                if row_issues:
                    issues.extend(row_issues)
                    continue

                try:
                    bars.append(_bar_from_row(row, ingested_at))
                except (ValueError, ValidationError) as error:
                    issues.append(
                        MarketDataQualityIssue(
                            code="invalid_bar",
                            message=str(error),
                            symbol=(row.get("symbol") or normalized_symbol).strip().upper(),
                            row_number=row_number,
                        )
                    )

        issues.extend(self.validate_bars(bars))
        if not bars:
            issues.append(
                MarketDataQualityIssue(
                    code="empty_dataset",
                    message="No valid bars were loaded",
                    symbol=normalized_symbol,
                )
            )

        return MarketDataSet(symbol=normalized_symbol, bars=bars, quality_issues=issues)

    def summarize_symbol(self, symbol: str) -> MarketDataSummary:
        """Build a summary for a local fixture symbol."""

        data = self.load_bars(symbol)
        bars = data.bars
        closes = [bar.close for bar in bars]
        timestamps = [bar.timestamp for bar in bars]
        intervals = {bar.interval for bar in bars}

        return MarketDataSummary(
            symbol=data.symbol,
            row_count=len(bars),
            start_timestamp=min(timestamps) if timestamps else None,
            end_timestamp=max(timestamps) if timestamps else None,
            interval=next(iter(intervals)) if len(intervals) == 1 else None,
            min_close=min(closes) if closes else None,
            max_close=max(closes) if closes else None,
            total_volume=sum(bar.volume for bar in bars),
            quality_issue_count=len(data.quality_issues),
        )

    def validate_bars(self, bars: list[OHLCVBar]) -> list[MarketDataQualityIssue]:
        """Validate duplicate keys and timestamp ordering."""

        issues: list[MarketDataQualityIssue] = []
        if not bars:
            return [
                MarketDataQualityIssue(
                    code="empty_dataset",
                    message="Dataset contains no bars",
                )
            ]

        seen: set[tuple[str, datetime, BarInterval]] = set()
        previous_by_symbol_interval: dict[tuple[str, BarInterval], datetime] = {}

        for index, bar in enumerate(bars, start=1):
            key = (bar.symbol, bar.timestamp, bar.interval)
            if key in seen:
                issues.append(
                    MarketDataQualityIssue(
                        code="duplicate_bar",
                        message="Duplicate symbol/timestamp/interval row",
                        symbol=bar.symbol,
                        timestamp=bar.timestamp,
                        interval=bar.interval,
                        row_number=index,
                    )
                )
            seen.add(key)

            order_key = (bar.symbol, bar.interval)
            previous_timestamp = previous_by_symbol_interval.get(order_key)
            if previous_timestamp is not None and bar.timestamp < previous_timestamp:
                issues.append(
                    MarketDataQualityIssue(
                        code="unsorted_timestamps",
                        message="Timestamps are not sorted ascending",
                        symbol=bar.symbol,
                        timestamp=bar.timestamp,
                        interval=bar.interval,
                        row_number=index,
                    )
                )
            previous_by_symbol_interval[order_key] = bar.timestamp

        return issues


def _default_fixture_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "market_data"


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("symbol must be non-empty")
    return normalized


def _row_missing_field_issues(
    row: dict[str, str | None], row_number: int
) -> list[MarketDataQualityIssue]:
    issues: list[MarketDataQualityIssue] = []
    for column in sorted(REQUIRED_COLUMNS):
        value = row.get(column)
        if value is None or value == "":
            issues.append(
                MarketDataQualityIssue(
                    code="missing_required_field",
                    message=f"Missing required field: {column}",
                    symbol=(row.get("symbol") or "").strip().upper() or None,
                    row_number=row_number,
                )
            )
    return issues


def _bar_from_row(row: dict[str, str | None], ingested_at: datetime) -> OHLCVBar:
    adjusted_close = row["adjusted_close"]
    data: dict[str, Any] = {
        "symbol": row["symbol"],
        "timestamp": row["timestamp"],
        "interval": row["interval"],
        "open": float(row["open"] or 0),
        "high": float(row["high"] or 0),
        "low": float(row["low"] or 0),
        "close": float(row["close"] or 0),
        "volume": int(row["volume"] or 0),
        "adjusted_close": float(adjusted_close) if adjusted_close else None,
        "source": row["source"],
        "ingested_at": ingested_at,
    }
    return OHLCVBar(**data)
