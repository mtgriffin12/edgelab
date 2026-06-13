from edgelab.portfolios.cards import model_portfolio_to_markdown_card
from edgelab.portfolios.construction import ModelPortfolioEngine


def test_portfolio_card_contains_required_sections() -> None:
    portfolio = ModelPortfolioEngine().get_portfolio("core-research-portfolio")
    assert portfolio is not None

    card = model_portfolio_to_markdown_card(portfolio)

    for section in [
        "## Bottom Line",
        "## What EdgeLab Is Testing",
        "## What EdgeLab Would Do In Research Mode",
        "## Why Each Holding Appears",
        "## Why Cash Is Included",
        "## What Supports This Test",
        "## What Is Missing",
        "## Why This Might Be Wrong",
        "## What Would Make Us Reconsider",
        "## Next Review Item",
        "## Evidence Details",
        "## Real-Money Status",
    ]:
        assert section in card
    assert "Real-money status: Not allowed" in card


def test_portfolio_card_contains_no_action_instruction_phrases() -> None:
    portfolio = ModelPortfolioEngine().get_portfolio("core-research-portfolio")
    assert portfolio is not None
    card = model_portfolio_to_markdown_card(portfolio).lower()

    for phrase in [
        "buy now",
        "sell now",
        "short now",
        "place an order",
        "submit an order",
        "execute a trade",
        "open a trade",
        "enter a trade",
        "trade now",
        "ready for real money",
    ]:
        assert phrase not in card
