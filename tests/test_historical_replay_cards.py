from edgelab.intraday.cards import historical_replay_to_markdown_card
from edgelab.intraday.replay import HistoricalIntradayReplayEngine
from edgelab.intraday.replay_schema import HistoricalReplayRequest


def test_replay_card_contains_required_sections_and_real_money_status() -> None:
    result = HistoricalIntradayReplayEngine().replay(
        HistoricalReplayRequest(symbol="RPLAY", session_id="replay-breakout-complete")
    )
    card = historical_replay_to_markdown_card(result)

    for section in [
        "# RPLAY Past Morning Practice Test",
        "## Bottom line",
        "## What EdgeLab would have done in practice mode",
        "## Pretend start and finish",
        "## What happened afterward",
        "## Why this might be misleading",
        "## What EdgeLab should test next",
        "## Real-money status: Not allowed",
        "## Evidence details",
    ]:
        assert section in card
    assert "Not allowed" in card
    assert "Pretend start" in card
    assert "Pretend finish" in card
    assert "Pretend result" in card


def test_replay_card_keeps_primary_sections_plain_english() -> None:
    result = HistoricalIntradayReplayEngine().replay(
        HistoricalReplayRequest(symbol="RPLAY", session_id="replay-breakout-complete")
    )
    card = historical_replay_to_markdown_card(result)
    primary_text = card.split("## Evidence details")[0].lower()

    for phrase in [
        "replay clock",
        "bars visible",
        "setup candidate",
        "signal bar",
        "hypothetical trade",
        "long context",
        "short context",
        "slippage",
        "commission",
        "quality issue",
        "session readiness",
        "entry",
        "exit",
    ]:
        assert phrase not in primary_text


def test_replay_card_has_no_action_instruction_phrases() -> None:
    result = HistoricalIntradayReplayEngine().replay(
        HistoricalReplayRequest(symbol="RPLAY", session_id="replay-breakout-complete")
    )
    card = historical_replay_to_markdown_card(result).lower()

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
    ]:
        assert phrase not in card
