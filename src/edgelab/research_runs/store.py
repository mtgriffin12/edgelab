"""SQLite storage for saved local research runs."""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from edgelab.research_runs.schema import (
    ResearchRunCreateRequest,
    ResearchRunSummary,
    ResearchRunType,
    SavedResearchRun,
)


def default_research_runs_db_path() -> Path:
    """Return the ignored local SQLite path for saved research runs."""

    return (
        Path(__file__).resolve().parents[3]
        / "data"
        / "processed"
        / "research_runs"
        / "edgelab_research_runs.db"
    )


class SQLiteResearchRunStore:
    """Small stdlib SQLite store for compact saved research results."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or default_research_runs_db_path()

    def initialize(self) -> None:
        """Create the saved-run table if it does not exist."""

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS saved_research_runs (
                    run_id TEXT PRIMARY KEY,
                    run_type TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_file_path TEXT NOT NULL,
                    source_file_size INTEGER NOT NULL,
                    source_file_modified_time INTEGER NOT NULL,
                    source_data_fingerprint TEXT NOT NULL,
                    start_date TEXT,
                    end_date TEXT,
                    hold_minutes INTEGER NOT NULL,
                    slippage_ticks INTEGER NOT NULL,
                    commission_per_contract REAL NOT NULL,
                    run_status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    elapsed_ms INTEGER NOT NULL,
                    summary_result TEXT NOT NULL,
                    first_hour_completeness_summary TEXT NOT NULL,
                    evidence_details TEXT NOT NULL,
                    quality_issues TEXT NOT NULL,
                    plain_english_bottom_line TEXT NOT NULL,
                    what_edgelab_tested TEXT NOT NULL,
                    what_edgelab_found TEXT NOT NULL,
                    is_this_enough_to_trust TEXT NOT NULL,
                    what_to_test_next TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    code_version TEXT NOT NULL,
                    research_only_status TEXT NOT NULL,
                    real_money_status TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_saved_research_runs_latest
                ON saved_research_runs (
                    run_type,
                    symbol,
                    start_date,
                    end_date,
                    hold_minutes,
                    slippage_ticks,
                    commission_per_contract,
                    completed_at DESC
                )
                """
            )

    def insert(self, run: SavedResearchRun) -> SavedResearchRun:
        """Insert or replace one saved research run."""

        self.initialize()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO saved_research_runs (
                    run_id,
                    run_type,
                    symbol,
                    source_name,
                    source_file_path,
                    source_file_size,
                    source_file_modified_time,
                    source_data_fingerprint,
                    start_date,
                    end_date,
                    hold_minutes,
                    slippage_ticks,
                    commission_per_contract,
                    run_status,
                    started_at,
                    completed_at,
                    elapsed_ms,
                    summary_result,
                    first_hour_completeness_summary,
                    evidence_details,
                    quality_issues,
                    plain_english_bottom_line,
                    what_edgelab_tested,
                    what_edgelab_found,
                    is_this_enough_to_trust,
                    what_to_test_next,
                    schema_version,
                    code_version,
                    research_only_status,
                    real_money_status
                ) VALUES (
                    :run_id,
                    :run_type,
                    :symbol,
                    :source_name,
                    :source_file_path,
                    :source_file_size,
                    :source_file_modified_time,
                    :source_data_fingerprint,
                    :start_date,
                    :end_date,
                    :hold_minutes,
                    :slippage_ticks,
                    :commission_per_contract,
                    :run_status,
                    :started_at,
                    :completed_at,
                    :elapsed_ms,
                    :summary_result,
                    :first_hour_completeness_summary,
                    :evidence_details,
                    :quality_issues,
                    :plain_english_bottom_line,
                    :what_edgelab_tested,
                    :what_edgelab_found,
                    :is_this_enough_to_trust,
                    :what_to_test_next,
                    :schema_version,
                    :code_version,
                    :research_only_status,
                    :real_money_status
                )
                """,
                _run_to_row(run),
            )
        return run

    def get(self, run_id: str) -> SavedResearchRun | None:
        """Return one saved run, or None when missing."""

        if not self.db_path.exists():
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM saved_research_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return _row_to_run(row) if row is not None else None

    def list(
        self,
        *,
        run_type: ResearchRunType | None = None,
        symbol: str | None = None,
        limit: int = 50,
    ) -> list[ResearchRunSummary]:
        """List saved runs newest first without creating a missing database."""

        if not self.db_path.exists():
            return []
        where: list[str] = []
        params: list[Any] = []
        if run_type is not None:
            where.append("run_type = ?")
            params.append(run_type.value)
        if symbol is not None:
            where.append("symbol = ?")
            params.append(symbol.strip().upper())
        query = "SELECT * FROM saved_research_runs"
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY completed_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_summary_from_run(_row_to_run(row)) for row in rows]

    def get_latest_matching(self, request: ResearchRunCreateRequest) -> SavedResearchRun | None:
        """Return latest saved run for matching assumptions, or None."""

        if not self.db_path.exists():
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM saved_research_runs
                WHERE run_type = ?
                  AND symbol = ?
                  AND start_date IS ?
                  AND end_date IS ?
                  AND hold_minutes = ?
                  AND slippage_ticks = ?
                  AND commission_per_contract = ?
                ORDER BY completed_at DESC
                LIMIT 1
                """,
                (
                    request.run_type.value,
                    request.symbol,
                    _date_to_text(request.start_date),
                    _date_to_text(request.end_date),
                    request.hold_minutes,
                    request.slippage_ticks,
                    request.commission_per_contract,
                ),
            ).fetchone()
        return _row_to_run(row) if row is not None else None

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection


