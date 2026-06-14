"""Services for running and saving local research results."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from edgelab.intraday.csv_normalizers import (
    FirstRateFileCacheSignature,
    FirstRateLocalCSVHistoricalProvider,
)
from edgelab.intraday.firstrate_replay import (
    CachedFirstRateHistoricalDataProvider,
    FirstHourCompletenessSummary,
    summarize_first_hour_completeness,
)
from edgelab.intraday.historical_schema import utc_now
from edgelab.intraday.pattern_results import MultiSessionPatternRunner
from edgelab.intraday.pattern_results_schema import MultiSessionReplayRequest
from edgelab.intraday.replay import HistoricalIntradayReplayEngine
from edgelab.intraday.schema import normalize_symbol
from edgelab.intraday.setups import IntradaySetupDetector
from edgelab.research_runs.schema import (
    SAVED_RESEARCH_RUN_CODE_VERSION,
    SAVED_RESEARCH_RUN_SCHEMA_VERSION,
    ResearchRunCreateRequest,
    ResearchRunFreshness,
    ResearchRunFreshnessStatus,
    ResearchRunQualityIssue,
    ResearchRunStatus,
    ResearchRunSummary,
    ResearchRunType,
    SavedResearchRun,
)
from edgelab.research_runs.store import SQLiteResearchRunStore


class ResearchRunSourceMissingError(RuntimeError):
    """Raised when a requested local source file or symbol is missing."""


@dataclass(frozen=True)
class SourceSnapshot:
    """Metadata used to detect stale saved results."""

    source_name: str
    path: str
    size_bytes: int
    modified_time_ns: int
    fingerprint: str


class FirstRateResearchRunService:
    """Run FirstRate analyses deliberately and save compact local results."""

    def __init__(
        self,
        *,
        store: SQLiteResearchRunStore | None = None,
        provider: FirstRateLocalCSVHistoricalProvider | None = None,
        setup_detector: IntradaySetupDetector | None = None,
    ) -> None:
        self.store = store or SQLiteResearchRunStore()
        self.provider = provider or FirstRateLocalCSVHistoricalProvider()
        self.setup_detector = setup_detector or IntradaySetupDetector()

    def list_runs(
        self,
        *,
        run_type: ResearchRunType | None = None,
        symbol: str | None = None,
        limit: int = 50,
    ) -> list[ResearchRunSummary]:
        """List saved runs newest first."""

        normalized_symbol = normalize_symbol(symbol) if symbol is not None else None
        return self.store.list(run_type=run_type, symbol=normalized_symbol, limit=limit)

    def get_run(self, run_id: str) -> SavedResearchRun | None:
        """Return one saved run."""

        return self.store.get(run_id)

    def latest_run(self, request: ResearchRunCreateRequest) -> SavedResearchRun | None:
        """Return latest saved run matching request assumptions."""

        return self.store.get_latest_matching(request)

    def run_firstrate_many_morning(self, request: ResearchRunCreateRequest) -> SavedResearchRun:
        """Run the existing local FirstRate many-morning analysis and save the result."""

        if request.run_type != ResearchRunType.FIRSTRATE_MANY_MORNING_REPLAY:
            raise ValueError("unsupported research run type")
        snapshot = self._source_snapshot(request.symbol)
        sessions = self.provider.list_sessions(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        if not sessions:
            raise ResearchRunSourceMissingError(
                "No local FirstRate sessions found for that symbol."
            )

        started_at = utc_now()
        timer_started = perf_counter()
        cached_provider = CachedFirstRateHistoricalDataProvider(self.provider)
        engine = HistoricalIntradayReplayEngine(
            provider=cached_provider,
            setup_detector=self.setup_detector,
        )
        runner = MultiSessionPatternRunner(provider=cached_provider, replay_engine=engine)
        replay_request = MultiSessionReplayRequest(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            hold_minutes=request.hold_minutes,
            slippage_ticks=request.slippage_ticks,
            commission_per_contract=request.commission_per_contract,
        )
        summary = runner.run(replay_request)
        completeness = cached_provider.first_hour_completeness_for_sessions(
            request.symbol,
            request.start_date,
            request.end_date,
        )
        completeness_summary = summarize_first_hour_completeness(completeness)
        elapsed_ms = round((perf_counter() - timer_started) * 1000)
        completed_at = utc_now()

        saved_run = SavedResearchRun(
            run_id=_run_id(request.symbol),
            run_type=request.run_type,
            symbol=request.symbol,
            source_name=snapshot.source_name,
            source_file_path=snapshot.path,
            source_file_size=snapshot.size_bytes,
            source_file_modified_time=snapshot.modified_time_ns,
            source_data_fingerprint=snapshot.fingerprint,
            start_date=request.start_date,
            end_date=request.end_date,
            hold_minutes=request.hold_minutes,
            slippage_ticks=request.slippage_ticks,
            commission_per_contract=request.commission_per_contract,
            run_status=ResearchRunStatus.COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
            elapsed_ms=elapsed_ms,
            summary_result=summary.model_dump(mode="json", exclude={"session_outcomes"}),
            first_hour_completeness_summary=completeness_summary.model_dump(mode="json"),
            evidence_details={
                "sessions_found": summary.sessions_found,
                "sessions_tested": summary.sessions_tested,
                "usable_sessions": summary.usable_sessions,
                "setup_count": summary.setup_count,
                "sit_out_count": summary.sit_out_count,
                "completed_pretend_result_count": summary.completed_pretend_result_count,
                "classification": summary.classification.value,
                "source_file": snapshot.path,
                "schema_version": SAVED_RESEARCH_RUN_SCHEMA_VERSION,
                "code_version": SAVED_RESEARCH_RUN_CODE_VERSION,
            },
            quality_issues=_quality_issues(summary.quality_issues, completeness_summary),
            plain_english_bottom_line=summary.bottom_line,
            what_edgelab_tested=summary.what_edgelab_tested,
            what_edgelab_found=summary.what_usually_happened,
            is_this_enough_to_trust=(
                "No. This is a saved local research result that needs more examples and review "
                "before EdgeLab should trust it."
            ),
            what_to_test_next=summary.what_edgelab_should_test_next,
            schema_version=SAVED_RESEARCH_RUN_SCHEMA_VERSION,
            code_version=SAVED_RESEARCH_RUN_CODE_VERSION,
            research_only_status="Research only",
            real_money_status="Not allowed",
        )
        return self.store.insert(saved_run)

    def freshness_for_run(self, run: SavedResearchRun) -> ResearchRunFreshness:
        """Check whether a saved run still matches its local source and schema."""

        if run.schema_version != SAVED_RESEARCH_RUN_SCHEMA_VERSION:
            return ResearchRunFreshness(
                status=ResearchRunFreshnessStatus.STALE,
                message=(
                    "This saved result may be stale because EdgeLab's saved-result format changed."
                ),
                checked_at=utc_now(),
            )
        try:
            snapshot = self._source_snapshot(run.symbol)
        except ResearchRunSourceMissingError:
            return ResearchRunFreshness(
                status=ResearchRunFreshnessStatus.STALE,
                message="This saved result may be stale because the source file changed.",
                checked_at=utc_now(),
            )
        if (
            snapshot.path != run.source_file_path
            or snapshot.size_bytes != run.source_file_size
            or snapshot.modified_time_ns != run.source_file_modified_time
            or snapshot.fingerprint != run.source_data_fingerprint
        ):
            return ResearchRunFreshness(
                status=ResearchRunFreshnessStatus.STALE,
                message="This saved result may be stale because the source file changed.",
                checked_at=utc_now(),
            )
        return ResearchRunFreshness(
            status=ResearchRunFreshnessStatus.FRESH,
            message="This saved result still matches the local source file and assumptions.",
            checked_at=utc_now(),
        )

    def latest_with_freshness(
        self,
        request: ResearchRunCreateRequest,
    ) -> tuple[SavedResearchRun | None, ResearchRunFreshness]:
        """Return latest matching run with a safe freshness message."""

        run = self.latest_run(request)
        if run is None:
            return None, ResearchRunFreshness(
                status=ResearchRunFreshnessStatus.NOT_FOUND,
                message="No saved local result matches these assumptions yet.",
                checked_at=utc_now(),
            )
        return run, self.freshness_for_run(run)

    def _source_snapshot(self, symbol: str) -> SourceSnapshot:
        normalized_symbol = normalize_symbol(symbol)
        matching = [
            signature
            for signature in self.provider.file_cache_signature()
            if self.provider.normalizer.infer_symbol_from_path(Path(signature.path))
            == normalized_symbol
        ]
        if not matching:
            raise ResearchRunSourceMissingError("No local FirstRate source file found.")
        signature = matching[0]
        return _snapshot_from_signature(self.provider.provider_name, signature)


def _snapshot_from_signature(
    source_name: str,
    signature: FirstRateFileCacheSignature,
) -> SourceSnapshot:
    fingerprint = hashlib.sha256(
        f"{signature.path}|{signature.size_bytes}|{signature.modified_time_ns}".encode()
    ).hexdigest()
    return SourceSnapshot(
        source_name=source_name,
        path=signature.path,
        size_bytes=signature.size_bytes,
        modified_time_ns=signature.modified_time_ns,
        fingerprint=fingerprint,
    )


def _quality_issues(
    summary_issues: list[str],
    completeness_summary: FirstHourCompletenessSummary,
) -> list[ResearchRunQualityIssue]:
    issues = [
        ResearchRunQualityIssue(code="summary_warning", message=message)
        for message in summary_issues
    ]
    if completeness_summary.minor_gaps or completeness_summary.major_gaps:
        issues.append(
            ResearchRunQualityIssue(
                code="first_hour_gaps",
                message=completeness_summary.plain_english_summary,
            )
        )
    if completeness_summary.replay_unsafe:
        issues.append(
            ResearchRunQualityIssue(
                code="first_hour_replay_unsafe",
                message=(
                    "Some local FirstRate mornings have first-hour gaps that are unsafe for "
                    "practice replay."
                ),
            )
        )
    return issues


def _run_id(symbol: str) -> str:
    return f"firstrate-{normalize_symbol(symbol).lower()}-{uuid4().hex[:12]}"
