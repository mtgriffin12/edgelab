"""FirstRate replay integration helpers."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from typing import Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator

from edgelab.intraday.csv_normalizers import (
    FirstRateFileCacheSignature,
    FirstRateLocalCSVHistoricalProvider,
)
from edgelab.intraday.historical_schema import (
    HistoricalIntradayBar,
    HistoricalIntradayImportResult,
    HistoricalIntradayInstrument,
    HistoricalIntradayProviderCapabilities,
    HistoricalIntradayQualityIssue,
    HistoricalIntradaySession,
    normalize_to_utc,
)
from edgelab.intraday.schema import IntradaySessionType, normalize_symbol


class FirstHourCompletenessLabel(StrEnum):
    """Plain labels for first-hour data continuity."""

    COMPLETE = "complete"
    MINOR_GAPS = "minor_gaps"
    MAJOR_GAPS = "major_gaps"
    REPLAY_UNSAFE = "replay_unsafe"


class FirstHourCompleteness(BaseModel):
    """First-hour bar continuity for one local historical session."""

    symbol: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    session_date: date
    source_timezone: str = Field(min_length=1)
    expected_first_hour_bar_count: int = Field(ge=0)
    actual_first_hour_bar_count: int = Field(ge=0)
    unique_first_hour_bar_count: int = Field(ge=0)
    missing_first_hour_timestamps_utc: list[datetime] = Field(default_factory=list)
    duplicate_first_hour_timestamps_utc: list[datetime] = Field(default_factory=list)
    first_hour_completeness_label: FirstHourCompletenessLabel
    plain_english_summary: str = Field(min_length=1)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @field_validator("symbol")
    @classmethod
    def normalize_completeness_symbol(cls, value: str) -> str:
        """Normalize symbols."""

        return normalize_symbol(value)

    @field_validator("missing_first_hour_timestamps_utc", "duplicate_first_hour_timestamps_utc")
    @classmethod
    def normalize_completeness_timestamps(cls, values: list[datetime]) -> list[datetime]:
        """Normalize timestamps to UTC."""

        return [normalize_to_utc(value) for value in values]

    @model_validator(mode="after")
    def validate_research_only(self) -> Self:
        """Keep completeness output conservative."""

        if self.research_only_status != "Research only":
            raise ValueError("first-hour completeness must remain research-only")
        if self.real_money_status != "Not allowed":
            raise ValueError("first-hour completeness real-money status must be Not allowed")
        return self


class FirstHourCompletenessSummary(BaseModel):
    """Aggregate first-hour completeness counts."""

    sessions_checked: int = Field(ge=0)
    complete: int = Field(ge=0)
    minor_gaps: int = Field(ge=0)
    major_gaps: int = Field(ge=0)
    replay_unsafe: int = Field(ge=0)
    sessions_with_missing_first_hour_timestamps: int = Field(ge=0)
    sessions_with_duplicate_first_hour_timestamps: int = Field(ge=0)
    plain_english_summary: str = Field(min_length=1)
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_research_only(self) -> Self:
        """Keep aggregate output conservative."""

        if self.research_only_status != "Research only":
            raise ValueError("first-hour completeness summary must remain research-only")
        if self.real_money_status != "Not allowed":
            raise ValueError(
                "first-hour completeness summary real-money status must be Not allowed"
            )
        return self


class CachedFirstRateHistoricalDataProvider:
    """Read-only FirstRate provider wrapper that caches normalized bars per symbol."""

    def __init__(self, provider: FirstRateLocalCSVHistoricalProvider) -> None:
        self.provider = provider
        self._file_signature: tuple[FirstRateFileCacheSignature, ...] = ()
        self._symbol_cache: dict[str, HistoricalIntradayImportResult] = {}
        self._session_cache: dict[str, dict[str, HistoricalIntradayImportResult]] = {}
        self._completeness_cache: dict[
            tuple[str | None, date | None, date | None],
            list[FirstHourCompleteness],
        ] = {}

    def provider_capabilities(self) -> HistoricalIntradayProviderCapabilities:
        """Return wrapped provider capabilities."""

        return self.provider.provider_capabilities()

    def list_symbols(self) -> list[str]:
        """Return available FirstRate symbols."""

        self._refresh_if_local_files_changed()
        return self.provider.list_symbols()

    def list_sessions(
        self,
        symbol: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[HistoricalIntradaySession]:
        """Return session summaries, using cached normalized bars when possible."""

        if symbol is None:
            sessions: list[HistoricalIntradaySession] = []
            for available_symbol in self.list_symbols():
                sessions.extend(self.list_sessions(available_symbol, start_date, end_date))
            return sessions

        result = self._result_for_symbol(symbol)
        return [
            session
            for session in result.sessions
            if _session_date_in_range(session.session_date, start_date, end_date)
        ]

    def load_session(self, symbol: str, session_id: str) -> HistoricalIntradayImportResult:
        """Load one cached FirstRate session with bars."""

        normalized_symbol = normalize_symbol(symbol)
        return self._session_results_for_symbol(normalized_symbol).get(
            session_id,
            _copy_import_result(
                self._result_for_symbol(normalized_symbol),
                sessions=[],
                bars=[],
                issues=[],
            ),
        )

    def load_all_sessions(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> HistoricalIntradayImportResult:
        """Load all cached FirstRate sessions with bars."""

        combined: HistoricalIntradayImportResult | None = None
        all_sessions: list[HistoricalIntradaySession] = []
        all_bars: list[HistoricalIntradayBar] = []
        all_issues: list[HistoricalIntradayQualityIssue] = []
        instruments: list[HistoricalIntradayInstrument] = []
        for symbol in self.list_symbols():
            result = self._result_for_symbol(symbol)
            sessions = [
                session
                for session in result.sessions
                if _session_date_in_range(session.session_date, start_date, end_date)
            ]
            session_keys = {(session.symbol, session.session_id) for session in sessions}
            all_sessions.extend(sessions)
            all_bars.extend(
                bar for bar in result.bars if (bar.symbol, bar.session_id) in session_keys
            )
            all_issues.extend(
                issue
                for issue in result.quality_issues
                if issue.session_id is None or (issue.symbol, issue.session_id) in session_keys
            )
            instruments.extend(result.instruments)
            combined = result

        if combined is None:
            return self.provider.load_all_sessions()
        unique_instruments = {instrument.symbol: instrument for instrument in instruments}
        return _copy_import_result(
            combined,
            sessions=sorted(all_sessions, key=lambda session: (session.symbol, session.session_id)),
            bars=sorted(all_bars, key=lambda bar: (bar.symbol, bar.session_id, bar.timestamp_utc)),
            issues=all_issues,
            instruments=list(unique_instruments.values()),
        )

    def load_sessions(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> HistoricalIntradayImportResult:
        """Load cached FirstRate sessions for one symbol with bars."""

        normalized_symbol = normalize_symbol(symbol)
        result = self._result_for_symbol(normalized_symbol)
        sessions = [
            session
            for session in result.sessions
            if _session_date_in_range(session.session_date, start_date, end_date)
        ]
        session_keys = {(session.symbol, session.session_id) for session in sessions}
        bars = [bar for bar in result.bars if (bar.symbol, bar.session_id) in session_keys]
        issues = [
            issue
            for issue in result.quality_issues
            if issue.session_id is None or (issue.symbol, issue.session_id) in session_keys
        ]
        return _copy_import_result(result, sessions=sessions, bars=bars, issues=issues)

    def get_instrument(self, symbol: str) -> HistoricalIntradayInstrument | None:
        """Return instrument metadata."""

        return self.provider.get_instrument(symbol)

    def first_hour_completeness_for_sessions(
        self,
        symbol: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[FirstHourCompleteness]:
        """Return first-hour completeness details for matching sessions."""

        self._refresh_if_local_files_changed()
        normalized_symbol = normalize_symbol(symbol) if symbol is not None else None
        cache_key = (normalized_symbol, start_date, end_date)
        if cache_key in self._completeness_cache:
            return self._completeness_cache[cache_key]

        result = (
            self.load_sessions(normalized_symbol, start_date, end_date)
            if normalized_symbol is not None
            else self.load_all_sessions(start_date, end_date)
        )
        completeness = first_hour_completeness_for_import_result(result)
        self._completeness_cache[cache_key] = completeness
        return completeness

    def _result_for_symbol(self, symbol: str) -> HistoricalIntradayImportResult:
        self._refresh_if_local_files_changed()
        normalized_symbol = normalize_symbol(symbol)
        if normalized_symbol not in self._symbol_cache:
            self._symbol_cache[normalized_symbol] = self.provider.load_sessions(
                normalized_symbol,
                include_bars=True,
            )
        return self._symbol_cache[normalized_symbol]

    def _session_results_for_symbol(
        self,
        symbol: str,
    ) -> dict[str, HistoricalIntradayImportResult]:
        normalized_symbol = normalize_symbol(symbol)
        if normalized_symbol in self._session_cache:
            return self._session_cache[normalized_symbol]

        result = self._result_for_symbol(normalized_symbol)
        bars_by_session: dict[str, list[HistoricalIntradayBar]] = {}
        for bar in result.bars:
            bars_by_session.setdefault(bar.session_id, []).append(bar)

        issues_by_session: dict[str, list[HistoricalIntradayQualityIssue]] = {}
        symbol_level_issues: list[HistoricalIntradayQualityIssue] = []
        for issue in result.quality_issues:
            if issue.session_id is None:
                symbol_level_issues.append(issue)
            elif issue.symbol == normalized_symbol:
                issues_by_session.setdefault(issue.session_id, []).append(issue)

        session_results: dict[str, HistoricalIntradayImportResult] = {}
        for session in result.sessions:
            session_results[session.session_id] = _copy_import_result(
                result,
                sessions=[session],
                bars=bars_by_session.get(session.session_id, []),
                issues=symbol_level_issues + issues_by_session.get(session.session_id, []),
            )

        self._session_cache[normalized_symbol] = session_results
        return session_results

    def _refresh_if_local_files_changed(self) -> None:
        file_signature = self.provider.file_cache_signature()
        if file_signature == self._file_signature:
            return
        self._file_signature = file_signature
        self._symbol_cache.clear()
        self._session_cache.clear()
        self._completeness_cache.clear()


def first_hour_completeness_for_import_result(
    result: HistoricalIntradayImportResult,
) -> list[FirstHourCompleteness]:
    """Calculate first-hour completeness for every session in an import result."""

    bars_by_session: dict[tuple[str, str], list[HistoricalIntradayBar]] = {}
    for bar in result.bars:
        bars_by_session.setdefault((bar.symbol, bar.session_id), []).append(bar)

    return [
        calculate_first_hour_completeness(
            session=session,
            bars=bars_by_session.get((session.symbol, session.session_id), []),
        )
        for session in result.sessions
    ]


def calculate_first_hour_completeness(
    *,
    session: HistoricalIntradaySession,
    bars: list[HistoricalIntradayBar],
) -> FirstHourCompleteness:
    """Calculate missing and duplicate one-minute first-hour bars."""

    first_hour_bars = [
        bar for bar in bars if bar.session_type == IntradaySessionType.REGULAR_FIRST_HOUR
    ]
    source_timezone = _source_timezone(first_hour_bars or bars)
    expected_timestamps = _expected_first_hour_timestamps(session.session_date, source_timezone)
    timestamp_counts = Counter(bar.timestamp_utc for bar in first_hour_bars)
    actual_timestamps = set(timestamp_counts)
    missing_timestamps = [
        timestamp for timestamp in expected_timestamps if timestamp not in actual_timestamps
    ]
    duplicate_timestamps = sorted(
        timestamp for timestamp, count in timestamp_counts.items() if count > 1
    )
    label = _completeness_label(
        missing_count=len(missing_timestamps),
        duplicate_count=len(duplicate_timestamps),
        unique_count=len(actual_timestamps),
    )
    return FirstHourCompleteness(
        symbol=session.symbol,
        session_id=session.session_id,
        session_date=session.session_date,
        source_timezone=source_timezone,
        expected_first_hour_bar_count=len(expected_timestamps),
        actual_first_hour_bar_count=len(first_hour_bars),
        unique_first_hour_bar_count=len(actual_timestamps),
        missing_first_hour_timestamps_utc=missing_timestamps,
        duplicate_first_hour_timestamps_utc=duplicate_timestamps,
        first_hour_completeness_label=label,
        plain_english_summary=_completeness_summary_text(
            label,
            missing_count=len(missing_timestamps),
            duplicate_count=len(duplicate_timestamps),
        ),
    )


def summarize_first_hour_completeness(
    completeness: list[FirstHourCompleteness],
) -> FirstHourCompletenessSummary:
    """Summarize first-hour completeness across sessions."""

    counts = Counter(item.first_hour_completeness_label for item in completeness)
    missing_sessions = sum(1 for item in completeness if item.missing_first_hour_timestamps_utc)
    duplicate_sessions = sum(1 for item in completeness if item.duplicate_first_hour_timestamps_utc)
    return FirstHourCompletenessSummary(
        sessions_checked=len(completeness),
        complete=counts[FirstHourCompletenessLabel.COMPLETE],
        minor_gaps=counts[FirstHourCompletenessLabel.MINOR_GAPS],
        major_gaps=counts[FirstHourCompletenessLabel.MAJOR_GAPS],
        replay_unsafe=counts[FirstHourCompletenessLabel.REPLAY_UNSAFE],
        sessions_with_missing_first_hour_timestamps=missing_sessions,
        sessions_with_duplicate_first_hour_timestamps=duplicate_sessions,
        plain_english_summary=_aggregate_summary_text(completeness, missing_sessions),
    )


def _copy_import_result(
    result: HistoricalIntradayImportResult,
    *,
    sessions: list[HistoricalIntradaySession],
    bars: list[HistoricalIntradayBar],
    issues: list[HistoricalIntradayQualityIssue],
    instruments: list[HistoricalIntradayInstrument] | None = None,
) -> HistoricalIntradayImportResult:
    return HistoricalIntradayImportResult(
        source=result.source,
        instruments=instruments if instruments is not None else result.instruments,
        sessions=sessions,
        bars=bars,
        bars_loaded=len(bars),
        quality_issues=issues,
        plain_english_summary=(
            f"Loaded {len(sessions)} local FirstRate session(s) and {len(bars)} bar(s). "
            "This remains research-only."
        ),
        research_only_status=result.research_only_status,
        real_money_status=result.real_money_status,
    )


def _source_timezone(bars: list[HistoricalIntradayBar]) -> str:
    if bars:
        return bars[0].source_timezone
    return "America/New_York"


def _expected_first_hour_timestamps(session_date: date, source_timezone: str) -> list[datetime]:
    try:
        timezone = ZoneInfo(source_timezone)
    except ZoneInfoNotFoundError:
        timezone = ZoneInfo("America/New_York")
    start = datetime.combine(session_date, time(9, 30), tzinfo=timezone)
    return [(start + timedelta(minutes=minute)).astimezone(UTC) for minute in range(60)]


def _completeness_label(
    *,
    missing_count: int,
    duplicate_count: int,
    unique_count: int,
) -> FirstHourCompletenessLabel:
    if duplicate_count > 0 or unique_count < 5:
        return FirstHourCompletenessLabel.REPLAY_UNSAFE
    if missing_count == 0:
        return FirstHourCompletenessLabel.COMPLETE
    if missing_count <= 4:
        return FirstHourCompletenessLabel.MINOR_GAPS
    if missing_count <= 15:
        return FirstHourCompletenessLabel.MAJOR_GAPS
    return FirstHourCompletenessLabel.REPLAY_UNSAFE


def _completeness_summary_text(
    label: FirstHourCompletenessLabel,
    *,
    missing_count: int,
    duplicate_count: int,
) -> str:
    if label == FirstHourCompletenessLabel.COMPLETE:
        return "The regular first hour has all expected one-minute bars."
    if duplicate_count:
        return "The regular first hour has duplicate timestamps, so replay continuity needs review."
    if label == FirstHourCompletenessLabel.MINOR_GAPS:
        return f"The regular first hour has {missing_count} small missing-minute gap(s)."
    if label == FirstHourCompletenessLabel.MAJOR_GAPS:
        return f"The regular first hour has {missing_count} missing minute(s) to review."
    return "The regular first hour is missing too much data for a safe replay."


def _aggregate_summary_text(
    completeness: list[FirstHourCompleteness],
    missing_sessions: int,
) -> str:
    if not completeness:
        return "No local FirstRate sessions were checked for first-hour completeness."
    complete_count = sum(
        1
        for item in completeness
        if item.first_hour_completeness_label == FirstHourCompletenessLabel.COMPLETE
    )
    return (
        f"{complete_count} of {len(completeness)} local FirstRate session(s) have complete "
        f"first-hour data. {missing_sessions} session(s) have at least one missing first-hour "
        "minute to review."
    )


def _session_date_in_range(
    session_date: date,
    start_date: date | None,
    end_date: date | None,
) -> bool:
    if start_date is not None and session_date < start_date:
        return False
    if end_date is not None and session_date > end_date:
        return False
    return True
