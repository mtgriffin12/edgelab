"""Placeholder monitoring notes for model portfolios."""

from __future__ import annotations

from edgelab.portfolios.schema import ModelPortfolio, PortfolioHolding, PortfolioMonitoringNote


def build_monitoring_notes(
    portfolio_id: str,
    holdings: list[PortfolioHolding],
) -> list[PortfolioMonitoringNote]:
    """Create future review notes without action instructions."""

    notes = [
        PortfolioMonitoringNote(
            note_id=f"{portfolio_id}-cash",
            portfolio_id=portfolio_id,
            severity="caution",
            plain_english_note="Re-check if model cash falls below the minimum.",
            what_to_watch="Cash left safely unused versus the minimum cash rule.",
            why_it_matters="Cash is an intentional safety choice in this phase.",
            future_review_trigger="Cash left safely unused drops below the configured minimum.",
        ),
        PortfolioMonitoringNote(
            note_id=f"{portfolio_id}-data",
            portfolio_id=portfolio_id,
            severity="warning",
            plain_english_note="Re-check if data quality becomes unreliable.",
            what_to_watch="Fixture quality issues and missing candidate evidence.",
            why_it_matters="Weak data can make a practice portfolio look cleaner than it is.",
            future_review_trigger="Any candidate or fixture quality issue becomes blocking.",
        ),
    ]
    notes.extend(_holding_note(portfolio_id, holding) for holding in holdings)
    return notes


def notes_for_portfolio(portfolio: ModelPortfolio) -> list[PortfolioMonitoringNote]:
    """Return notes already attached to a model portfolio."""

    return portfolio.monitoring_notes


def _holding_note(portfolio_id: str, holding: PortfolioHolding) -> PortfolioMonitoringNote:
    return PortfolioMonitoringNote(
        note_id=f"{portfolio_id}-{holding.symbol.lower()}",
        portfolio_id=portfolio_id,
        symbol=holding.symbol,
        severity="info",
        plain_english_note=(
            f"Re-check {holding.symbol} if it no longer matches its inclusion reason."
        ),
        what_to_watch="Candidate score, evidence strength, market mood context, and risk flags.",
        why_it_matters="A model holding should keep matching the reason it appeared.",
        future_review_trigger=(
            "Candidate support weakens or the holding grows beyond its safe size."
        ),
    )