def _run_to_row(run: SavedResearchRun) -> dict[str, object]:
    return {
        "run_id": run.run_id,
        "run_type": run.run_type.value,
        "symbol": run.symbol,
        "source_name": run.source_name,
        "source_file_path": run.source_file_path,
        "source_file_size": run.source_file_size,
        "source_file_modified_time": run.source_file_modified_time,
        "source_data_fingerprint": run.source_data_fingerprint,
        "start_date": _date_to_text(run.start_date),
        "end_date": _date_to_text(run.end_date),
        "hold_minutes": run.hold_minutes,
        "slippage_ticks": run.slippage_ticks,
        "commission_per_contract": run.commission_per_contract,
        "run_status": run.run_status.value,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat(),
        "elapsed_ms": run.elapsed_ms,
        "summary_result": json.dumps(run.summary_result, sort_keys=True),
        "first_hour_completeness_summary": json.dumps(
            run.first_hour_completeness_summary,
            sort_keys=True,
        ),
        "evidence_details": json.dumps(run.evidence_details, sort_keys=True),
        "quality_issues": json.dumps(
            [issue.model_dump(mode="json") for issue in run.quality_issues],
            sort_keys=True,
        ),
        "plain_english_bottom_line": run.plain_english_bottom_line,
        "what_edgelab_tested": run.what_edgelab_tested,
        "what_edgelab_found": run.what_edgelab_found,
        "is_this_enough_to_trust": run.is_this_enough_to_trust,
        "what_to_test_next": run.what_to_test_next,
        "schema_version": run.schema_version,
        "code_version": run.code_version,
        "research_only_status": run.research_only_status,
        "real_money_status": run.real_money_status,
    }


def _row_to_run(row: sqlite3.Row) -> SavedResearchRun:
    return SavedResearchRun(
        run_id=row["run_id"],
        run_type=row["run_type"],
        symbol=row["symbol"],
        source_name=row["source_name"],
        source_file_path=row["source_file_path"],
        source_file_size=row["source_file_size"],
        source_file_modified_time=row["source_file_modified_time"],
        source_data_fingerprint=row["source_data_fingerprint"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        hold_minutes=row["hold_minutes"],
        slippage_ticks=row["slippage_ticks"],
        commission_per_contract=row["commission_per_contract"],
        run_status=row["run_status"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        elapsed_ms=row["elapsed_ms"],
        summary_result=json.loads(row["summary_result"]),
        first_hour_completeness_summary=json.loads(row["first_hour_completeness_summary"]),
        evidence_details=json.loads(row["evidence_details"]),
        quality_issues=json.loads(row["quality_issues"]),
        plain_english_bottom_line=row["plain_english_bottom_line"],
        what_edgelab_tested=row["what_edgelab_tested"],
        what_edgelab_found=row["what_edgelab_found"],
        is_this_enough_to_trust=row["is_this_enough_to_trust"],
        what_to_test_next=row["what_to_test_next"],
        schema_version=row["schema_version"],
        code_version=row["code_version"],
        research_only_status=row["research_only_status"],
        real_money_status=row["real_money_status"],
    )


def _summary_from_run(run: SavedResearchRun) -> ResearchRunSummary:
    return ResearchRunSummary(
        run_id=run.run_id,
        run_type=run.run_type,
        symbol=run.symbol,
        completed_at=run.completed_at,
        plain_english_bottom_line=run.plain_english_bottom_line,
        run_status=run.run_status,
        real_money_status=run.real_money_status,
    )


def _date_to_text(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None
