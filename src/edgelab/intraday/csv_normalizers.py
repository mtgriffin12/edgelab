"""CSV normalizers for local historical intraday research files."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Protocol, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

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

FIRSTRATE_REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}
FIRST_RATE_PROVIDER = "firstratedata"
FIRST_RATE_DEFAULT_TIMEZONE = "America/New_York"
FIRST_RATE_DEFAULT_LICENSE_NOTE = (
    "Local FirstRate CSV dry run for EdgeLab research only. Do not commit real downloaded "
    "market data."
)


class HistoricalIntradayCSVNormalizer(Protocol):
    """Protocol for local historical intraday CSV normalizers."""

    def can_normalize(self, path: Path) -> bool:
        """Return whether this normalizer can read a file."""
        ...

    def normalize_file(
        self,
        path: Path,
        *,
        symbol: str | None = None,
        include_bars: bool = False,
        only_session_id: str | None = None,
    ) -> FirstRateFileNormalizationResult:
        """Normalize one local file."""
        ...


class FirstRateDetectedFile(BaseModel):
    """One detected local FirstRate CSV file."""

    path: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    ignored_by_git: bool = True
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @field_validator("symbol")
    @classmethod
    def normalize_detected_symbol(cls, value: str) -> str:
        """Normalize symbols."""

        return normalize_symbol(value)

    @model_validator(mode="after")
    def validate_research_only(self) -> Self:
        """Keep detected-file output conservative."""

        if self.research_only_status != "Research only":
            raise ValueError("detected file output must remain research-only")
        if self.real_money_status != "Not allowed":
            raise ValueError("detected file real-money status must be Not allowed")
        return self


class FirstRateFileDryRunSummary(BaseModel):
    """Dry-run summary for one local FirstRate CSV file."""

    path: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    row_count: int = Field(ge=0)
    session_count: int = Field(ge=0)
    earliest_timestamp_utc: datetime | None = None
    latest_timestamp_utc: datetime | None = None
    start_date: date | None = None
    end_date: date | None = None
    readiness_counts: dict[str, int] = Field(default_factory=dict)
    quality_issue_count: int = Field(ge=0)
    plain_english_summary: str = Field(min_length=1)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @field_validator("symbol")
    @classmethod
    def normalize_file_symbol(cls, value: str) -> str:
        """Normalize symbols."""

        return normalize_symbol(value)

    @field_validator("earliest_timestamp_utc", "latest_timestamp_utc")
    @classmethod
    def normalize_optional_timestamp(cls, value: datetime | None) -> datetime | None:
        """Normalize timestamps to UTC."""

        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_research_only(self) -> Self:
        """Keep dry-run file output conservative."""

        if self.research_only_status != "Research only":
            raise ValueError("dry-run output must remain research-only")
        if self.real_money_status != "Not allowed":
            raise ValueError("dry-run real-money status must be Not allowed")
        return self


class FirstRateDryRunSummary(BaseModel):
    """Dry-run summary for local FirstRate files."""

    data_dir: str = Field(min_length=1)
    files_found: int = Field(ge=0)
    symbols_detected: list[str] = Field(default_factory=list)
    row_count: int = Field(ge=0)
    session_count: int = Field(ge=0)
    earliest_timestamp_utc: datetime | None = None
    latest_timestamp_utc: datetime | None = None
    start_date: date | None = None
    end_date: date | None = None
    readiness_counts: dict[str, int] = Field(default_factory=dict)
    quality_issue_count: int = Field(ge=0)
    files: list[FirstRateFileDryRunSummary] = Field(default_factory=list)
    quality_issues: list[HistoricalIntradayQualityIssue] = Field(default_factory=list)
    plain_english_summary: str = Field(min_length=1)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @field_validator("symbols_detected")
    @classmethod
    def normalize_symbols(cls, values: list[str]) -> list[str]:
        """Normalize detected symbols."""

        return sorted({normalize_symbol(value) for value in values})

    @field_validator("earliest_timestamp_utc", "latest_timestamp_utc")
    @classmethod
    def normalize_optional_timestamp(cls, value: datetime | None) -> datetime | None:
        """Normalize timestamps to UTC."""

        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_research_only(self) -> Self:
        """Keep dry-run output conservative."""

        if self.research_only_status != "Research only":
            raise ValueError("dry-run output must remain research-only")
        if self.real_money_status != "Not allowed":
            raise ValueError("dry-run real-money status must be Not allowed")
        return self


class FirstRateFileNormalizationResult:
    """Internal normalized FirstRate file result."""

    def __init__(
        self,
        *,
        path: Path,
        symbol: str,
        row_count: int,
        bars: list[HistoricalIntradayBar],
        sessions: list[HistoricalIntradaySession],
        issues: list[HistoricalIntradayQualityIssue],
        instrument: HistoricalIntradayInstrument | None,
        source_timezone: str,
        adjustment_mode: HistoricalIntradayAdjustmentMode,
    ) -> None:
        self.path = path
        self.symbol = symbol
        self.row_count = row_count
        self.bars = bars
        self.sessions = sessions
        self.issues = issues
        self.instrument = instrument
        self.source_timezone = source_timezone
        self.adjustment_mode = adjustment_mode


@dataclass(frozen=True)
class FirstRateFileCacheSignature:
    """Process-local cache fingerprint for one ignored local CSV file."""

    path: str
    size_bytes: int
    modified_time_ns: int


class FirstRateHistoricalCSVNormalizer:
    """Normalize FirstRate 1-minute CSV files into EdgeLab historical rows."""

    def __init__(
        self,
        *,
        source_timezone: str = FIRST_RATE_DEFAULT_TIMEZONE,
        interval: IntradayBarInterval = IntradayBarInterval.ONE_MINUTE,
        provider: str = FIRST_RATE_PROVIDER,
        adjustment_mode: HistoricalIntradayAdjustmentMode = (
            HistoricalIntradayAdjustmentMode.UNKNOWN
        ),
    ) -> None:
        self.source_timezone = source_timezone
        self.interval = interval
        self.provider = provider
        self.adjustment_mode = adjustment_mode

    def can_normalize(self, path: Path) -> bool:
        """Return whether the file has the FirstRate header."""

        try:
            with path.open(newline="", encoding="utf-8") as csv_file:
                reader = csv.DictReader(csv_file)
                return set(reader.fieldnames or []) == FIRSTRATE_REQUIRED_COLUMNS
        except OSError:
            return False

    def infer_symbol_from_path(self, path: Path) -> str:
        """Infer a symbol from a FirstRate filename."""

        stem = path.stem
        candidate = stem.split("_", maxsplit=1)[0]
        return normalize_symbol(candidate)

    def normalize_file(
        self,
        path: Path,
        *,
        symbol: str | None = None,
        include_bars: bool = False,
        only_session_id: str | None = None,
    ) -> FirstRateFileNormalizationResult:
        """Normalize one FirstRate CSV file without writing output files."""

        imported_at = utc_now()
        normalized_symbol = (
            normalize_symbol(symbol) if symbol else self.infer_symbol_from_path(path)
        )
        issues: list[HistoricalIntradayQualityIssue] = []
        bars: list[HistoricalIntradayBar] = []
        accumulators: dict[str, _SessionAccumulator] = {}
        seen: set[tuple[str, datetime, IntradayBarInterval]] = set()
        previous_timestamp: datetime | None = None
        row_count = 0

        try:
            source_zone = ZoneInfo(self.source_timezone)
        except ZoneInfoNotFoundError:
            source_zone = ZoneInfo("UTC")
            issues.append(
                HistoricalIntradayQualityIssue(
                    code="invalid_source_timezone",
                    message=(
                        f"Source timezone {self.source_timezone!r} is not recognized for "
                        f"{path.name}."
                    ),
                    severity="error",
                    symbol=normalized_symbol,
                )
            )

        if not path.exists():
            issues.append(
                HistoricalIntradayQualityIssue(
                    code="missing_firstrate_file",
                    message=f"FirstRate CSV file {path.name} was not found.",
                    severity="error",
                    symbol=normalized_symbol,
                )
            )
            return FirstRateFileNormalizationResult(
                path=path,
                symbol=normalized_symbol,
                row_count=0,
                bars=[],
                sessions=[],
                issues=issues,
                instrument=None,
                source_timezone=self.source_timezone,
                adjustment_mode=self.adjustment_mode,
            )

        with path.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            missing_columns = FIRSTRATE_REQUIRED_COLUMNS - set(reader.fieldnames or [])
            if missing_columns:
                for _row in reader:
                    row_count += 1
                issues.append(
                    HistoricalIntradayQualityIssue(
                        code="missing_required_columns",
                        message=(
                            f"{path.name} is missing FirstRate column(s): "
                            f"{', '.join(sorted(missing_columns))}."
                        ),
                        severity="error",
                        symbol=normalized_symbol,
                    )
                )
                return FirstRateFileNormalizationResult(
                    path=path,
                    symbol=normalized_symbol,
                    row_count=row_count,
                    bars=[],
                    sessions=[],
                    issues=issues,
                    instrument=None,
                    source_timezone=self.source_timezone,
                    adjustment_mode=self.adjustment_mode,
                )

            for row_number, row in enumerate(reader, start=2):
                row_count += 1
                parsed = self._parse_row(
                    row=row,
                    row_number=row_number,
                    path_name=path.name,
                    symbol=normalized_symbol,
                    source_zone=source_zone,
                    imported_at=imported_at,
                )
                if parsed.issue is not None:
                    issues.append(parsed.issue)
                    continue
                if parsed.bar is None:
                    continue

                key = (parsed.bar.session_id, parsed.bar.timestamp_utc, parsed.bar.interval)
                if key in seen:
                    issues.append(
                        HistoricalIntradayQualityIssue(
                            code="duplicate_bar",
                            message="Duplicate FirstRate symbol/session/timestamp/interval row.",
                            symbol=parsed.bar.symbol,
                            session_id=parsed.bar.session_id,
                            row_number=row_number,
                            timestamp_utc=parsed.bar.timestamp_utc,
                        )
                    )
                seen.add(key)

                if previous_timestamp is not None and parsed.bar.timestamp_utc < previous_timestamp:
                    issues.append(
                        HistoricalIntradayQualityIssue(
                            code="unsorted_bars",
                            message="FirstRate rows are not sorted by timestamp.",
                            symbol=parsed.bar.symbol,
                            session_id=parsed.bar.session_id,
                            row_number=row_number,
                            timestamp_utc=parsed.bar.timestamp_utc,
                        )
                    )
                previous_timestamp = parsed.bar.timestamp_utc

                accumulator = accumulators.setdefault(
                    parsed.bar.session_id,
                    _SessionAccumulator(
                        symbol=parsed.bar.symbol,
                        session_id=parsed.bar.session_id,
                        session_date=parsed.bar.timestamp_utc.astimezone(source_zone).date(),
                    ),
                )
                accumulator.add_bar(parsed.bar)

                if include_bars and (
                    only_session_id is None or parsed.bar.session_id == only_session_id
                ):
                    bars.append(parsed.bar)

        sessions = _sessions_from_accumulators(accumulators, issues)
        if only_session_id is not None:
            sessions = [session for session in sessions if session.session_id == only_session_id]
            issues = [
                issue
                for issue in issues
                if issue.session_id is None or issue.session_id == only_session_id
            ]
        return FirstRateFileNormalizationResult(
            path=path,
            symbol=normalized_symbol,
            row_count=row_count,
            bars=bars,
            sessions=sessions,
            issues=issues,
            instrument=_instrument_for_symbol(normalized_symbol, self.source_timezone),
            source_timezone=self.source_timezone,
            adjustment_mode=self.adjustment_mode,
        )

    def _parse_row(
        self,
        *,
        row: dict[str, str],
        row_number: int,
        path_name: str,
        symbol: str,
        source_zone: ZoneInfo,
        imported_at: datetime,
    ) -> _ParsedFirstRateRow:
        missing_values = [
            column for column in FIRSTRATE_REQUIRED_COLUMNS if not (row.get(column) or "").strip()
        ]
        if missing_values:
            return _ParsedFirstRateRow(
                issue=HistoricalIntradayQualityIssue(
                    code="missing_required_value",
                    message=(
                        f"{path_name} row {row_number} has blank FirstRate value(s): "
                        f"{', '.join(sorted(missing_values))}."
                    ),
                    severity="error",
                    symbol=symbol,
                    row_number=row_number,
                )
            )

        timestamp_utc, timestamp_issue = _parse_firstrate_timestamp(
            row["timestamp"], source_zone, row_number, symbol
        )
        if timestamp_issue is not None:
            return _ParsedFirstRateRow(issue=timestamp_issue)

        session_type = _session_type_for(timestamp_utc.astimezone(source_zone).time())
        if session_type is None:
            return _ParsedFirstRateRow(
                issue=HistoricalIntradayQualityIssue(
                    code="unsupported_session_time",
                    message=(
                        f"{path_name} row {row_number} is outside the supported local session "
                        "window and was skipped."
                    ),
                    symbol=symbol,
                    row_number=row_number,
                    timestamp_utc=timestamp_utc,
                )
            )

        local_date = timestamp_utc.astimezone(source_zone).date()
        session_id = f"{symbol}-{local_date.isoformat()}"
        try:
            volume = int(row["volume"])
        except ValueError:
            return _ParsedFirstRateRow(
                issue=HistoricalIntradayQualityIssue(
                    code="invalid_volume",
                    message=f"{path_name} row {row_number} has invalid volume.",
                    severity="error",
                    symbol=symbol,
                    session_id=session_id,
                    row_number=row_number,
                    timestamp_utc=timestamp_utc,
                )
            )
        if volume < 0:
            return _ParsedFirstRateRow(
                issue=HistoricalIntradayQualityIssue(
                    code="invalid_volume",
                    message=f"{path_name} row {row_number} has negative volume.",
                    severity="error",
                    symbol=symbol,
                    session_id=session_id,
                    row_number=row_number,
                    timestamp_utc=timestamp_utc,
                )
            )
        try:
            bar = HistoricalIntradayBar(
                symbol=symbol,
                timestamp_utc=timestamp_utc,
                raw_timestamp=row["timestamp"],
                source_timezone=self.source_timezone,
                interval=self.interval,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=volume,
                session_type=session_type,
                session_id=session_id,
                provider=self.provider,
                dataset_id=f"{symbol.lower()}_firstrate_1min",
                adjustment_mode=self.adjustment_mode,
                ingested_at=imported_at,
            )
        except (ValueError, ValidationError) as error:
            return _ParsedFirstRateRow(
                issue=HistoricalIntradayQualityIssue(
                    code=_invalid_firstrate_row_code(error),
                    message=f"{path_name} row {row_number} could not be normalized: {error}",
                    severity="error",
                    symbol=symbol,
                    session_id=session_id,
                    row_number=row_number,
                    timestamp_utc=timestamp_utc,
                )
            )
        return _ParsedFirstRateRow(bar=bar)


class FirstRateLocalCSVHistoricalProvider:
    """Read-only provider for ignored local FirstRate CSV files."""

    provider_name = "FirstRate Local CSV Historical Provider"

    def __init__(
        self,
        data_dir: Path | None = None,
        normalizer: FirstRateHistoricalCSVNormalizer | None = None,
    ) -> None:
        self.data_dir = data_dir or _default_firstrate_data_dir()
        self.normalizer = normalizer or FirstRateHistoricalCSVNormalizer()
        self._normalization_cache: dict[
            tuple[
                tuple[FirstRateFileCacheSignature, ...],
                str | None,
                bool,
                str | None,
            ],
            list[FirstRateFileNormalizationResult],
        ] = {}
        self._dry_run_cache: dict[
            tuple[FirstRateFileCacheSignature, ...], FirstRateDryRunSummary
        ] = {}

    def provider_capabilities(self) -> HistoricalIntradayProviderCapabilities:
        """Return FirstRate local-file capabilities."""

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
                "Reads ignored local FirstRate CSV files for dry-run research only. It does not "
                "call vendors, fetch live data, or require credentials."
            ),
        )

    def detected_files(self) -> list[FirstRateDetectedFile]:
        """Return FirstRate files detected under the ignored raw-data folder."""

        return [
            FirstRateDetectedFile(
                path=str(path),
                filename=path.name,
                symbol=self.normalizer.infer_symbol_from_path(path),
            )
            for path in self._csv_paths()
            if self.normalizer.can_normalize(path)
        ]

    def list_symbols(self) -> list[str]:
        """Return symbols inferred from local FirstRate filenames."""

        return sorted({detected.symbol for detected in self.detected_files()})

    def list_sessions(
        self,
        symbol: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[HistoricalIntradaySession]:
        """Return normalized FirstRate session summaries."""

        result = self._load(symbol=symbol, start_date=start_date, end_date=end_date)
        return result.sessions

    def load_session(self, symbol: str, session_id: str) -> HistoricalIntradayImportResult:
        """Load one normalized FirstRate session."""

        return self._load(symbol=symbol, session_id=session_id, include_bars=True)

    def load_all_sessions(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        include_bars: bool = False,
    ) -> HistoricalIntradayImportResult:
        """Load normalized FirstRate sessions without storing all bars."""

        return self._load(start_date=start_date, end_date=end_date, include_bars=include_bars)

    def load_sessions(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
        include_bars: bool = False,
    ) -> HistoricalIntradayImportResult:
        """Load normalized FirstRate sessions for one symbol."""

        return self._load(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            include_bars=include_bars,
        )

    def get_instrument(self, symbol: str) -> HistoricalIntradayInstrument | None:
        """Return FirstRate instrument metadata if a matching file exists."""

        normalized_symbol = normalize_symbol(symbol)
        if normalized_symbol not in self.list_symbols():
            return None
        return _instrument_for_symbol(normalized_symbol, self.normalizer.source_timezone)

    def dry_run(self) -> FirstRateDryRunSummary:
        """Inspect local FirstRate files without writing processed output."""

        file_signature = self.file_cache_signature()
        if file_signature in self._dry_run_cache:
            return self._dry_run_cache[file_signature]

        result = self._load()
        file_summaries = [
            _file_dry_run_summary(file_result) for file_result in self._normalize_files(symbol=None)
        ]
        summary = FirstRateDryRunSummary(
            data_dir=str(self.data_dir),
            files_found=len(file_summaries),
            symbols_detected=[summary.symbol for summary in file_summaries],
            row_count=sum(summary.row_count for summary in file_summaries),
            session_count=len(result.sessions),
            earliest_timestamp_utc=_min_optional_datetime(
                summary.earliest_timestamp_utc for summary in file_summaries
            ),
            latest_timestamp_utc=_max_optional_datetime(
                summary.latest_timestamp_utc for summary in file_summaries
            ),
            start_date=_min_optional_date(summary.start_date for summary in file_summaries),
            end_date=_max_optional_date(summary.end_date for summary in file_summaries),
            readiness_counts=_readiness_counts(result.sessions),
            quality_issue_count=len(result.quality_issues),
            files=file_summaries,
            quality_issues=result.quality_issues,
            plain_english_summary=_dry_run_summary(result.sessions, file_summaries),
        )
        self._dry_run_cache[file_signature] = summary
        return summary

    def _load(
        self,
        symbol: str | None = None,
        session_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        include_bars: bool = False,
    ) -> HistoricalIntradayImportResult:
        imported_at = utc_now()
        normalized_symbol = normalize_symbol(symbol) if symbol is not None else None
        bars: list[HistoricalIntradayBar] = []
        sessions: list[HistoricalIntradaySession] = []
        issues: list[HistoricalIntradayQualityIssue] = []
        instruments: list[HistoricalIntradayInstrument] = []
        row_count = 0
        adjustment_modes: set[HistoricalIntradayAdjustmentMode] = set()

        file_results = self._normalize_files(
            symbol=normalized_symbol,
            include_bars=include_bars,
            only_session_id=session_id,
        )
        if not file_results:
            issues.append(
                HistoricalIntradayQualityIssue(
                    code="missing_firstrate_files",
                    message=(
                        f"No ignored local FirstRate CSV files were found under {self.data_dir}."
                    ),
                )
            )

        for file_result in file_results:
            row_count += file_result.row_count
            bars.extend(file_result.bars)
            sessions.extend(file_result.sessions)
            issues.extend(file_result.issues)
            adjustment_modes.add(file_result.adjustment_mode)
            if file_result.instrument is not None:
                instruments.append(file_result.instrument)

        sessions = _filter_sessions(sessions, normalized_symbol, session_id, start_date, end_date)
        session_keys = {(session.symbol, session.session_id) for session in sessions}
        bars = [
            bar
            for bar in bars
            if (bar.symbol, bar.session_id) in session_keys
            and _date_in_range(bar.timestamp_utc.date(), start_date, end_date)
        ]
        issues = [
            issue
            for issue in issues
            if _issue_matches_first_rate_filter(issue, normalized_symbol, session_id, session_keys)
        ]
        instruments = _unique_instruments(instruments, {session.symbol for session in sessions})
        source = HistoricalIntradayDataSource(
            source_id="firstrate-local-csv-dry-run",
            provider_name=self.provider_name,
            provider_type=HistoricalIntradayProviderType.LOCAL_CSV,
            source_path=str(self.data_dir),
            dataset_id="firstrate_local_csv_dry_run",
            imported_at=imported_at,
            row_count=row_count,
            source_timezone=self.normalizer.source_timezone,
            adjustment_mode=_one_or_unknown(adjustment_modes),
            license_note=FIRST_RATE_DEFAULT_LICENSE_NOTE,
        )
        return HistoricalIntradayImportResult(
            source=source,
            instruments=instruments,
            sessions=sessions,
            bars=bars,
            bars_loaded=len(bars),
            quality_issues=issues,
            plain_english_summary=_import_summary(sessions, row_count, issues),
        )

    def _normalize_files(
        self,
        *,
        symbol: str | None,
        include_bars: bool = False,
        only_session_id: str | None = None,
    ) -> list[FirstRateFileNormalizationResult]:
        file_signature = self.file_cache_signature()
        cache_key = (file_signature, symbol, include_bars, only_session_id)
        if cache_key in self._normalization_cache:
            return self._normalization_cache[cache_key]

        results: list[FirstRateFileNormalizationResult] = []
        for file_item in file_signature:
            path = Path(file_item.path)
            inferred_symbol = self.normalizer.infer_symbol_from_path(path)
            if symbol is not None and inferred_symbol != symbol:
                continue
            if not self.normalizer.can_normalize(path):
                continue
            results.append(
                self.normalizer.normalize_file(
                    path,
                    symbol=inferred_symbol,
                    include_bars=include_bars,
                    only_session_id=only_session_id,
                )
            )
        self._normalization_cache[cache_key] = results
        return results

    def _csv_paths(self) -> list[Path]:
        if not self.data_dir.exists():
            return []
        return sorted(self.data_dir.glob("*.csv"))

    def file_cache_signature(self) -> tuple[FirstRateFileCacheSignature, ...]:
        """Return cache keys that refresh when local CSV files change."""

        signatures: list[FirstRateFileCacheSignature] = []
        for path in self._csv_paths():
            if not self.normalizer.can_normalize(path):
                continue
            stat = path.stat()
            signatures.append(
                FirstRateFileCacheSignature(
                    path=str(path),
                    size_bytes=stat.st_size,
                    modified_time_ns=stat.st_mtime_ns,
                )
            )
        return tuple(signatures)


class _ParsedFirstRateRow:
    def __init__(
        self,
        *,
        bar: HistoricalIntradayBar | None = None,
        issue: HistoricalIntradayQualityIssue | None = None,
    ) -> None:
        self.bar = bar
        self.issue = issue


class _SessionAccumulator:
    def __init__(self, *, symbol: str, session_id: str, session_date: date) -> None:
        self.symbol = symbol
        self.session_id = session_id
        self.session_date = session_date
        self.bar_count = 0
        self.first_bar_timestamp_utc: datetime | None = None
        self.last_bar_timestamp_utc: datetime | None = None
        self.has_premarket = False
        self.has_regular_first_hour = False
        self.has_regular_session = False
        self.has_after_hours = False
        self.has_overnight = False
        self.regular_first_hour_bar_count = 0

    def add_bar(self, bar: HistoricalIntradayBar) -> None:
        """Add one normalized bar to the session summary accumulator."""

        self.bar_count += 1
        if self.first_bar_timestamp_utc is None or bar.timestamp_utc < self.first_bar_timestamp_utc:
            self.first_bar_timestamp_utc = bar.timestamp_utc
        if self.last_bar_timestamp_utc is None or bar.timestamp_utc > self.last_bar_timestamp_utc:
            self.last_bar_timestamp_utc = bar.timestamp_utc
        self.has_premarket = self.has_premarket or bar.session_type == IntradaySessionType.PREMARKET
        self.has_regular_first_hour = (
            self.has_regular_first_hour
            or bar.session_type == IntradaySessionType.REGULAR_FIRST_HOUR
        )
        if bar.session_type == IntradaySessionType.REGULAR_FIRST_HOUR:
            self.regular_first_hour_bar_count += 1
        self.has_regular_session = (
            self.has_regular_session or bar.session_type == IntradaySessionType.REGULAR_SESSION
        )
        self.has_after_hours = (
            self.has_after_hours or bar.session_type == IntradaySessionType.AFTER_HOURS
        )
        self.has_overnight = self.has_overnight or bar.session_type == IntradaySessionType.OVERNIGHT


def _parse_firstrate_timestamp(
    raw_timestamp: str,
    source_zone: ZoneInfo,
    row_number: int,
    symbol: str,
) -> tuple[datetime, HistoricalIntradayQualityIssue | None]:
    try:
        parsed = datetime.fromisoformat(raw_timestamp)
    except ValueError:
        return utc_now(), HistoricalIntradayQualityIssue(
            code="invalid_timestamp",
            message=f"FirstRate timestamp {raw_timestamp!r} could not be parsed.",
            severity="error",
            symbol=symbol,
            row_number=row_number,
        )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=source_zone)
    return parsed.astimezone(UTC), None


def _session_type_for(local_time: time) -> IntradaySessionType | None:
    if time(4, 0) <= local_time < time(9, 30):
        return IntradaySessionType.PREMARKET
    if time(9, 30) <= local_time <= time(10, 29):
        return IntradaySessionType.REGULAR_FIRST_HOUR
    if time(10, 30) <= local_time <= time(16, 0):
        return IntradaySessionType.REGULAR_SESSION
    if time(16, 0) < local_time <= time(20, 0):
        return IntradaySessionType.AFTER_HOURS
    return None


def _sessions_from_accumulators(
    accumulators: dict[str, _SessionAccumulator],
    issues: list[HistoricalIntradayQualityIssue],
) -> list[HistoricalIntradaySession]:
    sessions: list[HistoricalIntradaySession] = []
    for accumulator in sorted(
        accumulators.values(), key=lambda item: (item.symbol, item.session_id)
    ):
        session_issues = [
            issue
            for issue in issues
            if issue.symbol == accumulator.symbol and issue.session_id == accumulator.session_id
        ]
        readiness = _classify_readiness(accumulator, session_issues)
        sessions.append(
            HistoricalIntradaySession(
                session_id=accumulator.session_id,
                symbol=accumulator.symbol,
                session_date=accumulator.session_date,
                bar_count=accumulator.bar_count,
                first_bar_timestamp_utc=accumulator.first_bar_timestamp_utc,
                last_bar_timestamp_utc=accumulator.last_bar_timestamp_utc,
                has_premarket=accumulator.has_premarket,
                has_regular_first_hour=accumulator.has_regular_first_hour,
                has_regular_session=accumulator.has_regular_session,
                has_after_hours=accumulator.has_after_hours,
                has_overnight=accumulator.has_overnight,
                readiness=readiness,
                quality_issue_count=len(session_issues),
                plain_english_summary=_readiness_summary(readiness),
            )
        )
    return sessions


def _classify_readiness(
    accumulator: _SessionAccumulator,
    issues: list[HistoricalIntradayQualityIssue],
) -> HistoricalIntradayReadiness:
    if any(issue.severity == "error" for issue in issues):
        return HistoricalIntradayReadiness.UNUSABLE
    if accumulator.regular_first_hour_bar_count < 5:
        return HistoricalIntradayReadiness.INCOMPLETE
    review_codes = {"duplicate_bar", "unsorted_bars"}
    if any(issue.code in review_codes for issue in issues):
        return HistoricalIntradayReadiness.NEEDS_REVIEW
    return HistoricalIntradayReadiness.READY_FOR_REPLAY


def _readiness_summary(readiness: HistoricalIntradayReadiness) -> str:
    if readiness == HistoricalIntradayReadiness.READY_FOR_REPLAY:
        return "This local FirstRate session has enough first-hour bars for future replay."
    if readiness == HistoricalIntradayReadiness.INCOMPLETE:
        return "This local FirstRate session has some data, but not enough first-hour coverage."
    if readiness == HistoricalIntradayReadiness.UNUSABLE:
        return "This local FirstRate session has critical data problems."
    return "This local FirstRate session needs review before replay."


def _file_dry_run_summary(
    file_result: FirstRateFileNormalizationResult,
) -> FirstRateFileDryRunSummary:
    earliest = _min_optional_datetime(
        session.first_bar_timestamp_utc for session in file_result.sessions
    )
    latest = _max_optional_datetime(
        session.last_bar_timestamp_utc for session in file_result.sessions
    )
    start_date = _min_optional_date(session.session_date for session in file_result.sessions)
    end_date = _max_optional_date(session.session_date for session in file_result.sessions)
    return FirstRateFileDryRunSummary(
        path=str(file_result.path),
        filename=file_result.path.name,
        symbol=file_result.symbol,
        row_count=file_result.row_count,
        session_count=len(file_result.sessions),
        earliest_timestamp_utc=earliest,
        latest_timestamp_utc=latest,
        start_date=start_date,
        end_date=end_date,
        readiness_counts=_readiness_counts(file_result.sessions),
        quality_issue_count=len(file_result.issues),
        plain_english_summary=_file_summary(file_result),
    )


def _file_summary(file_result: FirstRateFileNormalizationResult) -> str:
    if not file_result.sessions:
        return f"{file_result.path.name} did not produce replay-ready session summaries."
    return (
        f"{file_result.path.name} produced {len(file_result.sessions)} local session(s) for "
        f"{file_result.symbol}. Real-money status remains Not allowed."
    )


def _dry_run_summary(
    sessions: list[HistoricalIntradaySession],
    file_summaries: list[FirstRateFileDryRunSummary],
) -> str:
    if not file_summaries:
        return "No ignored local FirstRate CSV files were found for dry-run inspection."
    ready_count = sum(
        1
        for session in sessions
        if session.readiness == HistoricalIntradayReadiness.READY_FOR_REPLAY
    )
    return (
        f"Found {len(file_summaries)} local FirstRate file(s) and {len(sessions)} session(s). "
        f"{ready_count} session(s) look ready for future replay. This is research-only and "
        "real-money status is Not allowed."
    )


def _import_summary(
    sessions: list[HistoricalIntradaySession],
    row_count: int,
    issues: list[HistoricalIntradayQualityIssue],
) -> str:
    if not sessions:
        return "No local FirstRate sessions are ready to inspect from ignored CSV files."
    ready_count = sum(
        1
        for session in sessions
        if session.readiness == HistoricalIntradayReadiness.READY_FOR_REPLAY
    )
    return (
        f"Inspected {row_count} FirstRate row(s) across {len(sessions)} session(s). "
        f"{ready_count} session(s) look ready for future replay. "
        f"{len(issues)} data quality issue(s) were reported."
    )


def _readiness_counts(sessions: list[HistoricalIntradaySession]) -> dict[str, int]:
    counts = {readiness.value: 0 for readiness in HistoricalIntradayReadiness}
    for session in sessions:
        counts[session.readiness.value] += 1
    return counts


def _filter_sessions(
    sessions: list[HistoricalIntradaySession],
    symbol: str | None,
    session_id: str | None,
    start_date: date | None,
    end_date: date | None,
) -> list[HistoricalIntradaySession]:
    filtered = sessions
    if symbol is not None:
        filtered = [session for session in filtered if session.symbol == symbol]
    if session_id is not None:
        filtered = [session for session in filtered if session.session_id == session_id]
    if start_date is not None:
        filtered = [session for session in filtered if session.session_date >= start_date]
    if end_date is not None:
        filtered = [session for session in filtered if session.session_date <= end_date]
    return filtered


def _date_in_range(value: date, start_date: date | None, end_date: date | None) -> bool:
    if start_date is not None and value < start_date:
        return False
    if end_date is not None and value > end_date:
        return False
    return True


def _issue_matches_first_rate_filter(
    issue: HistoricalIntradayQualityIssue,
    symbol: str | None,
    session_id: str | None,
    session_keys: set[tuple[str, str]],
) -> bool:
    if symbol is not None and issue.symbol != symbol:
        return False
    if session_id is not None and issue.session_id != session_id:
        return False
    if issue.session_id is not None and session_keys:
        return (issue.symbol, issue.session_id) in session_keys
    return True


def _unique_instruments(
    instruments: list[HistoricalIntradayInstrument], symbols: set[str]
) -> list[HistoricalIntradayInstrument]:
    by_symbol = {instrument.symbol: instrument for instrument in instruments}
    return [instrument for symbol, instrument in sorted(by_symbol.items()) if symbol in symbols]


def _instrument_for_symbol(symbol: str, timezone: str) -> HistoricalIntradayInstrument:
    return HistoricalIntradayInstrument(
        symbol=symbol,
        display_name=f"{symbol} FirstRate Local CSV",
        instrument_type=(
            IntradayInstrumentType.INDEX_ETF_REFERENCE
            if symbol in {"SPY", "QQQ"}
            else IntradayInstrumentType.OTHER
        ),
        point_value=1,
        tick_size=0.01,
        tick_value=0.01,
        exchange_or_venue="Local FirstRate CSV",
        timezone=timezone,
        regular_session_open="09:30",
        regular_session_close="16:00",
        plain_english_description=(
            f"{symbol} FirstRate local CSV data for research-only dry-run inspection."
        ),
    )


def _invalid_firstrate_row_code(error: Exception) -> str:
    text = str(error).lower()
    if "high must" in text or "low must" in text or "greater than" in text:
        return "invalid_ohlc"
    if "volume" in text:
        return "invalid_volume"
    return "invalid_row"


def _min_optional_datetime(values: Iterator[datetime | None]) -> datetime | None:
    present = [value for value in values if value is not None]
    return min(present) if present else None


def _max_optional_datetime(values: Iterator[datetime | None]) -> datetime | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _min_optional_date(values: Iterator[date | None]) -> date | None:
    present = [value for value in values if value is not None]
    return min(present) if present else None


def _max_optional_date(values: Iterator[date | None]) -> date | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _one_or_unknown(
    values: set[HistoricalIntradayAdjustmentMode],
) -> HistoricalIntradayAdjustmentMode:
    if len(values) == 1:
        return next(iter(values))
    return HistoricalIntradayAdjustmentMode.UNKNOWN


def _default_firstrate_data_dir() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "data"
        / "raw"
        / "historical_intraday"
        / "firstratedata"
    )
