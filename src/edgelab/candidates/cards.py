"""Markdown cards for research-only equity candidates."""

from __future__ import annotations

from collections.abc import Iterable

from edgelab.candidates.schema import EquityCandidate


def candidate_to_markdown_card(candidate: EquityCandidate) -> str:
    """Render a candidate as a plain-English Markdown card."""

    return "\n".join(
        [
            f"# {candidate.title}",
            "",
            "## Bottom Line",
            candidate.plain_english_summary,
            "",
            "## Why It Appeared",
            *_bullets(reason.summary for reason in candidate.what_supports_it),
            "",
            "## What Supports It",
            *_bullets(
                [
                    _matched_line("Matched strategy ideas", candidate.matched_strategy_ids),
                    _matched_line("Matched discovery ideas", candidate.matched_discovery_ids),
                    _matched_line("Matched ranking scorecards", candidate.matched_scorecard_ids),
                ]
            ),
            "",
            "## What Is Missing",
            *_bullets(candidate.what_is_missing),
            "",
            "## What Would Change Our Mind",
            *_bullets(candidate.what_would_change_our_mind),
            "",
            "## Current Status",
            f"- Symbol: {candidate.symbol}",
            f"- Candidate score: {candidate.candidate_score:.1f}/100",
            f"- Evidence strength: {candidate.evidence_strength.value.replace('_', ' ')}",
            f"- Status: {candidate.status.value.replace('_', ' ')}",
            f"- Real-money status: {candidate.real_money_status}",
            "",
            "## Risk And Data Cautions",
            *_bullets(_risk_lines(candidate)),
            "",
            "## Structured Summary",
            f"- Candidate ID: {candidate.candidate_id}",
            f"- Market rows: {_market_row_count(candidate)}",
            f"- Sentiment events: {_sentiment_event_count(candidate)}",
            f"- Quality issue count: {len(candidate.quality_issues)}",
            "",
            "This card is a research triage artifact. It does not approve real-money use.",
        ]
    )


def _bullets(items: Iterable[str]) -> list[str]:
    return [f"- {item}" for item in items] or ["- None yet."]


def _matched_line(label: str, values: list[str]) -> str:
    return f"{label}: {', '.join(values) or 'None yet'}"


def _risk_lines(candidate: EquityCandidate) -> list[str]:
    lines = [flag.message for flag in candidate.risk_flags]
    lines.extend(issue.message for issue in candidate.quality_issues)
    return lines or ["No additional candidate-specific caution beyond synthetic sample limits."]


def _market_row_count(candidate: EquityCandidate) -> int | str:
    if candidate.market_snapshot is None:
        return "Not available"
    return candidate.market_snapshot.row_count


def _sentiment_event_count(candidate: EquityCandidate) -> int | str:
    if candidate.sentiment_snapshot is None:
        return "Not available"
    return candidate.sentiment_snapshot.event_count
