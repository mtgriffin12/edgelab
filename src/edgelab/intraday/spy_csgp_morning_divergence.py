"""Local SPY/CSGP morning divergence study."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import UTC, date, datetime, time
from pathlib import Path
from statistics import mean, median
from typing import Self
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator, model_validator

DEFAULT_RECENT_DATA_DIR = Path("data/raw/historical_intraday/firstratedata")
DEFAULT_SPY_RECENT_PATH = DEFAULT_RECENT_DATA_DIR / "SPY_recent_1min.csv"
DEFAULT_CSGP_RECENT_PATH = DEFAULT_RECENT_DATA_DIR / "CSGP_recent_1min.csv"
REQUIRED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
NEW_YORK = ZoneInfo("America/New_York")
WINDOWS = [
    ("open_to_15_minutes", "9:30-9:45", time(9, 30), time(9, 45), False),
    ("open_to_30_minutes", "9:30-10:00", time(9, 30), time(10, 0), False),
    ("open_to_60_minutes", "9:30-10:30", time(9, 30), time(10, 30), False),
    ("follow_through_after_10", "10:00-11:00", time(10, 0), time(11, 0), False),
    ("full_regular_session", "9:30-16:00", time(9, 30), time(16, 0), True),
]
SPY_WEAKNESS_THRESHOLDS = [0.50, 0.75, 1.00, 1.25]
SPY_STRENGTH_THRESHOLDS = [0.50, 0.75, 1.00, 1.25]


class DateRangeSummary(BaseModel):
    """Plain date range summary for local files and analyzed overlap."""

    first_date: date | None = None
    last_date: date | None = None
    trading_dates: int = Field(ge=0)
    plain_english_summary: str = Field(min_length=1)


class MorningDivergenceFileSummary(BaseModel):
    """One local CSV file used by the morning divergence study."""

    symbol: str
    path: str = Field(min_length=1)
    exists: bool
    row_count: int = Field(ge=0)
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None
    first_date: date | None = None
    last_date: date | None = None
    trading_dates: int = Field(ge=0)
    regular_hours_rows: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)


class MorningWindowReturn(BaseModel):
    """One symbol return for one local trading date and morning window."""

    date: date
    window_id: str = Field(min_length=1)
    window_label: str = Field(min_length=1)
    start_timestamp: datetime | None = None
    end_timestamp: datetime | None = None
    start_price: float | None = None
    end_price: float | None = None
    return_pct: float | None = None
    missing_reason: str | None = None


class MorningWindowSummary(BaseModel):
    """Plain summary for one morning window."""

    window_id: str = Field(min_length=1)
    window_label: str = Field(min_length=1)
    dates_analyzed: int = Field(ge=0)
    missing_dates: int = Field(ge=0)
    average_spy_move: float | None = None
    median_spy_move: float | None = None
    average_csgp_move: float | None = None
    median_csgp_move: float | None = None
    spy_down_csgp_up_count: int = Field(ge=0)
    opposite_direction_count: int = Field(ge=0)
    same_direction_count: int = Field(ge=0)
    csgp_held_stronger_count: int = Field(ge=0)
    plain_english_summary: str = Field(min_length=1)
    secondary_only: bool = False


class CsgpBehaviorBucket(BaseModel):
    """CSGP behavior bucket for weak SPY mornings."""

    label: str = Field(min_length=1)
    count: int = Field(ge=0)


class DivergenceDay(BaseModel):
    """One strongest or weakest SPY/CSGP divergence date."""

    date: date
    window_label: str = Field(min_length=1)
    spy_move: float
    csgp_move: float
    csgp_minus_spy: float
    plain_english_summary: str = Field(min_length=1)


class SpyWeaknessThresholdSummary(BaseModel):
    """Result for one SPY weakness threshold inside one morning window."""

    window_id: str = Field(min_length=1)
    window_label: str = Field(min_length=1)
    threshold_pct: float
    threshold_label: str = Field(min_length=1)
    matching_mornings: int = Field(ge=0)
    average_spy_move: float | None = None
    median_spy_move: float | None = None
    average_csgp_move: float | None = None
    median_csgp_move: float | None = None
    csgp_positive_while_spy_negative_count: int = Field(ge=0)
    csgp_beat_spy_by_1pt_count: int = Field(ge=0)
    csgp_beat_spy_by_2pt_count: int = Field(ge=0)
    csgp_also_fell_count: int = Field(ge=0)
    same_direction_count: int = Field(ge=0)
    opposite_direction_count: int = Field(ge=0)
    behavior_buckets: list[CsgpBehaviorBucket] = Field(default_factory=list)
    strongest_divergence_days: list[DivergenceDay] = Field(default_factory=list)
    weakest_divergence_days: list[DivergenceDay] = Field(default_factory=list)
    plain_english_summary: str = Field(min_length=1)
    secondary_only: bool = False


class SpyStrengthThresholdSummary(BaseModel):
    """Result for one SPY strength threshold inside one morning window."""

    window_id: str = Field(min_length=1)
    window_label: str = Field(min_length=1)
    threshold_pct: float
    threshold_label: str = Field(min_length=1)
    matching_mornings: int = Field(ge=0)
    average_spy_move: float | None = None
    median_spy_move: float | None = None
    average_csgp_move: float | None = None
    median_csgp_move: float | None = None
    csgp_negative_while_spy_positive_count: int = Field(ge=0)
    csgp_lagged_spy_by_1pt_count: int = Field(ge=0)
    csgp_lagged_spy_by_2pt_count: int = Field(ge=0)
    csgp_also_rose_count: int = Field(ge=0)
    same_direction_count: int = Field(ge=0)
    opposite_direction_count: int = Field(ge=0)
    strongest_inverse_dates: list[DivergenceDay] = Field(default_factory=list)
    weakest_inverse_dates: list[DivergenceDay] = Field(default_factory=list)
    plain_english_summary: str = Field(min_length=1)
    secondary_only: bool = False


class CombinedInverseSummary(BaseModel):
    """Combined inverse-relationship summary across SPY-down and SPY-up sides."""

    window_id: str = Field(min_length=1)
    window_label: str = Field(min_length=1)
    threshold_pct: float
    threshold_label: str = Field(min_length=1)
    total_meaningful_spy_move_mornings: int = Field(ge=0)
    inverse_mornings_count: int = Field(ge=0)
    inverse_mornings_percent: float | None = None
    same_direction_mornings_count: int = Field(ge=0)
    same_direction_mornings_percent: float | None = None
    average_csgp_minus_spy_return_spread: float | None = None
    clearer_side: str = Field(min_length=1)
    sample_readiness: str = Field(min_length=1)
    plain_english_summary: str = Field(min_length=1)
    secondary_only: bool = False


class FollowThroughSummary(BaseModel):
    """CSGP movement from 10:00 to 11:00 after weak SPY 9:30-10:00 mornings."""

    threshold_label: str = Field(min_length=1)
    matching_mornings: int = Field(ge=0)
    csgp_continued_higher_count: int = Field(ge=0)
    csgp_gave_back_count: int = Field(ge=0)
    csgp_mixed_count: int = Field(ge=0)
    average_follow_through_move: float | None = None
    median_follow_through_move: float | None = None
    plain_english_summary: str = Field(min_length=1)


class SpyCsgpMorningDivergenceStudy(BaseModel):
    """Read-only local SPY/CSGP morning divergence study."""

    study_id: str = "phase-7x-2u-spy-csgp-morning-divergence-study"
    data_readiness_summary: str = Field(min_length=1)
    files_used: list[MorningDivergenceFileSummary] = Field(min_length=1)
    spy_file_range: DateRangeSummary
    csgp_file_range: DateRangeSummary
    overlap_range_analyzed: DateRangeSummary
    overlapping_start_date: date | None = None
    overlapping_end_date: date | None = None
    trading_dates_analyzed: int = Field(ge=0)
    analyzed_sample_description: str = Field(min_length=1)
    morning_windows_tested: list[str] = Field(min_length=1)
    spy_weakness_thresholds_tested: list[str] = Field(min_length=1)
    spy_strength_thresholds_tested: list[str] = Field(min_length=1)
    window_summaries: list[MorningWindowSummary] = Field(default_factory=list)
    threshold_summaries: list[SpyWeaknessThresholdSummary] = Field(default_factory=list)
    strength_threshold_summaries: list[SpyStrengthThresholdSummary] = Field(default_factory=list)
    combined_inverse_summaries: list[CombinedInverseSummary] = Field(default_factory=list)
    spy_down_csgp_stronger_summary: str = Field(min_length=1)
    spy_up_csgp_weaker_summary: str = Field(min_length=1)
    combined_inverse_summary: str = Field(min_length=1)
    strongest_divergence_days: list[DivergenceDay] = Field(default_factory=list)
    weakest_divergence_days: list[DivergenceDay] = Field(default_factory=list)
    strongest_inverse_mornings: list[DivergenceDay] = Field(default_factory=list)
    weakest_inverse_mornings: list[DivergenceDay] = Field(default_factory=list)
    follow_through_summary: FollowThroughSummary
    strongest_window_if_any: str = Field(min_length=1)
    csgp_opposite_spy_plain_english: str = Field(min_length=1)
    bottom_line: str = Field(min_length=1)
    plain_english_bottom_line: str = Field(min_length=1)
    what_to_study_next: list[str] = Field(default_factory=list)
    no_external_calls: bool = True
    no_live_data: bool = True
    no_saved_outputs: bool = True
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_safety(self) -> Self:
        """Keep study output inside the local research-only boundary."""

        if not self.no_external_calls:
            raise ValueError("SPY/CSGP study must not call external services")
        if not self.no_live_data:
            raise ValueError("SPY/CSGP study must not use live data")
        if self.research_only_status != "Research only":
            raise ValueError("SPY/CSGP study must remain research-only")
        if self.real_money_status != "Not allowed":
            raise ValueError("SPY/CSGP study real-money status must be Not allowed")
        return self


class _LocalBar(BaseModel):
    symbol: str
    timestamp: datetime
    local_date: date
    local_time: time
    open: float
    high: float
    low: float
    close: float

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo=NEW_YORK)
        return value.astimezone(UTC)


class _DailyWindowPair(BaseModel):
    date: date
    window_id: str
    window_label: str
    spy_return: float | None
    csgp_return: float | None
    missing_reason: str | None = None
    secondary_only: bool = False


class SpyCsgpMorningDivergenceStudyService:
    """Run the local SPY/CSGP morning divergence study."""

    def __init__(
        self,
        *,
        spy_path: Path = DEFAULT_SPY_RECENT_PATH,
        csgp_path: Path = DEFAULT_CSGP_RECENT_PATH,
    ) -> None:
        self.spy_path = spy_path
        self.csgp_path = csgp_path

    def run(self) -> SpyCsgpMorningDivergenceStudy:
        """Read the local recent CSV files and compute the study."""

        spy_file, spy_bars = _load_symbol_bars("SPY", self.spy_path)
        csgp_file, csgp_bars = _load_symbol_bars("CSGP", self.csgp_path)
        common_dates = sorted(set(spy_bars) & set(csgp_bars))
        window_pairs = _daily_window_pairs(spy_bars, csgp_bars, common_dates)
        window_summaries = [
            _window_summary(window_id, window_label, window_pairs, secondary)
            for (
                window_id,
                window_label,
                _start,
                _end,
                secondary,
            ) in WINDOWS
        ]
        threshold_summaries = [
            _threshold_summary(window_id, window_label, threshold, window_pairs, secondary)
            for window_id, window_label, _start, _end, secondary in WINDOWS
            for threshold in SPY_WEAKNESS_THRESHOLDS
        ]
        strength_threshold_summaries = [
            _strength_threshold_summary(window_id, window_label, threshold, window_pairs, secondary)
            for window_id, window_label, _start, _end, secondary in WINDOWS
            for threshold in SPY_STRENGTH_THRESHOLDS
        ]
        combined_inverse_summaries = [
            _combined_inverse_summary(
                window_id,
                window_label,
                threshold,
                window_pairs,
                secondary,
            )
            for window_id, window_label, _start, _end, secondary in WINDOWS
            for threshold in SPY_WEAKNESS_THRESHOLDS
        ]
        primary_threshold_summaries = [
            summary for summary in threshold_summaries if not summary.secondary_only
        ]
        primary_strength_summaries = [
            summary for summary in strength_threshold_summaries if not summary.secondary_only
        ]
        primary_combined_summaries = [
            summary for summary in combined_inverse_summaries if not summary.secondary_only
        ]
        all_strongest_days = _top_divergence_days(window_pairs, strongest=True)
        all_weakest_days = _top_divergence_days(window_pairs, strongest=False)
        strongest_inverse = _top_inverse_days(window_pairs, strongest=True)
        weakest_inverse = _top_inverse_days(window_pairs, strongest=False)
        follow_through = _follow_through_summary(window_pairs, 0.50)
        strongest_window = _strongest_window(window_summaries)
        csgp_opposite_spy = _opposite_spy_summary(primary_threshold_summaries)
        sample_description = _sample_description(len(common_dates))
        spy_down_summary = _spy_down_csgp_stronger_summary(primary_threshold_summaries)
        spy_up_summary = _spy_up_csgp_weaker_summary(primary_strength_summaries)
        combined_summary = _combined_inverse_plain_summary(primary_combined_summaries)
        bottom_line = _bottom_line(
            primary_threshold_summaries,
            primary_strength_summaries,
            primary_combined_summaries,
            sample_description,
        )
        return SpyCsgpMorningDivergenceStudy(
            data_readiness_summary=_data_readiness_summary(spy_file, csgp_file, common_dates),
            files_used=[spy_file, csgp_file],
            spy_file_range=_date_range_summary("SPY file", spy_file),
            csgp_file_range=_date_range_summary("CSGP file", csgp_file),
            overlap_range_analyzed=_overlap_range_summary(common_dates),
            overlapping_start_date=min(common_dates) if common_dates else None,
            overlapping_end_date=max(common_dates) if common_dates else None,
            trading_dates_analyzed=len(common_dates),
            analyzed_sample_description=sample_description,
            morning_windows_tested=[window_label for _id, window_label, _s, _e, _sec in WINDOWS],
            spy_weakness_thresholds_tested=[
                f"SPY down at least {threshold:.2f}%" for threshold in SPY_WEAKNESS_THRESHOLDS
            ],
            spy_strength_thresholds_tested=[
                f"SPY up at least {threshold:.2f}%" for threshold in SPY_STRENGTH_THRESHOLDS
            ],
            window_summaries=window_summaries,
            threshold_summaries=threshold_summaries,
            strength_threshold_summaries=strength_threshold_summaries,
            combined_inverse_summaries=combined_inverse_summaries,
            spy_down_csgp_stronger_summary=spy_down_summary,
            spy_up_csgp_weaker_summary=spy_up_summary,
            combined_inverse_summary=combined_summary,
            strongest_divergence_days=all_strongest_days,
            weakest_divergence_days=all_weakest_days,
            strongest_inverse_mornings=strongest_inverse,
            weakest_inverse_mornings=weakest_inverse,
            follow_through_summary=follow_through,
            strongest_window_if_any=strongest_window,
            csgp_opposite_spy_plain_english=csgp_opposite_spy,
            bottom_line=bottom_line,
            plain_english_bottom_line=bottom_line,
            what_to_study_next=_what_to_study_next(
                primary_threshold_summaries,
                primary_strength_summaries,
                primary_combined_summaries,
                sample_description,
            ),
        )


def _load_symbol_bars(
    symbol: str,
    path: Path,
) -> tuple[MorningDivergenceFileSummary, dict[date, list[_LocalBar]]]:
    warnings: list[str] = []
    bars_by_date: dict[date, list[_LocalBar]] = {}
    timestamps: list[datetime] = []
    regular_rows = 0
    row_count = 0
    if not path.exists():
        return (
            MorningDivergenceFileSummary(
                symbol=symbol,
                path=str(path),
                exists=False,
                row_count=0,
                regular_hours_rows=0,
                trading_dates=0,
                warnings=[f"{symbol} recent CSV file is missing."],
            ),
            {},
        )

    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        missing_columns = set(REQUIRED_COLUMNS) - set(reader.fieldnames or [])
        if missing_columns:
            warnings.append(f"Missing column(s): {', '.join(sorted(missing_columns))}.")
            return (
                MorningDivergenceFileSummary(
                    symbol=symbol,
                    path=str(path),
                    exists=True,
                    row_count=0,
                    regular_hours_rows=0,
                    trading_dates=0,
                    warnings=warnings,
                ),
                {},
            )
        for row_number, row in enumerate(reader, start=2):
            row_count += 1
            try:
                bar = _parse_bar(symbol, row, row_number)
            except ValueError as error:
                warnings.append(str(error))
                continue
            if not _is_regular_hours(bar.local_time):
                continue
            regular_rows += 1
            timestamps.append(bar.timestamp)
            bars_by_date.setdefault(bar.local_date, []).append(bar)

    for daily_bars in bars_by_date.values():
        daily_bars.sort(key=lambda bar: bar.timestamp)
    dates = sorted(bars_by_date)
    sorted_timestamps = sorted(timestamps)
    return (
        MorningDivergenceFileSummary(
            symbol=symbol,
            path=str(path),
            exists=True,
            row_count=row_count,
            first_timestamp=sorted_timestamps[0] if sorted_timestamps else None,
            last_timestamp=sorted_timestamps[-1] if sorted_timestamps else None,
            first_date=dates[0] if dates else None,
            last_date=dates[-1] if dates else None,
            trading_dates=len(dates),
            regular_hours_rows=regular_rows,
            warnings=warnings,
        ),
        bars_by_date,
    )


def _parse_bar(symbol: str, row: dict[str, str], row_number: int) -> _LocalBar:
    try:
        timestamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
    except (KeyError, ValueError) as error:
        raise ValueError(f"{symbol} row {row_number} has an invalid timestamp.") from error
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=NEW_YORK)
    local_timestamp = timestamp.astimezone(NEW_YORK)
    try:
        open_price = float(row["open"])
        high_price = float(row["high"])
        low_price = float(row["low"])
        close_price = float(row["close"])
    except (KeyError, ValueError) as error:
        raise ValueError(f"{symbol} row {row_number} has invalid price values.") from error
    return _LocalBar(
        symbol=symbol,
        timestamp=timestamp,
        local_date=local_timestamp.date(),
        local_time=local_timestamp.time(),
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
    )


def _is_regular_hours(value: time) -> bool:
    return time(9, 30) <= value < time(16, 0)


def _daily_window_pairs(
    spy_bars: dict[date, list[_LocalBar]],
    csgp_bars: dict[date, list[_LocalBar]],
    common_dates: list[date],
) -> list[_DailyWindowPair]:
    pairs: list[_DailyWindowPair] = []
    for trading_date in common_dates:
        for window_id, window_label, start_time, end_time, secondary in WINDOWS:
            spy_return = _window_return(
                spy_bars[trading_date], trading_date, window_id, window_label, start_time, end_time
            )
            csgp_return = _window_return(
                csgp_bars[trading_date],
                trading_date,
                window_id,
                window_label,
                start_time,
                end_time,
            )
            missing = None
            if spy_return.return_pct is None:
                missing = f"SPY missing {window_label} data"
            elif csgp_return.return_pct is None:
                missing = f"CSGP missing {window_label} data"
            pairs.append(
                _DailyWindowPair(
                    date=trading_date,
                    window_id=window_id,
                    window_label=window_label,
                    spy_return=spy_return.return_pct,
                    csgp_return=csgp_return.return_pct,
                    missing_reason=missing,
                    secondary_only=secondary,
                )
            )
    return pairs


def _window_return(
    bars: list[_LocalBar],
    trading_date: date,
    window_id: str,
    window_label: str,
    start_time: time,
    end_time: time,
) -> MorningWindowReturn:
    start_bar = next((bar for bar in bars if bar.local_time >= start_time), None)
    end_candidates = [bar for bar in bars if bar.local_time <= end_time]
    end_bar = end_candidates[-1] if end_candidates else None
    if start_bar is None or end_bar is None or end_bar.timestamp < start_bar.timestamp:
        return MorningWindowReturn(
            date=trading_date,
            window_id=window_id,
            window_label=window_label,
            missing_reason=f"Missing enough bars for {window_label}.",
        )
    return_pct = ((end_bar.close - start_bar.open) / start_bar.open) * 100
    return MorningWindowReturn(
        date=trading_date,
        window_id=window_id,
        window_label=window_label,
        start_timestamp=start_bar.timestamp,
        end_timestamp=end_bar.timestamp,
        start_price=start_bar.open,
        end_price=end_bar.close,
        return_pct=round(return_pct, 4),
    )


def _window_summary(
    window_id: str,
    window_label: str,
    pairs: list[_DailyWindowPair],
    secondary: bool,
) -> MorningWindowSummary:
    window_pairs = [
        pair
        for pair in pairs
        if pair.window_id == window_id
        and pair.spy_return is not None
        and pair.csgp_return is not None
    ]
    missing_dates = len([pair for pair in pairs if pair.window_id == window_id]) - len(window_pairs)
    spy_moves = [pair.spy_return for pair in window_pairs if pair.spy_return is not None]
    csgp_moves = [pair.csgp_return for pair in window_pairs if pair.csgp_return is not None]
    spy_down_csgp_up = [
        pair
        for pair in window_pairs
        if pair.spy_return is not None
        and pair.csgp_return is not None
        and pair.spy_return < 0 < pair.csgp_return
    ]
    opposite = [pair for pair in window_pairs if _is_inverse_pair(pair)]
    same = [
        pair
        for pair in window_pairs
        if pair.spy_return is not None
        and pair.csgp_return is not None
        and (
            pair.spy_return < 0
            and pair.csgp_return < 0
            or pair.spy_return >= 0
            and pair.csgp_return >= 0
        )
    ]
    stronger = [
        pair
        for pair in window_pairs
        if pair.spy_return is not None
        and pair.csgp_return is not None
        and pair.csgp_return > pair.spy_return
    ]
    return MorningWindowSummary(
        window_id=window_id,
        window_label=window_label,
        dates_analyzed=len(window_pairs),
        missing_dates=missing_dates,
        average_spy_move=_round_optional_mean(spy_moves),
        median_spy_move=_round_optional_median(spy_moves),
        average_csgp_move=_round_optional_mean(csgp_moves),
        median_csgp_move=_round_optional_median(csgp_moves),
        spy_down_csgp_up_count=len(spy_down_csgp_up),
        opposite_direction_count=len(opposite),
        same_direction_count=len(same),
        csgp_held_stronger_count=len(stronger),
        plain_english_summary=_window_plain_english(
            window_label, len(window_pairs), len(opposite), len(stronger)
        ),
        secondary_only=secondary,
    )


def _threshold_summary(
    window_id: str,
    window_label: str,
    threshold: float,
    pairs: list[_DailyWindowPair],
    secondary: bool,
) -> SpyWeaknessThresholdSummary:
    threshold_label = f"SPY down at least {threshold:.2f}%"
    matching_pairs = [
        pair
        for pair in pairs
        if pair.window_id == window_id
        and pair.spy_return is not None
        and pair.csgp_return is not None
        and pair.spy_return <= -threshold
    ]
    spy_moves = [pair.spy_return for pair in matching_pairs if pair.spy_return is not None]
    csgp_moves = [pair.csgp_return for pair in matching_pairs if pair.csgp_return is not None]
    positive = [
        pair for pair in matching_pairs if pair.csgp_return is not None and pair.csgp_return > 0
    ]
    beat_by_1 = [
        pair
        for pair in matching_pairs
        if pair.spy_return is not None
        and pair.csgp_return is not None
        and pair.csgp_return - pair.spy_return >= 1.0
    ]
    beat_by_2 = [
        pair
        for pair in matching_pairs
        if pair.spy_return is not None
        and pair.csgp_return is not None
        and pair.csgp_return - pair.spy_return >= 2.0
    ]
    also_fell = [
        pair for pair in matching_pairs if pair.csgp_return is not None and pair.csgp_return < 0
    ]
    same = [
        pair
        for pair in matching_pairs
        if pair.spy_return is not None
        and pair.csgp_return is not None
        and pair.spy_return < 0
        and pair.csgp_return < 0
    ]
    opposite = positive
    return SpyWeaknessThresholdSummary(
        window_id=window_id,
        window_label=window_label,
        threshold_pct=threshold,
        threshold_label=threshold_label,
        matching_mornings=len(matching_pairs),
        average_spy_move=_round_optional_mean(spy_moves),
        median_spy_move=_round_optional_median(spy_moves),
        average_csgp_move=_round_optional_mean(csgp_moves),
        median_csgp_move=_round_optional_median(csgp_moves),
        csgp_positive_while_spy_negative_count=len(positive),
        csgp_beat_spy_by_1pt_count=len(beat_by_1),
        csgp_beat_spy_by_2pt_count=len(beat_by_2),
        csgp_also_fell_count=len(also_fell),
        same_direction_count=len(same),
        opposite_direction_count=len(opposite),
        behavior_buckets=_behavior_buckets(matching_pairs),
        strongest_divergence_days=_top_divergence_days(matching_pairs, strongest=True),
        weakest_divergence_days=_top_divergence_days(matching_pairs, strongest=False),
        plain_english_summary=_threshold_plain_english(
            window_label,
            threshold_label,
            len(matching_pairs),
            len(positive),
            len(beat_by_1),
        ),
        secondary_only=secondary,
    )


def _strength_threshold_summary(
    window_id: str,
    window_label: str,
    threshold: float,
    pairs: list[_DailyWindowPair],
    secondary: bool,
) -> SpyStrengthThresholdSummary:
    threshold_label = f"SPY up at least {threshold:.2f}%"
    matching_pairs = [
        pair
        for pair in pairs
        if pair.window_id == window_id
        and pair.spy_return is not None
        and pair.csgp_return is not None
        and pair.spy_return >= threshold
    ]
    spy_moves = [pair.spy_return for pair in matching_pairs if pair.spy_return is not None]
    csgp_moves = [pair.csgp_return for pair in matching_pairs if pair.csgp_return is not None]
    negative = [
        pair for pair in matching_pairs if pair.csgp_return is not None and pair.csgp_return < 0
    ]
    lagged_by_1 = [
        pair
        for pair in matching_pairs
        if pair.spy_return is not None
        and pair.csgp_return is not None
        and pair.spy_return - pair.csgp_return >= 1.0
    ]
    lagged_by_2 = [
        pair
        for pair in matching_pairs
        if pair.spy_return is not None
        and pair.csgp_return is not None
        and pair.spy_return - pair.csgp_return >= 2.0
    ]
    also_rose = [
        pair for pair in matching_pairs if pair.csgp_return is not None and pair.csgp_return > 0
    ]
    return SpyStrengthThresholdSummary(
        window_id=window_id,
        window_label=window_label,
        threshold_pct=threshold,
        threshold_label=threshold_label,
        matching_mornings=len(matching_pairs),
        average_spy_move=_round_optional_mean(spy_moves),
        median_spy_move=_round_optional_median(spy_moves),
        average_csgp_move=_round_optional_mean(csgp_moves),
        median_csgp_move=_round_optional_median(csgp_moves),
        csgp_negative_while_spy_positive_count=len(negative),
        csgp_lagged_spy_by_1pt_count=len(lagged_by_1),
        csgp_lagged_spy_by_2pt_count=len(lagged_by_2),
        csgp_also_rose_count=len(also_rose),
        same_direction_count=len(also_rose),
        opposite_direction_count=len(negative),
        strongest_inverse_dates=_top_inverse_days(matching_pairs, strongest=True),
        weakest_inverse_dates=_top_inverse_days(matching_pairs, strongest=False),
        plain_english_summary=_strength_threshold_plain_english(
            window_label,
            threshold_label,
            len(matching_pairs),
            len(negative),
            len(lagged_by_1),
        ),
        secondary_only=secondary,
    )


def _combined_inverse_summary(
    window_id: str,
    window_label: str,
    threshold: float,
    pairs: list[_DailyWindowPair],
    secondary: bool,
) -> CombinedInverseSummary:
    meaningful_pairs = [
        pair
        for pair in pairs
        if pair.window_id == window_id
        and pair.spy_return is not None
        and pair.csgp_return is not None
        and abs(pair.spy_return) >= threshold
    ]
    inverse_pairs = [pair for pair in meaningful_pairs if _is_inverse_pair(pair)]
    same_direction_pairs = [pair for pair in meaningful_pairs if _is_same_direction_pair(pair)]
    spreads = [
        (pair.csgp_return or 0) - (pair.spy_return or 0)
        for pair in meaningful_pairs
        if pair.spy_return is not None and pair.csgp_return is not None
    ]
    down_pairs = [pair for pair in meaningful_pairs if (pair.spy_return or 0) <= -threshold]
    up_pairs = [pair for pair in meaningful_pairs if (pair.spy_return or 0) >= threshold]
    down_inverse = [pair for pair in down_pairs if _is_inverse_pair(pair)]
    up_inverse = [pair for pair in up_pairs if _is_inverse_pair(pair)]
    clearer_side = _clearer_side(
        down_matching=len(down_pairs),
        down_inverse=len(down_inverse),
        up_matching=len(up_pairs),
        up_inverse=len(up_inverse),
    )
    sample_readiness = _sample_readiness(len(meaningful_pairs))
    return CombinedInverseSummary(
        window_id=window_id,
        window_label=window_label,
        threshold_pct=threshold,
        threshold_label=f"SPY up or down at least {threshold:.2f}%",
        total_meaningful_spy_move_mornings=len(meaningful_pairs),
        inverse_mornings_count=len(inverse_pairs),
        inverse_mornings_percent=_percent(len(inverse_pairs), len(meaningful_pairs)),
        same_direction_mornings_count=len(same_direction_pairs),
        same_direction_mornings_percent=_percent(len(same_direction_pairs), len(meaningful_pairs)),
        average_csgp_minus_spy_return_spread=_round_optional_mean(spreads),
        clearer_side=clearer_side,
        sample_readiness=sample_readiness,
        plain_english_summary=_combined_plain_english(
            window_label=window_label,
            threshold=threshold,
            meaningful_count=len(meaningful_pairs),
            inverse_count=len(inverse_pairs),
            clearer_side=clearer_side,
            sample_readiness=sample_readiness,
        ),
        secondary_only=secondary,
    )


def _behavior_buckets(pairs: list[_DailyWindowPair]) -> list[CsgpBehaviorBucket]:
    bucket_counts = {
        "CSGP up at least 3.00%": 0,
        "CSGP up at least 2.00%": 0,
        "CSGP up at least 1.00%": 0,
        "CSGP up at least 0.50%": 0,
        "CSGP positive": 0,
        "CSGP down, but less than SPY": 0,
        "CSGP down as much as or more than SPY": 0,
    }
    for pair in pairs:
        if pair.spy_return is None or pair.csgp_return is None:
            continue
        if pair.csgp_return >= 3.0:
            bucket_counts["CSGP up at least 3.00%"] += 1
        elif pair.csgp_return >= 2.0:
            bucket_counts["CSGP up at least 2.00%"] += 1
        elif pair.csgp_return >= 1.0:
            bucket_counts["CSGP up at least 1.00%"] += 1
        elif pair.csgp_return >= 0.5:
            bucket_counts["CSGP up at least 0.50%"] += 1
        elif pair.csgp_return > 0:
            bucket_counts["CSGP positive"] += 1
        elif pair.csgp_return > pair.spy_return:
            bucket_counts["CSGP down, but less than SPY"] += 1
        else:
            bucket_counts["CSGP down as much as or more than SPY"] += 1
    return [CsgpBehaviorBucket(label=label, count=count) for label, count in bucket_counts.items()]


def _top_divergence_days(
    pairs: list[_DailyWindowPair],
    *,
    strongest: bool,
    limit: int = 5,
) -> list[DivergenceDay]:
    complete_pairs = [
        pair
        for pair in pairs
        if pair.spy_return is not None and pair.csgp_return is not None and not pair.secondary_only
    ]
    ranked = sorted(
        complete_pairs,
        key=lambda pair: (pair.csgp_return or 0) - (pair.spy_return or 0),
        reverse=strongest,
    )
    days: list[DivergenceDay] = []
    for pair in ranked[:limit]:
        if pair.spy_return is None or pair.csgp_return is None:
            continue
        difference = round(pair.csgp_return - pair.spy_return, 4)
        days.append(
            DivergenceDay(
                date=pair.date,
                window_label=pair.window_label,
                spy_move=round(pair.spy_return, 4),
                csgp_move=round(pair.csgp_return, 4),
                csgp_minus_spy=difference,
                plain_english_summary=(
                    f"SPY moved {pair.spy_return:.2f}% and CSGP moved {pair.csgp_return:.2f}% "
                    f"during {pair.window_label}."
                ),
            )
        )
    return days


def _top_inverse_days(
    pairs: list[_DailyWindowPair],
    *,
    strongest: bool,
    limit: int = 5,
) -> list[DivergenceDay]:
    inverse_pairs = [
        pair
        for pair in pairs
        if pair.spy_return is not None
        and pair.csgp_return is not None
        and not pair.secondary_only
        and _is_inverse_pair(pair)
    ]
    ranked = sorted(
        inverse_pairs,
        key=lambda pair: _inverse_gap(pair),
        reverse=strongest,
    )
    days: list[DivergenceDay] = []
    for pair in ranked[:limit]:
        if pair.spy_return is None or pair.csgp_return is None:
            continue
        difference = round(pair.csgp_return - pair.spy_return, 4)
        days.append(
            DivergenceDay(
                date=pair.date,
                window_label=pair.window_label,
                spy_move=round(pair.spy_return, 4),
                csgp_move=round(pair.csgp_return, 4),
                csgp_minus_spy=difference,
                plain_english_summary=(
                    f"SPY moved {pair.spy_return:.2f}% and CSGP moved "
                    f"{pair.csgp_return:.2f}% during {pair.window_label}."
                ),
            )
        )
    return days


def _is_inverse_pair(pair: _DailyWindowPair) -> bool:
    if pair.spy_return is None or pair.csgp_return is None:
        return False
    return pair.spy_return < 0 < pair.csgp_return or pair.spy_return > 0 > pair.csgp_return


def _is_same_direction_pair(pair: _DailyWindowPair) -> bool:
    if pair.spy_return is None or pair.csgp_return is None:
        return False
    return (
        pair.spy_return < 0 and pair.csgp_return < 0 or pair.spy_return > 0 and pair.csgp_return > 0
    )


def _inverse_gap(pair: _DailyWindowPair) -> float:
    if pair.spy_return is None or pair.csgp_return is None:
        return 0.0
    return abs(pair.spy_return - pair.csgp_return)


def _follow_through_summary(
    pairs: list[_DailyWindowPair],
    threshold: float,
) -> FollowThroughSummary:
    early_pairs = {
        pair.date: pair
        for pair in pairs
        if pair.window_id == "open_to_30_minutes"
        and pair.spy_return is not None
        and pair.csgp_return is not None
        and pair.spy_return <= -threshold
    }
    follow_pairs = [
        pair
        for pair in pairs
        if pair.window_id == "follow_through_after_10"
        and pair.date in early_pairs
        and pair.csgp_return is not None
    ]
    continued = [
        pair for pair in follow_pairs if pair.csgp_return is not None and pair.csgp_return > 0
    ]
    gave_back = []
    for pair in follow_pairs:
        early_csgp_return = early_pairs[pair.date].csgp_return
        if (
            pair.csgp_return is not None
            and pair.csgp_return < 0
            and early_csgp_return is not None
            and early_csgp_return > 0
        ):
            gave_back.append(pair)
    mixed = len(follow_pairs) - len(continued) - len(gave_back)
    moves = [pair.csgp_return for pair in follow_pairs if pair.csgp_return is not None]
    return FollowThroughSummary(
        threshold_label=f"SPY down at least {threshold:.2f}% during 9:30-10:00",
        matching_mornings=len(follow_pairs),
        csgp_continued_higher_count=len(continued),
        csgp_gave_back_count=len(gave_back),
        csgp_mixed_count=mixed,
        average_follow_through_move=_round_optional_mean(moves),
        median_follow_through_move=_round_optional_median(moves),
        plain_english_summary=_follow_through_plain_english(
            len(follow_pairs), len(continued), len(gave_back)
        ),
    )


def _data_readiness_summary(
    spy_file: MorningDivergenceFileSummary,
    csgp_file: MorningDivergenceFileSummary,
    common_dates: list[date],
) -> str:
    if not spy_file.exists and not csgp_file.exists:
        return "Recent SPY and CSGP files are missing locally."
    if not spy_file.exists:
        return "Recent SPY file is missing locally."
    if not csgp_file.exists:
        return "Recent CSGP file is missing locally."
    if not common_dates:
        return "Recent SPY and CSGP files exist, but their trading dates do not overlap."
    return (
        f"Recent SPY and CSGP files overlap from {min(common_dates)} to {max(common_dates)} "
        f"with {len(common_dates)} trading days available for local morning research."
    )


def _date_range_summary(
    label: str,
    file_summary: MorningDivergenceFileSummary,
) -> DateRangeSummary:
    if not file_summary.exists:
        return DateRangeSummary(
            first_date=None,
            last_date=None,
            trading_dates=0,
            plain_english_summary=f"{label}: missing locally.",
        )
    if file_summary.first_date is None or file_summary.last_date is None:
        return DateRangeSummary(
            first_date=None,
            last_date=None,
            trading_dates=0,
            plain_english_summary=f"{label}: no usable regular-session dates found.",
        )
    return DateRangeSummary(
        first_date=file_summary.first_date,
        last_date=file_summary.last_date,
        trading_dates=file_summary.trading_dates,
        plain_english_summary=(
            f"{label}: {file_summary.first_date} to {file_summary.last_date} "
            f"with {file_summary.trading_dates} trading dates."
        ),
    )


def _overlap_range_summary(common_dates: list[date]) -> DateRangeSummary:
    if not common_dates:
        return DateRangeSummary(
            first_date=None,
            last_date=None,
            trading_dates=0,
            plain_english_summary="Overlapping date range analyzed: none yet.",
        )
    return DateRangeSummary(
        first_date=min(common_dates),
        last_date=max(common_dates),
        trading_dates=len(common_dates),
        plain_english_summary=(
            f"Overlapping date range analyzed: {min(common_dates)} to {max(common_dates)} "
            f"with {len(common_dates)} trading days."
        ),
    )


def _sample_description(trading_days: int) -> str:
    if trading_days < 60:
        return "Short local sample"
    if trading_days <= 300:
        return "Recent local sample"
    if trading_days <= 600:
        return "Larger recent local sample"
    return "Broader historical local sample"


def _sample_context_sentence(sample_description: str) -> str:
    if sample_description == "Short local sample":
        return "This is a short local sample."
    if sample_description == "Recent local sample":
        return "This is a recent one-year local sample."
    if sample_description == "Larger recent local sample":
        return "This is a larger recent local sample."
    return "This is a broader historical local sample."


def _window_plain_english(
    window_label: str,
    dates_analyzed: int,
    opposite_count: int,
    stronger_count: int,
) -> str:
    if dates_analyzed == 0:
        return f"{window_label}: not enough matching local data."
    return (
        f"{window_label}: CSGP moved up while SPY moved down on {opposite_count} of "
        f"{dates_analyzed} mornings, and held stronger than SPY on {stronger_count} mornings."
    )


def _threshold_plain_english(
    window_label: str,
    threshold_label: str,
    matching_count: int,
    positive_count: int,
    beat_by_1_count: int,
) -> str:
    if matching_count == 0:
        return f"{window_label}, {threshold_label}: too few mornings to judge."
    return (
        f"{window_label}, {threshold_label}: CSGP moved up on {positive_count} of "
        f"{matching_count} weak SPY mornings and held at least 1 point stronger on "
        f"{beat_by_1_count} mornings."
    )


def _strength_threshold_plain_english(
    window_label: str,
    threshold_label: str,
    matching_count: int,
    negative_count: int,
    lagged_by_1_count: int,
) -> str:
    if matching_count == 0:
        return f"{window_label}, {threshold_label}: too few mornings to judge."
    extra = ""
    if matching_count < 10:
        extra = " Interesting clue, but too few examples to rely on by itself."
    return (
        f"{window_label}, {threshold_label}: CSGP moved down on {negative_count} of "
        f"{matching_count} strong SPY mornings and lagged SPY by at least 1 point on "
        f"{lagged_by_1_count} mornings.{extra}"
    )


def _combined_plain_english(
    *,
    window_label: str,
    threshold: float,
    meaningful_count: int,
    inverse_count: int,
    clearer_side: str,
    sample_readiness: str,
) -> str:
    if meaningful_count == 0:
        return (
            f"{window_label}, SPY up or down at least {threshold:.2f}%: too few examples to judge."
        )
    percent = _percent(inverse_count, meaningful_count)
    percent_text = f"{percent:.1f}%" if percent is not None else "0.0%"
    caution = ""
    if sample_readiness == "Too few examples":
        caution = " Interesting clue, but too few examples to rely on by itself."
    return (
        f"{window_label}, SPY up or down at least {threshold:.2f}%: CSGP moved opposite SPY "
        f"on {inverse_count} of {meaningful_count} meaningful SPY mornings "
        f"({percent_text}). {clearer_side}.{caution}"
    )


def _follow_through_plain_english(
    matching_count: int,
    continued_count: int,
    gave_back_count: int,
) -> str:
    if matching_count == 0:
        return "Too few weak SPY mornings during 9:30-10:00 to judge after-10:00 movement."
    if continued_count > gave_back_count:
        return (
            f"After 10:00, CSGP continued higher on {continued_count} of {matching_count} "
            "weak SPY mornings."
        )
    if gave_back_count > continued_count:
        return (
            f"After 10:00, CSGP gave back ground on {gave_back_count} of {matching_count} "
            "weak SPY mornings."
        )
    return "After 10:00, CSGP follow-through was mixed with no clear answer."


def _strongest_window(window_summaries: list[MorningWindowSummary]) -> str:
    primary = [summary for summary in window_summaries if not summary.secondary_only]
    if not primary:
        return "No clear strongest morning window yet."
    strongest = max(primary, key=lambda summary: summary.csgp_held_stronger_count)
    if strongest.csgp_held_stronger_count == 0:
        return "No clear strongest morning window yet."
    return (
        f"{strongest.window_label}, where CSGP held stronger than SPY on "
        f"{strongest.csgp_held_stronger_count} mornings."
    )


def _opposite_spy_summary(threshold_summaries: list[SpyWeaknessThresholdSummary]) -> str:
    useful = [
        summary
        for summary in threshold_summaries
        if summary.window_id == "open_to_30_minutes" and summary.threshold_pct == 0.50
    ]
    if not useful:
        return "Not enough local data to judge whether CSGP often moved opposite SPY."
    summary = useful[0]
    if summary.matching_mornings == 0:
        return "Too few weak SPY mornings to judge whether CSGP often moved opposite SPY."
    return (
        f"During 9:30-10:00 weak SPY mornings, CSGP moved opposite SPY on "
        f"{summary.opposite_direction_count} of {summary.matching_mornings} mornings."
    )


def _spy_down_csgp_stronger_summary(
    threshold_summaries: list[SpyWeaknessThresholdSummary],
) -> str:
    summary = _find_early_050_weak_summary(threshold_summaries)
    if summary is None or summary.matching_mornings == 0:
        return "SPY down / CSGP stronger: too few examples to judge."
    extra = ""
    if summary.matching_mornings < 10:
        extra = " Interesting clue, but too few examples to rely on by itself."
    return (
        "SPY down / CSGP stronger: CSGP moved opposite SPY on "
        f"{summary.opposite_direction_count} of {summary.matching_mornings} matching mornings "
        f"and held at least 1 point stronger on {summary.csgp_beat_spy_by_1pt_count} mornings."
        f"{extra}"
    )


def _spy_up_csgp_weaker_summary(
    strength_summaries: list[SpyStrengthThresholdSummary],
) -> str:
    summary = _find_early_050_strength_summary(strength_summaries)
    if summary is None or summary.matching_mornings == 0:
        return "SPY up / CSGP weaker: too few examples to judge."
    extra = ""
    if summary.matching_mornings < 10:
        extra = " Interesting clue, but too few examples to rely on by itself."
    return (
        "SPY up / CSGP weaker: CSGP moved opposite SPY on "
        f"{summary.opposite_direction_count} of {summary.matching_mornings} matching mornings "
        f"and lagged SPY by at least 1 point on {summary.csgp_lagged_spy_by_1pt_count} mornings."
        f"{extra}"
    )


def _combined_inverse_plain_summary(
    combined_summaries: list[CombinedInverseSummary],
) -> str:
    summary = _find_early_050_combined_summary(combined_summaries)
    if summary is None:
        return "Combined inverse relationship: too few examples to judge."
    return f"Combined inverse relationship: {summary.plain_english_summary}"


def _find_early_050_weak_summary(
    threshold_summaries: list[SpyWeaknessThresholdSummary],
) -> SpyWeaknessThresholdSummary | None:
    return next(
        (
            summary
            for summary in threshold_summaries
            if summary.window_id == "open_to_30_minutes" and summary.threshold_pct == 0.50
        ),
        None,
    )


def _find_early_050_strength_summary(
    strength_summaries: list[SpyStrengthThresholdSummary],
) -> SpyStrengthThresholdSummary | None:
    return next(
        (
            summary
            for summary in strength_summaries
            if summary.window_id == "open_to_30_minutes" and summary.threshold_pct == 0.50
        ),
        None,
    )


def _find_early_050_combined_summary(
    combined_summaries: list[CombinedInverseSummary],
) -> CombinedInverseSummary | None:
    return next(
        (
            summary
            for summary in combined_summaries
            if summary.window_id == "open_to_30_minutes" and summary.threshold_pct == 0.50
        ),
        None,
    )


def _clearer_side(
    *,
    down_matching: int,
    down_inverse: int,
    up_matching: int,
    up_inverse: int,
) -> str:
    if down_matching < 5 and up_matching < 5:
        return "Too few examples on both sides"
    down_rate = down_inverse / down_matching if down_matching else 0
    up_rate = up_inverse / up_matching if up_matching else 0
    if down_matching >= 5 and down_rate >= up_rate + 0.15:
        return "Weak-SPY side looks clearer"
    if up_matching >= 5 and up_rate >= down_rate + 0.15:
        return "Strong-SPY side looks clearer"
    return "Neither side is clearly stronger"


def _sample_readiness(matching_count: int) -> str:
    if matching_count < 10:
        return "Too few examples"
    if matching_count < 30:
        return "Interesting clue"
    return "Worth studying further"


def _percent(count: int, total: int) -> float | None:
    if total == 0:
        return None
    return round((count / total) * 100, 1)


def _bottom_line(
    threshold_summaries: list[SpyWeaknessThresholdSummary],
    strength_summaries: list[SpyStrengthThresholdSummary],
    combined_summaries: list[CombinedInverseSummary],
    sample_description: str,
) -> str:
    weak_summary = _find_early_050_weak_summary(threshold_summaries)
    strong_summary = _find_early_050_strength_summary(strength_summaries)
    combined_summary = _find_early_050_combined_summary(combined_summaries)
    sample_context = _sample_context_sentence(sample_description)
    if combined_summary is None or combined_summary.total_meaningful_spy_move_mornings == 0:
        return f"Too few examples to judge. {sample_context}"
    if combined_summary.total_meaningful_spy_move_mornings < 10:
        return (
            f"CSGP moved opposite SPY on {combined_summary.inverse_mornings_count} of "
            f"{combined_summary.total_meaningful_spy_move_mornings} matching mornings. "
            f"That is an interesting clue, but there are too few examples to rely on by itself. "
            f"{sample_context}"
        )
    weak_rate = (
        weak_summary.opposite_direction_count / weak_summary.matching_mornings
        if weak_summary is not None and weak_summary.matching_mornings
        else 0
    )
    strong_rate = (
        strong_summary.opposite_direction_count / strong_summary.matching_mornings
        if strong_summary is not None and strong_summary.matching_mornings
        else 0
    )
    if weak_rate >= 0.55 and strong_rate >= 0.55:
        return (
            "Both SPY-down and SPY-up mornings showed some inverse CSGP behavior, but the "
            f"sample still needs more review. {sample_context}"
        )
    if weak_rate >= strong_rate + 0.15:
        return (
            "The inverse behavior appears more visible on weak-SPY mornings than strong-SPY "
            f"mornings. {sample_context}"
        )
    if strong_rate >= weak_rate + 0.15:
        return (
            "The inverse behavior appears more visible on strong-SPY mornings than weak-SPY "
            f"mornings. {sample_context}"
        )
    return (
        "EdgeLab found some isolated inverse mornings, but not a consistent pattern across "
        f"windows or thresholds. {sample_context}"
    )


def _what_to_study_next(
    threshold_summaries: list[SpyWeaknessThresholdSummary],
    strength_summaries: list[SpyStrengthThresholdSummary],
    combined_summaries: list[CombinedInverseSummary],
    sample_description: str,
) -> list[str]:
    combined_summary = _find_early_050_combined_summary(combined_summaries)
    next_steps = [
        "Try separating SPY-down mornings from SPY-up mornings.",
        "Look at the strongest inverse dates before creating a narrower rule.",
    ]
    if combined_summary is not None and combined_summary.window_label == "9:30-10:00":
        next_steps.insert(0, "Try focusing on 9:30-10:00 because it had the clearest early clue.")
    if sample_description == "Short local sample":
        next_steps.append(
            "Consider testing a longer local sample if the current sample is too small."
        )
    weak_summary = _find_early_050_weak_summary(threshold_summaries)
    strong_summary = _find_early_050_strength_summary(strength_summaries)
    if (
        weak_summary is not None
        and weak_summary.matching_mornings < 10
        or strong_summary is not None
        and strong_summary.matching_mornings < 10
    ):
        next_steps.append("Do not advance this yet if examples are too few.")
    return next_steps


def _round_optional_mean(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return round(mean(present), 4)


def _round_optional_median(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return round(median(present), 4)
