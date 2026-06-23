"""Local SPY/CSGP morning divergence data audit."""

from __future__ import annotations

from datetime import date, timedelta

from edgelab.intraday.csv_normalizers import (
    FirstRateFileDryRunSummary,
    FirstRateLocalCSVHistoricalProvider,
)
from edgelab.intraday.spy_csgp_data_audit_schema import (
    DataImportFileSpec,
    MorningDivergenceWindow,
    SpyCsgpDataAudit,
    SpyCsgpFileAudit,
)

EXPECTED_LOCAL_SYMBOLS = ["SPY", "QQQ", "AAPL", "AMZN", "DIA", "EEM", "META", "MSFT", "TSLA", "VXX"]
TARGET_NORMALIZED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
ACCEPTABLE_ALTERNATIVE_COLUMNS = [
    "datetime",
    "date",
    "time",
    "o",
    "h",
    "l",
    "c",
    "v",
]


class SpyCsgpDataAuditService:
    """Build a read-only data readiness report for the SPY/CSGP morning question."""

    def __init__(
        self,
        provider: FirstRateLocalCSVHistoricalProvider | None = None,
        *,
        as_of: date | None = None,
    ) -> None:
        self.provider = provider or FirstRateLocalCSVHistoricalProvider()
        self.as_of = as_of or date.today()

    def run(self) -> SpyCsgpDataAudit:
        """Return the current local-data audit and first test plan."""

        dry_run = self.provider.dry_run()
        capabilities = self.provider.provider_capabilities()
        file_audits = [_file_audit(file_summary) for file_summary in dry_run.files]
        legacy_spy_summary = _legacy_summary(file_audits, "SPY")
        recent_spy_summary = _recent_summary(file_audits, "SPY")
        recent_csgp_summary = _recent_summary(file_audits, "CSGP")
        spy_summary = recent_spy_summary or legacy_spy_summary or _first_summary(file_audits, "SPY")
        csgp_summary = recent_csgp_summary or _first_summary(file_audits, "CSGP")
        recent_enough = _is_recent_enough(spy_summary, self.as_of)
        recent_pair_has_enough_overlap = _recent_pair_has_enough_overlap(
            recent_spy_summary,
            recent_csgp_summary,
        )

        return SpyCsgpDataAudit(
            audit_id="phase-7x-2s-spy-csgp-morning-divergence-data-audit",
            as_of=self.as_of,
            data_dir=dry_run.data_dir,
            available_symbols=dry_run.symbols_detected,
            expected_symbols=EXPECTED_LOCAL_SYMBOLS,
            files=file_audits,
            spy_data_found=spy_summary is not None,
            csgp_data_found=csgp_summary is not None,
            spy_summary=spy_summary,
            csgp_summary=csgp_summary,
            legacy_spy_summary=legacy_spy_summary,
            recent_spy_summary=recent_spy_summary,
            recent_csgp_summary=recent_csgp_summary,
            recent_pair_has_enough_overlap=recent_pair_has_enough_overlap,
            recent_pair_plain_english=_recent_pair_summary(
                recent_spy_summary,
                recent_csgp_summary,
                recent_pair_has_enough_overlap,
            ),
            current_spy_data_plain_english=_spy_data_summary(spy_summary, recent_enough),
            csgp_data_plain_english=_csgp_data_summary(csgp_summary),
            spy_data_recent_enough_for_last_year_observation=recent_enough,
            recommended_data_window=(
                "Minimum: trailing 12 months. Better: trailing 18 months. "
                "Best practical: trailing 24 months."
            ),
            why_old_and_current_data_should_not_be_mixed=(
                "Old SPY data should not be mixed with current CSGP data because the test "
                "would compare different market periods. EdgeLab needs both files from the "
                "same date range, provider, timestamp convention, and trading-hours treatment."
            ),
            exact_data_needed=[
                "SPY 1-minute bars for the same recent date range as CSGP.",
                "CSGP 1-minute bars for the same recent date range as SPY.",
                (
                    "Regular market hours at minimum, with the same timestamp convention "
                    "in both files."
                ),
                "The same OHLCV fields in both files.",
            ],
            required_files=[
                DataImportFileSpec(
                    symbol="SPY",
                    recommended_path=(
                        "data/raw/historical_intraday/firstratedata/SPY_recent_1min.csv"
                    ),
                    accepted_existing_pattern=(
                        "Any ignored CSV whose filename starts with SPY_ and has the "
                        "required header."
                    ),
                    required_columns=TARGET_NORMALIZED_COLUMNS,
                    acceptable_alternative_columns=ACCEPTABLE_ALTERNATIVE_COLUMNS,
                    plain_english_summary=(
                        "Use a recent SPY one-minute CSV that matches the CSGP file date range."
                    ),
                ),
                DataImportFileSpec(
                    symbol="CSGP",
                    recommended_path=(
                        "data/raw/historical_intraday/firstratedata/CSGP_recent_1min.csv"
                    ),
                    accepted_existing_pattern=(
                        "Any ignored CSV whose filename starts with CSGP_ and has the "
                        "required header."
                    ),
                    required_columns=TARGET_NORMALIZED_COLUMNS,
                    acceptable_alternative_columns=ACCEPTABLE_ALTERNATIVE_COLUMNS,
                    plain_english_summary=(
                        "Use a recent CSGP one-minute CSV that matches the SPY file date range."
                    ),
                ),
            ],
            morning_windows=[
                MorningDivergenceWindow(
                    label="Open to 15 minutes",
                    local_time_window="9:30-9:45",
                    why_it_matters="Checks whether the relationship appears immediately.",
                ),
                MorningDivergenceWindow(
                    label="Open to 30 minutes",
                    local_time_window="9:30-10:00",
                    why_it_matters="Checks whether the relationship needs the first half hour.",
                ),
                MorningDivergenceWindow(
                    label="Open to 60 minutes",
                    local_time_window="9:30-10:30",
                    why_it_matters="Checks whether the first hour is the real window.",
                ),
                MorningDivergenceWindow(
                    label="Follow-through window",
                    local_time_window="10:00-11:00",
                    why_it_matters="Checks whether CSGP keeps moving after the open.",
                ),
                MorningDivergenceWindow(
                    label="Full regular session comparison",
                    local_time_window="9:30-16:00",
                    why_it_matters=(
                        "Secondary comparison only, because the user noticed a morning pattern."
                    ),
                ),
            ],
            spy_weakness_thresholds=[
                "SPY down at least 0.50%",
                "SPY down at least 0.75%",
                "SPY down at least 1.00%",
                "SPY down at least 1.25%",
            ],
            csgp_strength_thresholds=[
                "CSGP up at least 0.50%",
                "CSGP up at least 1.00%",
                "CSGP up at least 2.00%",
                "CSGP up at least 3.00%",
                "CSGP down less than SPY by at least 1.00 percentage point",
                "CSGP positive while SPY is negative",
            ],
            first_study_question=(
                "On mornings when SPY is meaningfully weak early, how often does CSGP move "
                "up or hold stronger than SPY?"
            ),
            future_metrics=[
                "number of matching mornings",
                "how often SPY down / CSGP up occurred",
                "how often SPY down / CSGP also down occurred",
                "average CSGP morning move when SPY was weak",
                "median CSGP morning move when SPY was weak",
                "average difference between CSGP return and SPY return",
                "same-direction count",
                "opposite-direction count",
                "strongest divergence days",
                "weakest divergence days",
                "whether the pattern appears concentrated in specific windows",
                "whether CSGP movement happens immediately at the open or after a delay",
                "whether CSGP continues after 10:00",
            ],
            next_steps=[
                "Obtain matching recent SPY and CSGP one-minute files.",
                "Place both ignored CSVs in data/raw/historical_intraday/firstratedata/.",
                "Run the local dry-run import to confirm both files are readable.",
                "Only after both files match, build the morning divergence study.",
            ],
            provider_supports_external_calls=capabilities.supports_external_calls,
            provider_requires_credentials=capabilities.requires_credentials,
            provider_plain_english_summary=capabilities.plain_english_summary,
        )


