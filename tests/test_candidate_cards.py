from edgelab.candidates.cards import candidate_to_markdown_card
from edgelab.candidates.screener import CandidateEquityScreener


def test_candidate_card_contains_required_sections() -> None:
    candidate = CandidateEquityScreener().get_candidate("spy-research-candidate")
    assert candidate is not None

    card = candidate_to_markdown_card(candidate)

    for section in [
        "## Bottom Line",
        "## Why It Appeared",
        "## What Supports It",
        "## What Is Missing",
        "## What Would Change Our Mind",
        "## Current Status",
        "## Risk And Data Cautions",
        "## Structured Summary",
    ]:
        assert section in card


def test_candidate_card_contains_no_action_instruction_phrases() -> None:
    candidate = CandidateEquityScreener().get_candidate("spy-research-candidate")
    assert candidate is not None
    card = candidate_to_markdown_card(candidate).lower()

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
