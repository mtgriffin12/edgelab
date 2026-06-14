"""Markdown cards for saved research runs."""

from __future__ import annotations

from edgelab.research_runs.schema import ResearchRunFreshness, SavedResearchRun


def saved_research_run_to_markdown_card(
    run: SavedResearchRun,
    freshness: ResearchRunFreshness,
) -> str:
    """Render one saved research run as a plain-English Markdown card."""

    return "\n".join(
        [
            f"# {run.symbol} Latest Saved Result",
            "",
            "## Bottom line",
            run.plain_english_bottom_line,
            "",
            "## What EdgeLab tested",
            run.what_edgelab_tested,
            "",
            "## What EdgeLab found",
            run.what_edgelab_found,
            "",
            "## Is this enough to trust?",
            run.is_this_enough_to_trust,
            "",
            "## What should EdgeLab test next?",
            run.what_to_test_next,
            "",
            "## Freshness status",
            f"- {freshness.status.value.replace('_', ' ')}",
            f"- {freshness.message}",
            "",
            "## Real-money status: Not allowed",
            f"- {run.real_money_status}",
            "",
            "## Evidence details",
            f"- Completed at: {run.completed_at.isoformat()}",
            f"- Source file: {run.source_file_path}",
            f"- Run type: {run.run_type.value.replace('_', ' ')}",
            f"- Hold minutes: {run.hold_minutes}",
            f"- Price friction ticks: {run.slippage_ticks}",
            f"- Transaction cost: {run.commission_per_contract}",
        ]
    )
