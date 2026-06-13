"""Markdown cards for research-only model portfolios."""

from __future__ import annotations

from collections.abc import Iterable

from edgelab.portfolios.schema import ModelPortfolio, PortfolioHolding


def model_portfolio_to_markdown_card(portfolio: ModelPortfolio) -> str:
    """Render a model portfolio as a plain-English Markdown card."""

    return "\n".join(
        [
            f"# {_simple_portfolio_name(portfolio.name)}",
            "",
            "## Bottom Line",
            portfolio.plain_english_summary,
            "",
            "## What EdgeLab Is Testing",
            portfolio.why_this_portfolio_exists,
            "",
            "## What EdgeLab Would Do In Research Mode",
            (
                "- Keep this as a practice portfolio, re-check whether the included ideas still "
                "make sense, and avoid real-money use."
            ),
            "",
            "## Why Each Holding Appears",
            *_why_holding_lines(portfolio.holdings),
            "",
            "## Why Cash Is Included",
            (
                "- Cash is the part EdgeLab leaves safely unused because the evidence is not "
                "strong enough yet."
            ),
            f"- {portfolio.target_cash.plain_english_reason}",
            "",
            "## What Supports This Test",
            *_bullets(portfolio.what_supports_it),
            "",
            "## What Is Missing",
            *_bullets(portfolio.what_is_missing),
            "",
            "## Why This Might Be Wrong",
            *_bullets(_caution_lines(portfolio)),
            "",
            "## What Would Make Us Reconsider",
            *_bullets(portfolio.what_would_change_our_mind),
            "",
            "## Next Review Item",
            *_bullets(note.future_review_trigger for note in portfolio.monitoring_notes),
            "",
            "## Evidence Details",
            f"- Starting sample amount: ${portfolio.initial_capital:,.2f}",
            (
                f"- Pretend portfolio share left in cash: "
                f"{portfolio.target_cash.target_weight_pct:.1f}% "
                f"(${portfolio.target_cash.target_value:,.2f})"
            ),
            *_holding_lines(portfolio.holdings),
            *_bullets(f"Safety rule: {issue.message}" for issue in portfolio.constraint_issues),
            "",
            "## Real-Money Status",
            f"- Real-money status: {portfolio.real_money_status}",
        ]
    )


def _holding_lines(holdings: list[PortfolioHolding]) -> list[str]:
    return [
        f"- {holding.symbol}: pretend portfolio share {holding.target_weight_pct:.1f}% "
        f"(${holding.target_value:,.2f}) as {holding.role.value.replace('_', ' ')}"
        for holding in holdings
    ] or ["- No practice holdings."]


def _why_holding_lines(holdings: list[PortfolioHolding]) -> list[str]:
    lines: list[str] = []
    for holding in holdings:
        lines.append(
            f"- {holding.symbol}: {holding.plain_english_reason} "
            f"Watch next: {holding.what_to_monitor[0]} "
            f"Why it might be wrong: {holding.what_would_make_us_reconsider[0]} "
            f"Real-money status: {holding.real_money_status}."
        )
    return lines or ["- No practice holding reasons."]


def _caution_lines(portfolio: ModelPortfolio) -> list[str]:
    lines = [issue.message for issue in portfolio.constraint_issues]
    lines.extend(issue.message for issue in portfolio.quality_issues)
    for holding in portfolio.holdings:
        lines.extend(flag.message for flag in holding.risk_flags)
    return lines or ["No additional portfolio-specific cautions beyond sample-data limits."]


def _bullets(items: Iterable[str]) -> list[str]:
    return [f"- {item}" for item in items] or ["- None yet."]


def _simple_portfolio_name(name: str) -> str:
    return (
        name.replace("EdgeLab ", "")
        .replace("Model Portfolio", "Pretend Portfolio Test")
        .replace("Benchmark Comparison", "Comparison Basket")
        .replace("Portfolio", "Test")
    )
