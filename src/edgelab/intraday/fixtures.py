"""Local synthetic intraday fixture provider."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from edgelab.intraday.schema import (
    IntradayBar,
    IntradayBarInterval,
    IntradayInstrument,
    IntradayInstrumentType,
    IntradayQualityIssue,
    normalize_symbol,
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
    "session_type",
    "session_id",
    "source",
    "ingested_at",
}

DEFAULT_INSTRUMENTS: dict[str, IntradayInstrument] = {
    "ES_SYN": IntradayInstrument(
        symbol="ES_SYN",
        display_name="Synthetic S&P 500-Style Fixture",
        instrument_type=IntradayInstrumentType.INDEX_FUTURE,
        point_value=50,
        tick_size=0.25,
        tick_value=12.50,
        plain_english_description=(
            "Synthetic S&P 500-style intraday fixture used for local research only."
        ),
    ),
    "NQ_SYN": IntradayInstrument(
        symbol="NQ_SYN",
        display_name="Synthetic Nasdaq-Style Fixture",
        instrument_type=IntradayInstrumentType.INDEX_FUTURE,
        point_value=20,
        tick_size=0.25,
        tick_value=5.00,
        plain_english_description=(
            "Synthetic Nasdaq-style intraday fixture used for local research only."
        ),
    ),
    "GEN_SYN": IntradayInstrument(
        symbol="GEN_SYN",
        display_name="Generic Synthetic Intraday Fixture",
        instrument_type=IntradayInstrumentType.OTHER,
        point_value=1,
        tick_size=0.01,
        tick_value=0.01,
        plain_english_description=(
            "Generic synthetic intraday fixture proving the engine is not tied to ES or NQ."
        ),
    ),
}


class LocalIntradayFixtureProvider:
    """Read-only provider backed by local synthetic intraday CSV fixtures."""

    def __init__(self, fixture_dir: Path | None = None) -> None:
        self.fixture_dir = fixture_dir or _default_fixture_dir()

    def list_available_symbols(self) -> list[str]:
        """Return symbols found dynamically in local fixture files."""

        symbols: set[str] = set()
        for path in self._fixture_paths():
            symbol = _first_row_value(path, "symbol")
            if symbol:
                symbols.add(normalize_symbol(symbol))
        return sorted(symbols)

    def list_available_sessions(self, symbol: str | None = None) -> list[dict[str, str]]:
        """Return available local fixture sessions."""

        normalized_symbol = normalize_symbol(symbol) if symbol is not None else None
        sessions: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for path in self._fixture_paths():
            row_symbol = _first_row_value(path, "symbol")
            session_id = _first_row_value(path, "session_id")
            if not row_symbol or not session_id:
                continue
            fixture_symbol = normalize_symbol(row_symbol)
            if normalized_symbol is not None and fixture_symbol != normalized_symbol:
                continue
            key = (fixture_symbol, session_id)
            if key in seen:
                continue
            seen.add(key)
            sessions.append(
                {
                    "symbol": fixture_symbol,
                    "session_id": session_id,
                    "fixture_file": path.name,
                    "source": "synthetic_intraday_fixture",
                }
            )

        return sorted(sessions, key=lambda session: (session["symbol"], session["session_id"]))

    def list_instruments(self) -> list[IntradayInstrument]:
        """Return instrument metadata for symbols with local fixtures."""

        return [self.get_instrument(symbol) for symbol in self.list_available_symbols()]

    def get_instrument(self, symbol: str) -> IntradayInstrument:
        """Return metadata for a fixture-backed symbol."""

        normalized_symbol = normalize_symbol(symbol)
        if normalized_symbol in DEFAULT_INSTRUMENTS:
            return DEFAULT_INSTRUMENTS[normalized_symbol]
        return IntradayInstrument(
            symbol=normalized_symbol,
            display_name=f"{normalized_symbol} Synthetic Intraday Fixture",
            instrument_type=IntradayInstrumentType.OTHER,
            point_value=1,
            tick_size=0.01,
            tick_value=0.01,
            plain_english_description=(
                "Generic synthetic intraday fixture with placeholder movement assumptions."
            ),
        )

    def load_bars(
        self, symbol: str, session_id: str | None = None
    ) -> tuple[list[IntradayBar], list[IntradayQualityIssue]]:
        """Load local CSV bars for a symbol and optional session."""

        normalized_symbol = normalize_symbol(symbol)
        sessions = self.list_available_sessions(normalized_symbol)
        if not sessions:
            return [], [
                IntradayQualityIssue(
                    code="missing_symbol",
                    message=f"No local intraday fixture found for symbol {normalized_symbol}",
                    symbol=normalized_symbol,
                )
            ]

        selected_session_id = session_id or sessions[0]["session_id"]
        matching_files = [
            self.fixture_dir / session["fixture_file"]
            for session in sessions
            if session["session_id"] == selected_session_id
        ]
        if not matching_files:
            return [], [
                IntradayQualityIssue(
                    code="missing_session",
                    message=(
                        f"No local intraday fixture found for {normalized_symbol} "
                        f"session {selected_session_id}"
                    ),
                    symbol=normalized_symbol,
                    session_id=selected_session_id,
                )
            ]

        bars: list[IntradayBar] = []
        issues: list[IntradayQualityIssue] = []
        for path in matching_files:
            file_bars, file_issues = self._load_file(path, normalized_symbol, selected_session_id)
            bars.extend(file_bars)
            issues.extend(file_issues)

        issues.extend(self.validate_bars(bars))
        bars = sorted(bars, key=lambda bar: bar.timestamp)
        if not bars:
            issues.append(
                IntradayQualityIssue(
                    code="empty_dataset",
                    message="No valid intraday bars were loaded",
                    symbol=normalized_symbol,
                    session_id=selected_session_id,
                )
            )
        return bars, issues

    def validate_bars(self, bars: list[IntradayBar]) -> list[IntradayQualityIssue]:
        """Validate duplicate keys and timestamp ordering."""

        if not bars:
            return []

        issues: list[IntradayQualityIssue] = []
        seen: set[tuple[str, str, datetime, IntradayBarInterval]] = set()
        previous_by_symbol_session: dict[tuple[str, str], datetime] = {}

        for index, bar in enumerate(bars, start=1):
            key = (bar.symbol, bar.session_id, bar.timestamp, bar.interval)
            if key in seen:
                issues.append(
                    IntradayQualityIssue(
                        code="duplicate_bar",
                        message="Duplicate symbol/session/timestamp/interval row",
                        symbol=bar.symbol,
                        session_id=bar.session_id,
                        timestamp=bar.timestamp,
                        row_number=index,
                    )
                )
            seen.add(key)

            order_key = (bar.symbol, bar.session_id)
            previous_timestamp = previous_by_symbol_session.get(order_key)
            if previous_timestamp is not None and bar.timestamp < previous_timestamp:
                issues.append(
                    IntradayQualityIssue(
                        code="unsorted_timestamps",
                        message="Timestamps are not sorted ascending",
                        symbol=bar.symbol,
                        session_id=bar.session_id,
                        timestamp=bar.timestamp,
                        row_number=index,
                    )
                )
            previous_by_symbol_session[order_key] = bar.timestamp

        return issues

    def _fixture_paths(self) -> list[Path]:
        if not self.fixture_dir.exists():
            return []
        return sorted(self.fixture_dir.glob("*.csv"))

    def _load_file(
        self, path: Path, symbol: str, session_id: str
    ) -> tuple[list[IntradayBar], list[IntradayQualityIssue]]:
        bars: list[IntradayBar] = []
        issues: list[IntradayQualityIssue] = []

        with path.open(newline="", encoding="utf-8") as fixture:
            reader = csv.DictReader(fixture)
            missing_columns = sorted(REQUIRED_COLUMNS - set(reader.fieldnames or []))
            if missing_columns:
                return [], [
                    IntradayQualityIssue(
                        code="missing_required_fields",
                        message=f"Missing required columns: {', '.join(missing_columns)}",
                        symbol=symbol,
                        session_id=session_id,
                    )
                ]

            for row_number, row in enumerate(reader, start=2):
                row_issues = _row_missing_field_issues(row, row_number, symbol, session_id)
                if row_issues:
                    issues.extend(row_issues)
                    continue
                if normalize_symbol(str(row["symbol"])) != symbol:
                    continue
                if row["session_id"] != session_id:
                    continue

                try:
                    bars.append(_bar_from_row(row))
                except (ValueError, ValidationError) as error:
                    issues.append(
                        IntradayQualityIssue(
                            code="invalid_bar",
                            message=str(error),
                            symbol=symbol,
                            session_id=session_id,
                            row_number=row_number,
                        )
                    )

        return bars, issues


def _default_fixture_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "intraday"


def _first_row_value(path: Path, column: str) -> str | None:
    with path.open(newline="", encoding="utf-8") as fixture:
        reader = csv.DictReader(fixture)
        try:
            row = next(reader)
        except StopIteration:
            return None
        value = row.get(column)
        return value.strip() if value else None


def _row_missing_field_issues(
    row: dict[str, str | None], row_number: int, symbol: str, session_id: str
) -> list[IntradayQualityIssue]:
    issues: list[IntradayQualityIssue] = []
    for column in sorted(REQUIRED_COLUMNS):
        value = row.get(column)
        if value is None or value == "":
            issues.append(
                IntradayQualityIssue(
                    code="missing_required_field",
                    message=f"Missing required field: {column}",
                    symbol=symbol,
                    session_id=session_id,
                    row_number=row_number,
                )
            )
    return issues


def _bar_from_row(row: dict[str, str | None]) -> IntradayBar:
    data: dict[str, Any] = {
        "symbol": row["symbol"],
        "timestamp": row["timestamp"],
        "interval": row["interval"],
        "open": float(row["open"] or 0),
        "high": float(row["high"] or 0),
        "low": float(row["low"] or 0),
        "close": float(row["close"] or 0),
        "volume": int(row["volume"] or 0),
        "session_type": row["session_type"],
        "session_id": row["session_id"],
        "source": row["source"],
        "ingested_at": row["ingested_at"],
    }
    return IntradayBar(**data)
