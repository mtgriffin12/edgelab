import pytest
from pydantic import ValidationError

from edgelab.intraday.cards import (
    intraday_simulation_to_markdown_card,
    prop_account_to_markdown_card,
)
from edgelab.intraday.fixtures import LocalIntradayFixtureProvider
from edgelab.intraday.prop_accounts import (
    PropAccountRuleSet,
    PropAccountSimulationRequest,
    PropAccountSimulationResult,
    PropAccountSimulator,
    sample_prop_account_result,
)
from edgelab.intraday.simulator import IntradaySimulator

FORBIDDEN_ACTION_PHRASES = [
    "buy now",
    "sell now",
    "short now",
    "go short",
    "enter short",
    "enter a trade",
    "place an order",
    "submit an order",
    "execute a trade",
    "open a trade",
    "trade now",
    "ready for real money",
]


def test_prop_account_reaches_qualification_target_when_appropriate() -> None:
    result = PropAccountSimulator().run(
        PropAccountSimulationRequest(daily_net_pnl_values=[1000, 1000, 1200])
    )

    assert result.qualification_target_reached is True
    assert result.max_loss_breached is False
    assert result.daily_loss_breached is False


def test_prop_account_detects_max_and_daily_loss_breaches() -> None:
    result = PropAccountSimulator().run(
        PropAccountSimulationRequest(daily_net_pnl_values=[-1200, -1400])
    )

    assert result.max_loss_breached is True
    assert result.daily_loss_breached is True
    assert result.qualification_target_reached is False


def test_copied_account_scaling_multiplies_pnl_and_warns_about_risk() -> None:
    result = sample_prop_account_result()

    assert result.copied_account_total_net_pnl == result.single_account_net_pnl * 10
    assert any("multiplies mistakes" in caution for caution in result.cautions)
    assert {scenario.account_count for scenario in result.scenarios} == {1, 5, 10, 20}


def test_prop_account_result_rejects_real_money_status_change() -> None:
    with pytest.raises(ValidationError):
        PropAccountSimulationResult(
            account_count=1,
            single_account_net_pnl=0,
            copied_account_total_net_pnl=0,
            qualification_target_reached=False,
            max_loss_breached=False,
            daily_loss_breached=False,
            payout_split_estimate=0,
            plain_english_summary="Generic sample.",
            cautions=["Generic only."],
            real_money_status="Allowed",
        )


def test_intraday_simulation_card_contains_required_sections_and_no_instructions() -> None:
    provider = LocalIntradayFixtureProvider()
    bars, issues = provider.load_bars("GEN_SYN", "generic-symbol-intraday-synthetic")
    assert issues == []

    card = intraday_simulation_to_markdown_card(IntradaySimulator(provider).run(bars))

    for section in [
        "## Bottom Line",
        "## What Happened",
        "## Why It Might Matter",
        "## Why EdgeLab Would Sit Out",
        "## Hypothetical Result",
        "## Reasons To Be Careful",
        "## What Needs Real Historical Testing",
        "## Spike Verdict",
        "## Real-Money Status",
    ]:
        assert section in card
    lowered = card.lower()
    for phrase in FORBIDDEN_ACTION_PHRASES:
        assert phrase not in lowered


def test_prop_account_card_contains_scaling_caution_and_no_instructions() -> None:
    card = prop_account_to_markdown_card(sample_prop_account_result())

    assert "Scaling changes economics" in card
    assert "Real-Money Status" in card
    lowered = card.lower()
    for phrase in FORBIDDEN_ACTION_PHRASES:
        assert phrase not in lowered


def test_prop_account_rules_are_generic() -> None:
    rule_set = PropAccountRuleSet()

    assert rule_set.account_size == 50000
    assert rule_set.qualification_profit_target == 3000
