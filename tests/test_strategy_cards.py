from edgelab.strategies.cards import strategy_to_markdown_card
from edgelab.strategies.samples import SAMPLE_STRATEGIES


def test_strategy_card_contains_required_markdown_sections() -> None:
    card = strategy_to_markdown_card(SAMPLE_STRATEGIES[0])

    for section in [
        "## Strategy",
        "## Current Conclusion",
        "## Why It Exists",
        "## How It Works",
        "## Evidence Required",
        "## Why It Might Fail",
        "## Current Eligibility",
        "## Risk Notes",
        "## Structured Summary",
    ]:
        assert section in card

    assert "Research candidate only" in card
