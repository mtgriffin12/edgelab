from edgelab.ranking.cards import ranking_scorecard_to_markdown_card
from edgelab.ranking.ranker import StrategyRankingEngine


def test_ranking_card_contains_required_sections() -> None:
    scorecard = StrategyRankingEngine().rank().scorecards[0]

    card = ranking_scorecard_to_markdown_card(scorecard)

    for section in [
        "## Bottom Line",
        "## What Was Evaluated",
        "## Evidence Strength",
        "## Overall Score",
        "## What Helped",
        "## What Hurt",
        "## Baseline Comparison",
        "## Reasons To Be Careful",
        "## What Evidence Is Still Missing",
        "## Current Conclusion",
        "## Real-Money Status",
    ]:
        assert section in card


def test_ranking_card_contains_no_action_instruction_phrases() -> None:
    card = ranking_scorecard_to_markdown_card(StrategyRankingEngine().rank().scorecards[0]).lower()

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
