from edgelab.discovery.cards import discovery_to_markdown_card
from edgelab.discovery.library import StrategyDiscoveryLibrary


def test_discovery_card_contains_required_sections() -> None:
    record = StrategyDiscoveryLibrary.with_samples().get("broad-fear-company-calm-pullback")
    assert record is not None

    card = discovery_to_markdown_card(record)

    for section in [
        "## What This Idea Is",
        "## Why It Might Work",
        "## Why It Might Work Now",
        "## What Simpler Idea It Must Beat",
        "## What Evidence Is Needed",
        "## What Would Disprove It",
        "## When It Is Likely Dangerous",
        "## Current Research Status",
        "## Plain-English Caution",
        "## Whether It Is Canonical, Adaptive, Or Novel",
    ]:
        assert section in card


def test_discovery_card_contains_no_action_instruction_phrases() -> None:
    record = StrategyDiscoveryLibrary.with_samples().get("good-news-weak-price-warning")
    assert record is not None

    card = discovery_to_markdown_card(record).lower()

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
    ]:
        assert phrase not in card
