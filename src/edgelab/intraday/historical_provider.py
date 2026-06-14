"""Vendor-neutral historical intraday providers."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import ValidationError

from edgelab.intraday.historical_schema import (
    HistoricalIntradayAdjustmentMode,
    HistoricalIntradayBar,
    HistoricalIntradayDataSource,
    HistoricalIntradayImportResult,
    HistoricalIntradayInstrument,
    HistoricalIntradayProviderCapabilities,
    HistoricalIntradayProviderType,
    HistoricalIntradayQualityIssue,
    HistoricalIntradayReadiness,
    HistoricalIntradaySession,
    utc_now,
)
from edgelab.intraday.schema import (
    IntradayBarInterval,
    IntradayInstrumentType,
    IntradaySessionType,
    normalize_symbol,
)

REQUIRED_COLUMNS = {
    "symbol",
    "raw_timestamp",
    "source_timezone",
    "interval",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "session_type",
    "session_id",
    "provider",
    "dataset_id",
    "adjustment_mode",
}

OPTIONAL_COLUMNS = {
    "display_name",
    "point_value",
    "tick_size",
    "tick_value",
    "exchange_or_venue",
    "regular_session_open",
    "regular_session_close",
}

DEFAULT_LICENSE_NOTE = (
    "Local CSV import for EdgeLab research only. Do not commit real downloaded market data."
)


class HistoricalIntradayDataProvider(Protocol):
    """Protocol for historical intraday data providers."""

    def provider_capabilities(self) -> HistoricalIntradayProviderCapabilities:
        """Return provider capabilities."""
        ...

    def list_symbols(self) -> list[str]:
        """Return symbols available from the provider."""
        ...

    def list_sessions(
        self,
        symbol: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[HistoricalIntradaySession]:
        """Return sessions available from the provider."""
        ...

    def load_session(self, symbol: str, session_id: str) -> HistoricalIntradayImportResult:
        """Load one historical session."""
        ...

    def load_all_sessions(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> HistoricalIntradayImportResult:
        """Load all historical sessions."""
        ...

    def load_sessions(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> HistoricalIntradayImportResult:
        """Load historical sessions for a symbol."""
        ...

    def get_instrument(self, symbol: str) -> HistoricalIntradayInstrument | None:
        """Return instrument metadata for a symbol."""
        ...


class LocalCSVHistoricalIntradayProvider:
    """Read-only historical intraday provider backed by local CSV files."""

    provider_name = "Local CSV Historical Intraday Provider"

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or _default_historical_fixture_dir()

    def provider_capabilities(self) -> HistoricalIntradayProviderCapabilities:
        """Return local CSV provider capabilities."""

        return HistoricalIntradayProviderCapabilities(
            provider_name=self.provider_name,
            provider_type=HistoricalIntradayProviderType.LOCAL_CSV,
            supports_local_files=True,
            supports_external_calls=False,
            requires_credentials=False,
            supported_intervals=[IntradayBarInterval.ONE_MINUTE],
            supported_adjustment_modes=list(HistoricalIntradayAdjustmentMode),
            supports_dynamic_symbols=True,
            plain_english_summary=(
                "Loads local historical intraday CSV files only. It does not call vendors, "
                "fetch live data, or require credentials."
            ),
        )

    def list_symbols(self) -> list[str]:
        """Return symbols found in valid local CSV rows."""

        result = self._load()
        return sorted({bar.symbol for bar in result.bars})

    def list_sessions(
        self,
        symbol: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[HistoricalIntradaySession]:
        """Return historical sessions found in local CSV rows."""

        result = self._load(symbol=symbol, start_date=start_date, end_date=end_date)
        return result.sessions

    def load_session(self, symbol: str, session_id: str) -> HistoricalIntradayImportResult:
        """Load one local historical intraday session."""

        return self._load(symbol=symbol, session_id=session_id)

    def load_all_sessions(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> HistoricalIntradayImportResult:
        """Load all local historical intraday sessions."""

        return self._load(start_date=start_date, end_date=end_date)

    def load_sessions(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> HistoricalIntradayImportResult:
        """Load local historical intraday sessions for one symbol."""

        return self._load(symbol=symbol, start_date=start_date, end_date=end_date)

    def get_instrument(self, symbol: str) -> HistoricalIntradayInstrument | None:
        """Return instrument metadata for a symbol if local data exists."""

        normalized_symbol = normalize_symbol(symbol)
        result = self._load(symbol=normalized_symbol)
        for instrument in result.instruments:
            if instrument.symbol == normalized_symbol:
                return instrument
        return None

    def _load(
        self,
        symbol: str | None = None,
        session_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> HistoricalIntradayImportResult:
        imported_at = utc_now()
        normalized_symbol = normalize_symbol(symbol) if symbol is not None else None
        bars: list[HistoricalIntradayBar] = []
        issues: list[HistoricalIntradayQualityIssue] = []
        instruments: dict[str, HistoricalIntradayInstrument] = {}
        source_timezones: set[str] = set()
        adjustment_modes: set[HistoricalIntradayAdjustmentMode] = set()
        row_count = 0

        paths = self._csv_paths()
        if not paths:
            issues.append(
                HistoricalIntradayQualityIssue(
                    code="missing_local_csv_files",
                    message="No local historical intraday CSV files were found.",
                )
            )

        for path in paths:
            file_result = self._load_file(path, imported_at)
            row_count += file_result.row_count
            bars.extend(file_result.bars)
            issues.extend(file_result.issues)
            instruments.update(file_result.instruments)
            source_timezones.update(file_result.source_timezones)
            adjustment_modes.update(file_result.adjustment_modes)

        issues.extend(_validate_bars(bars))
        bars = sorted(bars, key=lambda bar: (bar.symbol, bar.session_id, bar.timestamp_utc))
        bars = _filter_bars(bars, normalized_symbol, session_id, start_date, end_date)
        session_keys = {(bar.symbol, bar.session_id) for bar in bars}
        filtered_issues = [
            issue
            for issue in issues
            if _issue_matches_filter(issue, normalized_symbol, session_id, session_keys)
        ]
        sessions = _build_sessions(bars, filtered_issues)
        filtered_instruments = [
            instrument
            for symbol_key, instrument in sorted(instruments.items())
            if symbol_key in {bar.symbol for bar in bars}
        ]
        source = HistoricalIntradayDataSource(
            source_id="local-csv-historical-intraday",
            provider_name=self.provider_name,
            provider_type=HistoricalIntradayProviderType.LOCAL_CSV,
            source_path=str(self.data_dir),
            dataset_id="local_csv_historical_intraday",
            imported_at=imported_at,
            row_count=row_count,
            source_timezone=_one_or_mixed(source_timezones),
            adjustment_mode=_one_or_unknown(adjustment_modes),
            license_note=DEFAULT_LICENSE_NOTE,
        )
        return HistoricalIntradayImportResult(
            source=source,
            instruments=filtered_instruments,
            sessions=sessions,
            bars=bars,
            bars_loaded=len(bars),
            quality_issues=filtered_issues,
            plain_english_summary=_import_summary(sessions, bars, filtered_issues),
        )

    def _csv_paths(self) -> list[Path]:
        if not self.data_dir.exists():
            return []
        return sorted(self.data_dir.glob("*.csv"))

    def _load_file(self, path: Path, imported_at: datetime) -> _FileLoadResult:
        bars: list[HistoricalIntradayBar] = []
        issues: list[HistoricalIntradayQualityIssue] = []
        instruments: dict[str, HistoricalIntradayInstrument] = {}
        source_timezones: set[str] = set()
        adjustment_modes: set[HistoricalIntradayAdjustmentMode] = set()
        row_count = 0

        with path.open(newline="", encoding="utf-8") as fixture:
            reader = csv.DictReader(fixture)
            missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames or [])
            if missing_columns:
                rows = list(reader)
                row_count = len(rows)
                issues.append(
                    HistoricalIntradayQualityIssue(
                        code="missing_required_columns",
                        message=(
                            f"{path.name} is missing required column(s): "
                            f"{', '.join(sorted(missing_columns))}."
                        ),
                        severity="error",
                    )
                )
                return _FileLoadResult(
                    bars=bars,
                    issues=issues,
                    instruments=instruments,
                    source_timezones=source_timezones,
                    adjustment_modes=adjustment_modes,
                    row_count=row_count,
                )

            for row_number, row in enumerate(reader, start=2):
                row_count += 1
                parsed = _parse_row(row, row_number, path.name, imported_at)
                if parsed.issue is not None:
                    issues.append(parsed.issue)
                    continue
                if parsed.bar is None:
                    continue
                bars.append(parsed.bar)
                source_timezones.add(parsed.bar.source_timezone)
                adjustment_modes.add(parsed.bar.adjustment_mode)
                if parsed.bar.adjustment_mode == HistoricalIntradayAdjustmentMode.UNKNOWN:
                    issues.append(
                        HistoricalIntradayQualityIssue(
                            code="adjustment_mode_unknown",
                            message="Adjustment mode is unknown and needs review.",
                            symbol=parsed.bar.symbol,
                            session_id=parsed.bar.session_id,
                            row_number=row_number,
                            timestamp_utc=parsed.bar.timestamp_utc,
                        )
                    )
                if parsed.bar.interval != IntradayBarInterval.ONE_MINUTE:
                    issues.append(
                        HistoricalIntradayQualityIssue(
                            code="unsupported_interval",
                            message=(
                                "Only one-minute historical bars are replay-ready in this phase."
                            ),
                            symbol=parsed.bar.symbol,
                            session_id=parsed.bar.session_id,
                            row_number=row_number,
                            timestamp_utc=parsed.bar.timestamp_utc,
                        )
                    )
                instruments.setdefault(parsed.bar.symbol, _instrument_from_row(row, parsed.bar))

        return _FileLoadResult(
            bars=bars,
            issues=issues,
            instruments=instruments,
            source_timezones=source_timezones,
            adjustment_modes=adjustment_modes,
            row_count=row_count,
        )


class FuturePaidHistoricalProvider:
    """Placeholder for future paid historical data providers."""

    provider_name = "Future Paid Historical Provider Placeholder"

    def provider_capabilities(self) -> HistoricalIntradayProviderCapabilities:
        """Return placeholder capabilities without making external calls."""

        return HistoricalIntradayProviderCapabilities(
            provider_name=self.provider_name,
            provider_type=HistoricalIntradayProviderType.FUTURE_PAID_PROVIDER_PLACEHOLDER,
            supports_local_files=False,
            supports_external_calls=False,
            requires_credentials=True,
            supported_intervals=[IntradayBarInterval.ONE_MINUTE],
            supported_adjustment_modes=list(HistoricalIntradayAdjustmentMode),
            supports_dynamic_symbols=False,
            plain_english_summary=(
                "Future paid providers are not configured. This placeholder makes no external "
                "calls and stores no credentials."
            ),
        )

    def list_symbols(self) -> list[str]:
        """Return no symbols because the placeholder is not configured."""

        return []

    def list_sessions(
        self,
        symbol: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[HistoricalIntradaySession]:
        """Return no sessions because the placeholder is not configured."""

        _ = (symbol, start_date, end_date)
        return []

    def load_session(self, symbol: str, session_id: str) -> HistoricalIntradayImportResult:
        """Reject loading because no paid provider is configured."""

        _ = (symbol, session_id)
        raise RuntimeError("Future paid historical providers are not configured.")

    def load_all_sessions(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> HistoricalIntradayImportResult:
        """Reject loading because no paid provider is configured."""

        _ = (start_date, end_date)
        raise RuntimeError("Future paid historical providers are not configured.")

    def load_sessions(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> HistoricalIntradayImportResult:
        """Reject loading because no paid provider is configured."""

        _ = (symbol, start_date, end_date)
        raise RuntimeError("Future paid historical providers are not configured.")

    def get_instrument(self, symbol: str) -> HistoricalIntradayInstrument | None:
        """Return no instrument because the placeholder is not configured."""

        _ = symbol
        return None


class _FileLoadResult:
    def __init__(
        self,
        *,
        bars: list[HistoricalIntradayBar],
        issues: list[HistoricalIntradayQualityIssue],
        instruments: dict[str, HistoricalIntradayInstrument],
        source_timezones: set[str],
        adjustment_modes: set[HistoricalIntradayAdjustmentMode],
        row_count: int,
    ) -> None:
        self.bars = bars
        self.issues = issues
        self.instruments = instruments
        self.source_timezones = source_timezones
        self.adjustment_modes = adjustment_modes
        self.row_count = row_count


class _ParsedRow:
    def __init__(
        self,
        *,
        bar: HistoricalIntradayBar | None = None,
        issue: HistoricalIntradayQualityIssue | None = None,
    ) -> None:
        self.bar = bar
        self.issue = issue


def _parse_row(
    row: dict[str, str], row_number: int, path_name: str, imported_at: datetime
) -> _ParsedRow:
    missing_values = [column for column in REQUIRED_COLUMNS if not (row.get(column) or "").strip()]
    symbol = row.get("symbol") or None
    session_id = row.get("session_id") or None
    if missing_values:
        return _ParsedRow(
            issue=HistoricalIntradayQualityIssue(
                code="missing_required_value",
                message=(
                    f"{path_name} row {row_number} has blank required value(s): "
                    f"{', '.join(sorted(missing_values))}."
                ),
                severity="error",
                symbol=symbol,
                session_id=session_id,
                row_number=row_number,
            )
        )

    timestamp_utc, timestamp_issue = _parse_timestamp(
        row["raw_timestamp"], row["source_timezone"], row_number, symbol, session_id
    )
    if timestamp_issue is not None:
        return _ParsedRow(issue=timestamp_issue)

    try:
        bar = HistoricalIntradayBar(
            symbol=row["symbol"],
            timestamp_utc=timestamp_utc,
            raw_timestamp=row["raw_timestamp"],
            source_timezone=row["source_timezone"],
            interval=IntradayBarInterval(row["interval"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row["volume"]),
            session_type=IntradaySessionType(row["session_type"]),
            session_id=row["session_id"],
            provider=row["provider"],
            dataset_id=row["dataset_id"],
            adjustment_mode=HistoricalIntradayAdjustmentMode(row["adjustment_mode"]),
            ingested_at=imported_at,
        )
    except (ValueError, ValidationError) as error:
        return _ParsedRow(
            issue=HistoricalIntradayQualityIssue(
                code=_invalid_row_code(error),
                message=f"{path_name} row {row_number} could not be imported: {error}",
                severity="error",
                symbol=symbol,
                session_id=session_id,
                row_number=row_number,
                timestamp_utc=timestamp_utc,
            )
        )
    return _ParsedRow(bar=bar)


def _parse_timestamp(
    raw_timestamp: str,
    source_timezone: str,
    row_number: int,
    symbol: str | None,
    session_id: str | None,
) -> tuple[datetime, HistoricalIntradayQualityIssue | None]:
    try:
        timezone = ZoneInfo(source_timezone)
    except ZoneInfoNotFoundError:
        return utc_now(), HistoricalIntradayQualityIssue(
            code="invalid_source_timezone",
            message=f"Source timezone {source_timezone!r} is not recognized.",
            severity="error",
            symbol=symbol,
            session_id=session_id,
            row_number=row_number,
        )

    try:
        parsed = datetime.fromisoformat(raw_timestamp)
    except ValueError:
        return utc_now(), HistoricalIntradayQualityIssue(
            code="invalid_timestamp",
            message=f"Raw timestamp {raw_timestamp!r} could not be parsed.",
            severity="error",
            symbol=symbol,
            session_id=session_id,
            row_number=row_number,
        )

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone)
    return parsed.astimezone(ZoneInfo("UTC")), None


def _instrument_from_row(
    row: dict[str, str], bar: HistoricalIntradayBar
) -> HistoricalIntradayInstrument:
    display_name = (row.get("display_name") or bar.symbol).strip()
    point_value = _optional_float(row.get("point_value"), default=1)
    tick_size = _optional_float(row.get("tick_size"), default=0.01)
    tick_value = _optional_float(row.get("tick_value"), default=tick_size)
    regular_open = (row.get("regular_session_open") or "09:30").strip()
    regular_close = (row.get("regular_session_close") or "16:00").strip()
    return HistoricalIntradayInstrument(
        symbol=bar.symbol,
        display_name=display_name,
        instrument_type=_instrument_type_for(bar.symbol),
        point_value=point_value,
        tick_size=tick_size,
        tick_value=tick_value,
        exchange_or_venue=(row.get("exchange_or_venue") or "").strip() or None,
        timezone=bar.source_timezone,
        regular_session_open=regular_open,
        regular_session_close=regular_close,
        plain_english_description=(
            f"{display_name} historical intraday CSV data for local research only."
        ),
    )


def _validate_bars(bars: list[HistoricalIntradayBar]) -> list[HistoricalIntradayQualityIssue]:
    issues: list[HistoricalIntradayQualityIssue] = []
    seen: set[tuple[str, str, datetime, IntradayBarInterval]] = set()
    previous_by_session: dict[tuple[str, str], datetime] = {}
    for index, bar in enumerate(bars, start=1):
        key = (bar.symbol, bar.session_id, bar.timestamp_utc, bar.interval)
        if key in seen:
            issues.append(
                HistoricalIntradayQualityIssue(
                    code="duplicate_bar",
                    message="Duplicate symbol/session/timestamp/interval row.",
                    symbol=bar.symbol,
                    session_id=bar.session_id,
                    row_number=index,
                    timestamp_utc=bar.timestamp_utc,
                )
            )
        seen.add(key)
        session_key = (bar.symbol, bar.session_id)
        previous = previous_by_session.get(session_key)
        if previous is not None and bar.timestamp_utc < previous:
            issues.append(
                HistoricalIntradayQualityIssue(
                    code="unsorted_bars",
                    message="Historical bars are not sorted by timestamp.",
                    symbol=bar.symbol,
                    session_id=bar.session_id,
                    row_number=index,
                    timestamp_utc=bar.timestamp_utc,
                )
            )
        previous_by_session[session_key] = bar.timestamp_utc
    return issues


def _build_sessions(
    bars: list[HistoricalIntradayBar],
    issues: list[HistoricalIntradayQualityIssue],
) -> list[HistoricalIntradaySession]:
    sessions: list[HistoricalIntradaySession] = []
    for symbol, session_id in sorted({(bar.symbol, bar.session_id) for bar in bars}):
        session_bars = [
            bar for bar in bars if bar.symbol == symbol and bar.session_id == session_id
        ]
        session_issues = [
            issue for issue in issues if issue.symbol == symbol and issue.session_id == session_id
        ]
        readiness = _classify_readiness(session_bars, session_issues)
        sessions.append(
            HistoricalIntradaySession(
                session_id=session_id,
                symbol=symbol,
                session_date=session_bars[0].timestamp_utc.date(),
                bar_count=len(session_bars),
                first_bar_timestamp_utc=min(bar.timestamp_utc for bar in session_bars),
                last_bar_timestamp_utc=max(bar.timestamp_utc for bar in session_bars),
                has_premarket=_has_session_type(session_bars, IntradaySessionType.PREMARKET),
                has_regular_first_hour=_has_session_type(
                    session_bars, IntradaySessionType.REGULAR_FIRST_HOUR
                ),
                has_regular_session=_has_session_type(
                    session_bars, IntradaySessionType.REGULAR_SESSION
                ),
                has_overnight=_has_session_type(session_bars, IntradaySessionType.OVERNIGHT),
                readiness=readiness,
                quality_issue_count=len(session_issues),
                plain_english_summary=_readiness_summary(readiness),
            )
        )
    return sessions


def _classify_readiness(
    bars: list[HistoricalIntradayBar], issues: list[HistoricalIntradayQualityIssue]
) -> HistoricalIntradayReadiness:
    if any(issue.severity == "error" for issue in issues):
        return HistoricalIntradayReadiness.UNUSABLE
    first_hour_one_minute = [
        bar
        for bar in bars
        if bar.session_type == IntradaySessionType.REGULAR_FIRST_HOUR
        and bar.interval == IntradayBarInterval.ONE_MINUTE
    ]
    if len(first_hour_one_minute) < 5:
        return HistoricalIntradayReadiness.INCOMPLETE
    review_codes = {
        "duplicate_bar",
        "unsorted_bars",
        "adjustment_mode_unknown",
        "unsupported_interval",
    }
    if any(issue.code in review_codes for issue in issues):
        return HistoricalIntradayReadiness.NEEDS_REVIEW
    return HistoricalIntradayReadiness.READY_FOR_REPLAY


def _filter_bars(
    bars: list[HistoricalIntradayBar],
    symbol: str | None,
    session_id: str | None,
    start_date: date | None,
    end_date: date | None,
) -> list[HistoricalIntradayBar]:
    filtered = bars
    if symbol is not None:
        filtered = [bar for bar in filtered if bar.symbol == symbol]
    if session_id is not None:
        filtered = [bar for bar in filtered if bar.session_id == session_id]
    if start_date is not None:
        filtered = [bar for bar in filtered if bar.timestamp_utc.date() >= start_date]
    if end_date is not None:
        filtered = [bar for bar in filtered if bar.timestamp_utc.date() <= end_date]
    return filtered


def _issue_matches_filter(
    issue: HistoricalIntradayQualityIssue,
    symbol: str | None,
    session_id: str | None,
    session_keys: set[tuple[str, str]],
) -> bool:
    if issue.symbol is None:
        return symbol is None and session_id is None
    if symbol is not None and issue.symbol != symbol:
        return False
    if session_id is not None and issue.session_id != session_id:
        return False
    if session_keys and issue.session_id is not None:
        return (issue.symbol, issue.session_id) in session_keys
    return True


def _has_session_type(
    bars: Iterable[HistoricalIntradayBar], session_type: IntradaySessionType
) -> bool:
    return any(bar.session_type == session_type for bar in bars)


def _readiness_summary(readiness: HistoricalIntradayReadiness) -> str:
    if readiness == HistoricalIntradayReadiness.READY_FOR_REPLAY:
        return "This local historical session has enough first-hour bars for future replay."
    if readiness == HistoricalIntradayReadiness.INCOMPLETE:
        return "This local historical session has some data, but not enough first-hour coverage."
    if readiness == HistoricalIntradayReadiness.UNUSABLE:
        return "This local historical session has critical data problems."
    return "This local historical session needs review before replay."


def _import_summary(
    sessions: list[HistoricalIntradaySession],
    bars: list[HistoricalIntradayBar],
    issues: list[HistoricalIntradayQualityIssue],
) -> str:
    if not sessions:
        return "No local historical intraday sessions are ready to inspect from CSV files."
    ready_count = len(
        [
            session
            for session in sessions
            if session.readiness == HistoricalIntradayReadiness.READY_FOR_REPLAY
        ]
    )
    return (
        f"Loaded {len(sessions)} local historical session(s) and {len(bars)} bar(s). "
        f"{ready_count} session(s) look ready for future replay. "
        f"{len(issues)} data quality issue(s) were reported."
    )


def _invalid_row_code(error: Exception) -> str:
    text = str(error).lower()
    if "high must" in text or "low must" in text or "greater than" in text:
        return "invalid_ohlc"
    return "invalid_row"


def _optional_float(value: str | None, *, default: float) -> float:
    if value is None or not value.strip():
        return default
    return float(value)


def _instrument_type_for(symbol: str) -> IntradayInstrumentType:
    if symbol in {"SPY", "QQQ"}:
        return IntradayInstrumentType.INDEX_ETF_REFERENCE
    return IntradayInstrumentType.OTHER


def _one_or_mixed(values: set[str]) -> str:
    if not values:
        return "unknown"
    if len(values) == 1:
        return next(iter(values))
    return "mixed"


def _one_or_unknown(
    values: set[HistoricalIntradayAdjustmentMode],
) -> HistoricalIntradayAdjustmentMode:
    if len(values) == 1:
        return next(iter(values))
    return HistoricalIntradayAdjustmentMode.UNKNOWN


def _default_historical_fixture_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "historical_intraday"
