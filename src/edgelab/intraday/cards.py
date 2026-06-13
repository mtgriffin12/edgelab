"""Markdown cards for intraday research spike outputs."""

from __future__ import annotations

from collections.abc import Iterable

from edgelab.intraday.prop_accounts import PropAccountSimulationResult
from edgelab.intraday.schema import (
    IntradaySetupCandidate,
    IntradaySetupType,
    IntradaySimulationResult,
)


def intraday_setup_to_markdown_card(setup: IntradaySetupCandidate) -> str:
    """Render one intraday setup candidate as plain-English Markdown."""

    return "\n".join(
        [
            f"# {setup.symbol} Intraday Setup Study",
            "",
            "## Bottom Line",
            setup.plain_english_summary,
            "",
            "## What Happened",
            *_bullets(event.plain_english_summary for event in setup.supporting_events),
            "",
            "## Why It Might Matter",
            *_bullets(setup.why_it_appeared),
            "",
            "## Why EdgeLab Would Sit Out",
            *_bullets(_sit_out_lines(setup)),
            "",
            "## Reasons To Be Careful",
            *_bullets(setup.what_is_missing),
            "",
            "## What Needs Real Historical Testing",
            "- Real one-minute intraday data.",
            "- More sessions across different market conditions.",
            "- Out-of-sample replay before any trust increases.",
            "",
            "## Real-Money Status",
            f"- {setup.real_money_status}",
        ]
    )


def intraday_simulation_to_markdown_card(result: IntradaySimulationResult) -> str:
    """Render a simulation result as plain-English Markdown."""

    return "\n".join(
        [
            f"# {result.symbol} Intraday Simulation Study",
            "",
            "## Bottom Line",
            result.plain_english_summary,
            "",
            "## What Happened",
            *_setup_lines(result.setup_candidates),
            "",
            "## Why It Might Matter",
            "- EdgeLab translated chart-like behavior into measurable fixture events.",
            "- The result can be reviewed as research workflow evidence only.",
            "",
            "## Why EdgeLab Would Sit Out",
            *_sit_out_result_lines(result),
            "",
            "## Hypothetical Result",
            *_trade_lines(result),
            "",
            "## Reasons To Be Careful",
            *_bullets(_quality_lines(result)),
            "",
            "## What Needs Real Historical Testing",
            "- Real historical intraday data.",
            "- Replay across many first-hour sessions.",
            "- Separate validation before any paper or live path.",
            "",
            "## Spike Verdict",
            f"- {result.spike_verdict.value.replace('_', ' ')}",
            "",
            "## Real-Money Status",
            f"- {result.real_money_status}",
        ]
    )


def prop_account_to_markdown_card(result: PropAccountSimulationResult) -> str:
    """Render a generic prop-account simulation as Markdown."""

    return "\n".join(
        [
            "# Generic Prop-Account Scaling Study",
            "",
            "## Bottom Line",
            result.plain_english_summary,
            "",
            "## What Happened",
            f"- Single-account sample result: ${result.single_account_net_pnl:,.2f}",
            f"- Copied-account total: ${result.copied_account_total_net_pnl:,.2f}",
            "",
            "## Why It Might Matter",
            "- Scaling changes economics, but it does not create an edge.",
            "- The same result repeated across accounts can enlarge both outcomes and mistakes.",
            "",
            "## Hypothetical Result",
            f"- Qualification target reached: {_yes_no(result.qualification_target_reached)}",
            f"- Max loss breached: {_yes_no(result.max_loss_breached)}",
            f"- Daily loss breached: {_yes_no(result.daily_loss_breached)}",
            f"- Payout split estimate: ${result.payout_split_estimate:,.2f}",
            "",
            "## Reasons To Be Careful",
            *_bullets(result.cautions),
            "",
            "## What Needs Real Historical Testing",
            "- A real historical sequence of intraday outcomes.",
            "- Program-specific rules reviewed outside this generic model.",
            "- Evidence that the underlying setup has durable behavior.",
            "",
            "## Real-Money Status",
            f"- {result.real_money_status}",
        ]
    )


def _setup_lines(setups: list[IntradaySetupCandidate]) -> list[str]:
    return [f"- {setup.plain_english_summary}" for setup in setups] or ["- No setup was selected."]


def _sit_out_result_lines(result: IntradaySimulationResult) -> list[str]:
    lines: list[str] = []
    for setup in result.setup_candidates:
        lines.extend(_sit_out_lines(setup))
    return [f"- {line}" for line in lines] or ["- No sit-out reason was triggered in this fixture."]


def _sit_out_lines(setup: IntradaySetupCandidate) -> list[str]:
    lines = [reason.message for reason in setup.no_trade_reasons]
    if setup.setup_type != IntradaySetupType.NO_TRADE:
        lines.extend(setup.why_edgelab_might_sit_out)
    return lines or ["No sit-out reason was triggered in this fixture."]


def _trade_lines(result: IntradaySimulationResult) -> list[str]:
    if not result.hypothetical_trades:
        return ["- No hypothetical result was calculated."]
    return [
        f"- {trade.symbol}: {trade.result_label} ${trade.net_pnl:,.2f} net over the fixture hold."
        for trade in result.hypothetical_trades
    ]


def _quality_lines(result: IntradaySimulationResult) -> list[str]:
    return [issue.message for issue in result.quality_issues] or [
        "No additional fixture quality issues were reported."
    ]


def _bullets(items: Iterable[str]) -> list[str]:
    return [f"- {item}" for item in items] or ["- None."]


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"
