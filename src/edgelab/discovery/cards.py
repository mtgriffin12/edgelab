"""Plain-English strategy discovery cards."""

from edgelab.discovery.schema import StrategyDiscoveryRecord


def discovery_to_markdown_card(record: StrategyDiscoveryRecord) -> str:
    """Convert a discovery record into a plain-English Markdown card."""

    lines = [
        f"# {record.title}",
        "",
        "## What This Idea Is",
        record.plain_english_summary,
        "",
        "## Why It Might Work",
        record.why_it_might_work,
        "",
        "## Why It Might Work Now",
        record.why_it_might_work_now,
        "",
        "## What Simpler Idea It Must Beat",
        f"{record.baseline_to_beat.description} It must beat: {record.baseline_to_beat.must_beat}",
        "",
        "## What Evidence Is Needed",
        _bullets(record.evidence_needed),
        "",
        "## What Would Disprove It",
        _bullets(record.disproof_conditions),
        "",
        "## When It Is Likely Dangerous",
        _bullets(record.worst_market_conditions),
        "",
        "## Current Research Status",
        f"{record.status.value}. No automatic promotion is allowed.",
        "",
        "## Plain-English Caution",
        (
            "This is a research hypothesis only. It must survive baseline comparison, local "
            "historical testing, and robustness review before it can be treated as a serious "
            "candidate."
        ),
        "",
        "## Whether It Is Canonical, Adaptive, Or Novel",
        f"Provenance: {record.provenance.value}. Lane: {record.lane.value}.",
        "",
    ]
    return "\n".join(lines)


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)
