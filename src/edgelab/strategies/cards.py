"""Markdown strategy card export."""

from edgelab.strategies.schema import StrategySpec


def strategy_to_markdown_card(strategy: StrategySpec) -> str:
    """Convert a strategy spec into an audit-friendly Markdown card."""

    conclusion = _current_conclusion(strategy)
    lines = [
        f"# {strategy.name}",
        "",
        "## Strategy",
        f"- ID: `{strategy.strategy_id}`",
        f"- Status: `{strategy.status.value}`",
        f"- Asset class: `{strategy.asset_class.value}`",
        f"- Direction: `{strategy.direction.value}`",
        f"- Horizon: `{strategy.horizon.value}`",
        "",
        "## Current Conclusion",
        conclusion,
        "",
        "## Why It Exists",
        strategy.thesis,
        "",
        "## How It Works",
        _bullets(
            [
                f"Universe: {strategy.universe.description}",
                f"Holding period: {strategy.holding_period}",
                f"Position sizing: {strategy.position_sizing.description}",
            ]
            + [f"Signal: {signal.name} - {signal.rule}" for signal in strategy.signals]
            + [f"Entry: {rule.name} - {rule.rule}" for rule in strategy.entry_rules]
            + [f"Exit: {rule.name} - {rule.rule}" for rule in strategy.exit_rules]
        ),
        "",
        "## Evidence Required",
        _bullets(
            [
                f"{requirement.name}: {requirement.minimum_threshold}"
                for requirement in strategy.evidence_required
            ]
        ),
        "",
        "## Why It Might Fail",
        _bullets(strategy.failure_conditions),
        "",
        "## Current Eligibility",
        _bullets(
            [
                f"Research: {strategy.eligible_for_research}",
                f"Backtesting: {strategy.eligible_for_backtesting}",
                f"Paper trading: {strategy.eligible_for_paper_trading}",
                f"Live trading: {strategy.eligible_for_live_trading}",
            ]
        ),
        "",
        "## Risk Notes",
        _bullets([f"{rule.name}: {rule.veto_condition}" for rule in strategy.risk_rules]),
        "",
        "## Structured Summary",
        _bullets(
            [
                f"Expected edge: {strategy.expected_edge}",
                f"Rejection reasons: {_format_list(strategy.rejection_reasons)}",
                f"Market regime filter: {_format_regime(strategy)}",
                f"Margin used: {strategy.uses_margin}",
            ]
        ),
        "",
    ]
    return "\n".join(lines)


def _current_conclusion(strategy: StrategySpec) -> str:
    if strategy.eligible_for_live_trading:
        return "Approved for live trading by metadata. This should not occur in Phase 1."
    if strategy.eligible_for_paper_trading:
        return "Eligible for paper trading only. Not eligible for live trading."
    if strategy.eligible_for_backtesting:
        return "Eligible for backtesting review. Not eligible for paper or live trading."
    return "Research candidate only. No paper trading, live trading, or forced exposure."


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _format_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _format_regime(strategy: StrategySpec) -> str:
    if strategy.market_regime_filter is None:
        return "none"
    return strategy.market_regime_filter.description
