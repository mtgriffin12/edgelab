from edgelab.intraday.cards import multi_session_replay_to_markdown_card
from edgelab.intraday.pattern_results import MultiSessionPatternRunner


def test_multi_session_card_contains_required_plain_english_sections() -> None:
    summary = MultiSessionPatternRunner().run()
    card = multi_session_replay_to_markdown_card(summary)

    for section in [
        "## Bottom line",
        "## What EdgeLab tested",
        "## What usually happened",
        "## Whether anything deserves more testing",
        "## When EdgeLab sat out",
        "## Whether sitting out seemed helpful",
        "## Why this might be misleading",
        "## What EdgeLab should test next",
        "## Real-money status: Not allowed",
        "## Evidence details",
    ]:
        assert section in card
    assert "Not enough examples yet" in card
    assert "Not allowed" in card


def test_multi_session_card_has_no_forbidden_language() -> None:
    summary = MultiSessionPatternRunner().run()
    card = multi_session_replay_to_markdown_card(summary).lower()

    for phrase in [
        "buy now",
        "sell now",
        "short now",
        "go short",
        "enter a trade",
        "place an order",
        "submit an order",
        "execute a trade",
        "open a trade",
        "trade now",
        "profitable",
        "proven",
        "reliable",
        "timely",
        "ready for real money",
    ]:
        assert phrase not in card
