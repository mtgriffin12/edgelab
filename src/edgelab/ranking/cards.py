"""Plain-English ranking cards."""

from edgelab.ranking.schema import StrategyScorecard


def ranking_scorecard_to_markdown_card(scorecard: StrategyScorecard) -> str:
    """Convert a scorecard into a plain-English Markdown card."""

    baseline = scorecard.baseline_comparison
    baseline_text = (
        (
            f"{baseline.improvement_summary}\n\n"
            f"Baseline: {baseline.baseline_description}\n\n"
            f"Caution: {baseline.caution}"
        )
        if baseline is not None
        else "No baseline comparison is available yet."
    )
    return "\n\n".join(
        [
            f"# {scorecard.title}",
            "## Bottom Line",
            scorecard.plain_english_summary,
            "## What Was Evaluated",
            (
                f"Strategy ID: {scorecard.strategy_id or 'none'}. "
                f"Discovery ID: {scorecard.discovery_id or 'none'}."
            ),
            "## Evidence Strength",
            scorecard.evidence_strength.value.replace("_", " "),
            "## Overall Score",
            f"{scorecard.overall_score:.1f}/100",
            "## What Helped",
            _list_items(scorecard.what_helped),
            "## What Hurt",
            _list_items(scorecard.what_hurt),
            "## Baseline Comparison",
            baseline_text,
            "## Reasons To Be Careful",
            scorecard.caution,
            "## What Evidence Is Still Missing",
            _list_items(scorecard.evidence_gaps),
            "## Current Conclusion",
            scorecard.conclusion.value.replace("_", " "),
            "## Real-Money Status",
            "Not allowed.",
        ]
    )


def _list_items(items: list[str]) -> str:
    if not items:
        return "- None recorded yet."
    return "\n".join(f"- {item}" for item in items)