def _file_audit(file_summary: FirstRateFileDryRunSummary) -> SpyCsgpFileAudit:
    start_date = file_summary.start_date
    end_date = file_summary.end_date
    readiness_counts = file_summary.readiness_counts
    usable_first_hour_sessions = int(readiness_counts.get("ready_for_replay", 0))
    quality_issue_count = file_summary.quality_issue_count
    session_count = file_summary.session_count
    calendar_days = (
        (end_date - start_date).days + 1
        if start_date is not None and end_date is not None
        else None
    )
    return SpyCsgpFileAudit(
        symbol=file_summary.symbol,
        file_path=file_summary.path,
        filename=file_summary.filename,
        row_count=file_summary.row_count,
        first_timestamp_utc=file_summary.earliest_timestamp_utc,
        last_timestamp_utc=file_summary.latest_timestamp_utc,
        start_date=start_date,
        end_date=end_date,
        calendar_days_covered=calendar_days,
        apparent_trading_sessions=session_count,
        usable_first_hour_sessions=usable_first_hour_sessions,
        first_hour_data_appears_usable=usable_first_hour_sessions > 0,
        readiness_counts=readiness_counts,
        quality_issue_count=quality_issue_count,
        data_quality_warning=_quality_warning(quality_issue_count, session_count),
    )


