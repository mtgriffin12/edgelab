from edgelab.intraday.discovery_sprint_schema import SupportedRuleFamily
from edgelab.intraday.strategy_library import fixed_intraday_strategy_ideas, strategy_by_id_or_slug


def test_fixed_intraday_strategy_library_contains_eight_supported_ideas() -> None:
    ideas = fixed_intraday_strategy_ideas()

    assert [idea.strategy_id for idea in ideas] == [
        SupportedRuleFamily.FAILED_EARLY_MOVE,
        SupportedRuleFamily.GAP_FADE,
        SupportedRuleFamily.GAP_CONTINUATION,
        SupportedRuleFamily.FIRST_15_MINUTE_BREAKOUT,
        SupportedRuleFamily.FIRST_30_MINUTE_BREAKOUT,
        SupportedRuleFamily.OPENING_RANGE_RECLAIM,
        SupportedRuleFamily.STRONG_OPEN_WEAK_FOLLOW_THROUGH,
        SupportedRuleFamily.SPY_QQQ_DIVERGENCE,
    ]
    assert len({idea.url_slug for idea in ideas}) == 8
    assert all(idea.research_only_status == "Research only" for idea in ideas)
    assert all(idea.real_money_status == "Not allowed" for idea in ideas)


def test_strategy_lookup_accepts_ids_and_url_slugs() -> None:
    assert strategy_by_id_or_slug("failed_early_move").url_slug == "failed-early-move"
    assert strategy_by_id_or_slug("failed-early-move").strategy_id == (
        SupportedRuleFamily.FAILED_EARLY_MOVE
    )
    assert strategy_by_id_or_slug("missing-idea") is None