def _first_summary(file_audits: list[SpyCsgpFileAudit], symbol: str) -> SpyCsgpFileAudit | None:
    for file_audit in file_audits:
        if file_audit.symbol == symbol:
            return file_audit
    return None


def _recent_summary(file_audits: list[SpyCsgpFileAudit], symbol: str) -> SpyCsgpFileAudit | None:
    recent_filename = f"{symbol}_recent_1min.csv"
    for file_audit in file_audits:
        if file_audit.symbol == symbol and file_audit.filename == recent_filename:
            return file_audit
    return None


def _legacy_summary(file_audits: list[SpyCsgpFileAudit], symbol: str) -> SpyCsgpFileAudit | None:
    for file_audit in file_audits:
        if file_audit.symbol == symbol and file_audit.filename != f"{symbol}_recent_1min.csv":
            return file_audit
    return None


def _recent_pair_has_enough_overlap(
    recent_spy_summary: SpyCsgpFileAudit | None,
    recent_csgp_summary: SpyCsgpFileAudit | None,
) -> bool:
    if recent_spy_summary is None or recent_csgp_summary is None:
        return False
    if (
        recent_spy_summary.start_date is None
        or recent_spy_summary.end_date is None
        or recent_csgp_summary.start_date is None
        or recent_csgp_summary.end_date is None
    ):
        return False
    overlap_start = max(recent_spy_summary.start_date, recent_csgp_summary.start_date)
    overlap_end = min(recent_spy_summary.end_date, recent_csgp_summary.end_date)
    return overlap_start <= overlap_end


def _recent_pair_summary(
    recent_spy_summary: SpyCsgpFileAudit | None,
    recent_csgp_summary: SpyCsgpFileAudit | None,
    has_enough_overlap: bool,
) -> str:
    if recent_spy_summary is None and recent_csgp_summary is None:
        return "EdgeLab does not yet see recent SPY or CSGP files for this study."
    if recent_spy_summary is None:
        return "EdgeLab sees recent CSGP data, but recent SPY data is still missing."
    if recent_csgp_summary is None:
        return "EdgeLab sees recent SPY data, but recent CSGP data is still missing."
    if has_enough_overlap:
        return (
            "EdgeLab sees recent SPY and CSGP files with overlapping dates, so the future "
            "morning divergence study has the local files it needs."
        )
    return "EdgeLab sees recent SPY and CSGP files, but their dates do not overlap enough yet."


def _quality_warning(quality_issue_count: int, session_count: int) -> str:
    if quality_issue_count == 0:
        return "No obvious data-quality warning from the local dry run."
    return (
        f"{quality_issue_count} local data-quality issue(s) were found across "
        f"{session_count} apparent session(s). Review before using this file."
    )


def _is_recent_enough(spy_summary: SpyCsgpFileAudit | None, as_of: date) -> bool:
    if spy_summary is None or spy_summary.end_date is None:
        return False
    return spy_summary.end_date >= as_of - timedelta(days=365)


def _spy_data_summary(spy_summary: SpyCsgpFileAudit | None, recent_enough: bool) -> str:
    if spy_summary is None:
        return "EdgeLab does not currently see a local SPY FirstRate CSV file."
    if spy_summary.start_date is None or spy_summary.end_date is None:
        return "EdgeLab sees a SPY file, but its timestamps are not clear enough to judge."
    if recent_enough:
        return (
            f"The current SPY file appears to cover {spy_summary.start_date} through "
            f"{spy_summary.end_date}, so it may be recent enough if matching CSGP data exists."
        )
    return (
        f"The current SPY file appears to cover {spy_summary.start_date} through "
        f"{spy_summary.end_date}, so it is probably too old for a relationship noticed in "
        "the last year."
    )


def _csgp_data_summary(csgp_summary: SpyCsgpFileAudit | None) -> str:
    if csgp_summary is None:
        return "EdgeLab does not currently see a local CSGP FirstRate CSV file."
    return (
        f"EdgeLab sees a CSGP file covering {csgp_summary.start_date} through "
        f"{csgp_summary.end_date}."
    )
