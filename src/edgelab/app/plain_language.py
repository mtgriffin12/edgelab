"""Plain-English UX language for EdgeLab."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlainLanguageTerm:
    """Plain-language explanation for a technical UI term."""

    technical_key: str
    plain_label: str
    short_explanation: str
    why_it_matters: str
    caution: str | None = None


PLAIN_LANGUAGE_TERMS: dict[str, PlainLanguageTerm] = {
    "backtest": PlainLanguageTerm(
        technical_key="backtest",
        plain_label="Historical Test",
        short_explanation="A replay of an idea against past sample prices.",
        why_it_matters="It helps decide whether an idea deserves more careful testing.",
        caution="Past sample behavior is not proof that the idea works.",
    ),
    "max_drawdown_pct": PlainLanguageTerm(
        technical_key="max_drawdown_pct",
        plain_label="Worst Drop",
        short_explanation="The largest fall from a high point during the test.",
        why_it_matters="Large drops can make a strategy hard to trust or continue using.",
    ),
    "total_return_pct": PlainLanguageTerm(
        technical_key="total_return_pct",
        plain_label="Total Change",
        short_explanation="How much the test account rose or fell overall.",
        why_it_matters="It shows direction and size of the result before deeper checks.",
    ),
    "profit_factor": PlainLanguageTerm(
        technical_key="profit_factor",
        plain_label="Gain/Loss Ratio",
        short_explanation="How much simulated gain appeared for each unit of simulated loss.",
        why_it_matters=(
            "A higher ratio can suggest a cleaner pattern, but only with enough examples."
        ),
        caution="This can look too good when there are very few completed examples.",
    ),
    "win_rate_pct": PlainLanguageTerm(
        technical_key="win_rate_pct",
        plain_label="Helpful Outcome Rate",
        short_explanation="How often completed test examples ended positive.",
        why_it_matters="It shows consistency, but not the size of gains or losses.",
    ),
    "exposure_pct": PlainLanguageTerm(
        technical_key="exposure_pct",
        plain_label="Time at Risk",
        short_explanation="How often the test had money committed in the simulation.",
        why_it_matters="More time at risk can mean more chances for unexpected losses.",
    ),
    "equity_curve": PlainLanguageTerm(
        technical_key="equity_curve",
        plain_label="Account Path",
        short_explanation="The test account value recorded through time.",
        why_it_matters="It shows whether results were steady, choppy, or fragile.",
    ),
    "slippage": PlainLanguageTerm(
        technical_key="slippage",
        plain_label="Price Friction",
        short_explanation="A small penalty for not getting the exact displayed price.",
        why_it_matters="Realistic price friction can turn weak ideas negative.",
    ),
    "commission": PlainLanguageTerm(
        technical_key="commission",
        plain_label="Transaction Cost",
        short_explanation="A cost charged for each simulated transaction.",
        why_it_matters="Costs matter because small edges can disappear after expenses.",
    ),
    "sentiment": PlainLanguageTerm(
        technical_key="sentiment",
        plain_label="Market Mood",
        short_explanation=(
            "Timestamped context about how news or crowd behavior looked in the sample."
        ),
        why_it_matters=(
            "Mood can explain the background around an idea without becoming an instruction."
        ),
    ),
    "weighted_sentiment_score": PlainLanguageTerm(
        technical_key="weighted_sentiment_score",
        plain_label="Importance-Adjusted Mood",
        short_explanation="A mood score that gives stronger sources more influence.",
        why_it_matters=(
            "It prevents every sample event from counting equally when confidence differs."
        ),
    ),
    "decayed_sentiment_score": PlainLanguageTerm(
        technical_key="decayed_sentiment_score",
        plain_label="Freshness-Adjusted Mood",
        short_explanation="A mood score that fades older events toward zero.",
        why_it_matters="Old context should matter less than newer context.",
    ),
    "dominant_event_type": PlainLanguageTerm(
        technical_key="dominant_event_type",
        plain_label="Main Event Type",
        short_explanation="The most common type of mood event in the current sample.",
        why_it_matters="It quickly explains what kind of story is driving the context.",
    ),
    "divergence_flags": PlainLanguageTerm(
        technical_key="divergence_flags",
        plain_label="Mixed-Signal Warnings",
        short_explanation="Signs that different mood sources disagree.",
        why_it_matters="Disagreement is a reason to slow down and ask for more evidence.",
    ),
    "quality_issues": PlainLanguageTerm(
        technical_key="quality_issues",
        plain_label="Reasons to Be Careful",
        short_explanation="Data or test warnings that could weaken the conclusion.",
        why_it_matters="Good research should show the weak spots before showing confidence.",
    ),
    "eligible_for_backtesting": PlainLanguageTerm(
        technical_key="eligible_for_backtesting",
        plain_label="Allowed to Use Historical Tests",
        short_explanation="Whether the idea is ready for the local historical test layer.",
        why_it_matters="Ideas should not move forward until their rules are clear enough to test.",
    ),
    "eligible_for_paper_trading": PlainLanguageTerm(
        technical_key="eligible_for_paper_trading",
        plain_label="Allowed to Use Paper Simulation",
        short_explanation="Whether the idea can move into a future simulated monitoring phase.",
        why_it_matters="Paper simulation should require evidence, not enthusiasm.",
    ),
    "eligible_for_live_trading": PlainLanguageTerm(
        technical_key="eligible_for_live_trading",
        plain_label="Allowed to Use Real Money",
        short_explanation="Whether the idea is allowed anywhere near real-money execution.",
        why_it_matters="This must stay conservative and explicit.",
        caution="Phase 5B should always show No.",
    ),
    "research_only": PlainLanguageTerm(
        technical_key="research_only",
        plain_label="Research Only",
        short_explanation="The result can inform learning, but cannot trigger action.",
        why_it_matters="It keeps evidence separate from execution.",
    ),
    "unsupported_strategy": PlainLanguageTerm(
        technical_key="unsupported_strategy",
        plain_label="Not Testable Yet",
        short_explanation="The current simple engine does not know how to evaluate this idea.",
        why_it_matters="Unsupported ideas should be shown honestly instead of approximated.",
    ),
    "insufficient_evidence": PlainLanguageTerm(
        technical_key="insufficient_evidence",
        plain_label="Not Enough Evidence",
        short_explanation="The current sample does not support a strong conclusion.",
        why_it_matters="Weak evidence should stop an idea from advancing too quickly.",
    ),
    "fixture_data": PlainLanguageTerm(
        technical_key="fixture_data",
        plain_label="Built-In Sample Data",
        short_explanation="Small local data files included with the app for testing behavior.",
        why_it_matters=(
            "It keeps development local, repeatable, and independent of outside services."
        ),
        caution="Built-in sample data is not live market data.",
    ),
    "synthetic_data": PlainLanguageTerm(
        technical_key="synthetic_data",
        plain_label="Synthetic Sample Data",
        short_explanation="Artificial data made for local testing, not real market history.",
        why_it_matters="It lets the app prove its workflow before real providers are added.",
        caution="Synthetic sample data should never be treated as market evidence.",
    ),
    "strategy_discovery_lab": PlainLanguageTerm(
        technical_key="strategy_discovery_lab",
        plain_label="Strategy Discovery Lab",
        short_explanation="A place to sort known ideas and new hypotheses before deeper testing.",
        why_it_matters="It keeps creativity separate from evidence and prevents premature trust.",
    ),
    "known_strategy_library": PlainLanguageTerm(
        technical_key="known_strategy_library",
        plain_label="Known Strategy Library",
        short_explanation=(
            "Historically discussed strategy families that still need current evidence."
        ),
        why_it_matters="Known ideas are allowed, but they still need proof in the current context.",
    ),
    "edge_innovation_lab": PlainLanguageTerm(
        technical_key="edge_innovation_lab",
        plain_label="Edge Innovation Lab",
        short_explanation="Adaptive and novel ideas that must beat simpler baselines.",
        why_it_matters="New ideas can be useful, but novelty alone is not evidence.",
    ),
    "baseline_to_beat": PlainLanguageTerm(
        technical_key="baseline_to_beat",
        plain_label="Simpler Idea to Beat",
        short_explanation="The simpler comparison that a more complex idea must improve on.",
        why_it_matters=(
            "Complex ideas should earn their complexity by beating simpler alternatives."
        ),
    ),
    "current_regime_fit": PlainLanguageTerm(
        technical_key="current_regime_fit",
        plain_label="Environment Fit",
        short_explanation=(
            "A scaffolded read on whether conditions resemble the idea's preferred setup."
        ),
        why_it_matters="An idea can be reasonable but poorly timed for the current environment.",
    ),
    "overfitting_risk_score": PlainLanguageTerm(
        technical_key="overfitting_risk_score",
        plain_label="Curve-Fit Risk",
        short_explanation=(
            "How likely an idea is to look good only because it was over-shaped to data."
        ),
        why_it_matters="High curve-fit risk means the idea needs stricter testing.",
    ),
    "novelty_score": PlainLanguageTerm(
        technical_key="novelty_score",
        plain_label="Newness",
        short_explanation="How different the idea is from familiar strategy families.",
        why_it_matters="Newness can create hypotheses, but it does not make them good.",
    ),
    "complexity_score": PlainLanguageTerm(
        technical_key="complexity_score",
        plain_label="Complexity",
        short_explanation="How many moving parts the idea depends on.",
        why_it_matters="More moving parts usually require stronger evidence.",
    ),
    "ranking": PlainLanguageTerm(
        technical_key="ranking",
        plain_label="Research Ranking",
        short_explanation="A conservative ordering of ideas by evidence quality.",
        why_it_matters="It helps decide what deserves deeper testing next.",
    ),
    "evidence_strength": PlainLanguageTerm(
        technical_key="evidence_strength",
        plain_label="Evidence Strength",
        short_explanation="How much confidence the current research evidence deserves.",
        why_it_matters=(
            "Weak evidence should slow an idea down, even when numbers look interesting."
        ),
    ),
    "overall_score": PlainLanguageTerm(
        technical_key="overall_score",
        plain_label="Overall Research Score",
        short_explanation="A 0-100 score that blends return, risk, sample size, and caution.",
        why_it_matters="It prevents one shiny metric from deciding the ranking alone.",
    ),
    "baseline_comparison": PlainLanguageTerm(
        technical_key="baseline_comparison",
        plain_label="Simpler Comparison",
        short_explanation="The simpler idea that a more complex idea must improve on.",
        why_it_matters="Complexity should only survive when it adds evidence.",
    ),
    "top_research_candidate": PlainLanguageTerm(
        technical_key="top_research_candidate",
        plain_label="Top Research Candidate",
        short_explanation="An idea that may deserve more testing before anything else.",
        why_it_matters="This is about research priority, not action.",
    ),
    "weak_candidate": PlainLanguageTerm(
        technical_key="weak_candidate",
        plain_label="Weak Candidate",
        short_explanation="An idea with thin, fragile, unsupported, or insufficient evidence.",
        why_it_matters="Weak ideas should stay visible so they can be improved or rejected.",
    ),
    "promising_research_candidate": PlainLanguageTerm(
        technical_key="promising_research_candidate",
        plain_label="Promising Research Candidate",
        short_explanation="An idea that looks worth deeper testing, not real-money use.",
        why_it_matters="Promising still means unproven.",
    ),
    "overfitting_risk": PlainLanguageTerm(
        technical_key="overfitting_risk",
        plain_label="Curve-Fit Risk",
        short_explanation="The risk that an idea only looks good because it was shaped to samples.",
        why_it_matters="High curve-fit risk needs stricter testing.",
    ),
    "cost_sensitivity": PlainLanguageTerm(
        technical_key="cost_sensitivity",
        plain_label="Cost Fragility",
        short_explanation="How much fees or price friction could weaken the idea.",
        why_it_matters="Small edges can disappear after costs.",
    ),
    "sample_size": PlainLanguageTerm(
        technical_key="sample_size",
        plain_label="Sample Size",
        short_explanation="How many completed examples support the result.",
        why_it_matters="A tiny sample can make weak evidence look stronger than it is.",
    ),
    "return_quality": PlainLanguageTerm(
        technical_key="return_quality",
        plain_label="Return Quality",
        short_explanation="Whether the result improved without relying on one flashy number.",
        why_it_matters="Return must be judged alongside risk and evidence quality.",
    ),
    "worst_drop_control": PlainLanguageTerm(
        technical_key="worst_drop_control",
        plain_label="Worst Drop Control",
        short_explanation="How well the idea avoided painful sample declines.",
        why_it_matters="Large drops can make good-looking returns fragile.",
    ),
    "consistency": PlainLanguageTerm(
        technical_key="consistency",
        plain_label="Consistency",
        short_explanation="Whether the sample looked steady enough to keep studying.",
        why_it_matters="A few lucky events are not durable evidence.",
    ),
    "candidate": PlainLanguageTerm(
        technical_key="candidate",
        plain_label="Research Candidate",
        short_explanation="A symbol that may deserve more research based on local evidence.",
        why_it_matters="It helps focus attention without becoming an action instruction.",
    ),
    "research_candidate": PlainLanguageTerm(
        technical_key="research_candidate",
        plain_label="Worth More Research",
        short_explanation="Interesting enough to examine more deeply, but still unproven.",
        why_it_matters="Research priority is not permission for real-money use.",
    ),
    "watchlist_only": PlainLanguageTerm(
        technical_key="watchlist_only",
        plain_label="Watchlist Only",
        short_explanation="Keep visible for learning, but do not treat as strong evidence.",
        why_it_matters="Some ideas are worth remembering even when confidence is low.",
    ),
    "interesting_but_incomplete": PlainLanguageTerm(
        technical_key="interesting_but_incomplete",
        plain_label="Interesting but Incomplete",
        short_explanation="Some evidence points in a useful direction, but key proof is missing.",
        why_it_matters="It prevents a partial story from sounding complete.",
    ),
    "blocked_by_risk": PlainLanguageTerm(
        technical_key="blocked_by_risk",
        plain_label="Blocked by Risk",
        short_explanation="Safety concerns stop the idea from advancing.",
        why_it_matters="Risk controls should be able to veto weak or unsafe evidence.",
    ),
    "blocked_by_data_quality": PlainLanguageTerm(
        technical_key="blocked_by_data_quality",
        plain_label="Blocked by Data Quality",
        short_explanation="The data is too weak or flawed for useful interpretation.",
        why_it_matters="Bad data can make a weak idea look better than it is.",
    ),
    "research_watchlist": PlainLanguageTerm(
        technical_key="research_watchlist",
        plain_label="Research Watchlist",
        short_explanation="A short list of symbols to keep studying.",
        why_it_matters="It keeps attention organized without implying action.",
    ),
    "market_context": PlainLanguageTerm(
        technical_key="market_context",
        plain_label="Market Context",
        short_explanation="Local sample price and volume background for a symbol.",
        why_it_matters="A candidate needs context before its evidence can be interpreted.",
    ),
    "market_mood_context": PlainLanguageTerm(
        technical_key="market_mood_context",
        plain_label="Market Mood Context",
        short_explanation="Local sample sentiment background for a symbol.",
        why_it_matters="Mood can explain conditions, but it is not a command to act.",
    ),
    "what_supports_it": PlainLanguageTerm(
        technical_key="what_supports_it",
        plain_label="What Supports It",
        short_explanation="The local evidence that caused a symbol to appear.",
        why_it_matters="Every candidate should explain why it exists.",
    ),
    "what_is_missing": PlainLanguageTerm(
        technical_key="what_is_missing",
        plain_label="What Is Missing",
        short_explanation="The evidence gaps that keep the candidate from being trusted.",
        why_it_matters="Missing evidence is often more important than the current score.",
    ),
    "what_would_change_our_mind": PlainLanguageTerm(
        technical_key="what_would_change_our_mind",
        plain_label="What Would Change Our Mind",
        short_explanation="Conditions that would weaken or reject the candidate.",
        why_it_matters="Good research defines how it can be wrong.",
    ),
    "real_money_status": PlainLanguageTerm(
        technical_key="real_money_status",
        plain_label="Real-Money Status",
        short_explanation="Whether this is allowed near real-money decisions.",
        why_it_matters="This must be explicit and conservative.",
        caution="The current answer is always Not allowed.",
    ),
    "fixture_universe": PlainLanguageTerm(
        technical_key="fixture_universe",
        plain_label="Built-In Sample Universe",
        short_explanation="The small local set of sample symbols included with the app.",
        why_it_matters="It makes the screener repeatable while real providers are absent.",
        caution="The built-in sample universe is not live or complete market coverage.",
    ),
    "pretend_portfolio_test": PlainLanguageTerm(
        technical_key="pretend_portfolio_test",
        plain_label="Pretend Portfolio Test",
        short_explanation=(
            "A practice portfolio that lets EdgeLab learn how it might group ideas later."
        ),
        why_it_matters="It keeps portfolio thinking separate from real-money decisions.",
        caution="Pretend portfolio tests are not recommendations.",
    ),
    "practice_portfolio": PlainLanguageTerm(
        technical_key="practice_portfolio",
        plain_label="Practice Portfolio",
        short_explanation="A sample-data portfolio used for learning, not action.",
        why_it_matters="It lets the app explain its thinking before any paper mode exists.",
        caution="Practice portfolios do not prove anything about real markets.",
    ),
    "model_portfolio": PlainLanguageTerm(
        technical_key="model_portfolio",
        plain_label="Pretend Portfolio Test",
        short_explanation=(
            "A beginner-friendly name for a hypothetical portfolio built from sample data."
        ),
        why_it_matters="It shows what EdgeLab is practicing without implying a recommendation.",
        caution="Internal APIs may still use model portfolio wording.",
    ),
    "target_weight": PlainLanguageTerm(
        technical_key="target_weight",
        plain_label="Pretend Portfolio Share",
        short_explanation="How much of the pretend portfolio goes into one idea.",
        why_it_matters="It explains size without turning the page into a trading dashboard.",
    ),
    "target_value": PlainLanguageTerm(
        technical_key="target_value",
        plain_label="Pretend Dollar Amount",
        short_explanation="The fake dollar amount implied by the pretend portfolio share.",
        why_it_matters="It keeps the number clearly separate from real money.",
        caution="This is not spendable or investable money.",
    ),
    "cash_allocation": PlainLanguageTerm(
        technical_key="cash_allocation",
        plain_label="Cash Left Safely Unused",
        short_explanation=(
            "The part EdgeLab leaves unused because the evidence is not strong enough yet."
        ),
        why_it_matters="Cash makes restraint visible instead of making it look like inaction.",
    ),
    "equity_exposure": PlainLanguageTerm(
        technical_key="equity_exposure",
        plain_label="Invested Instead of Sitting Safely in Cash",
        short_explanation="How much of the pretend portfolio is not sitting safely unused.",
        why_it_matters="It shows how cautious or aggressive the practice test is.",
    ),
    "portfolio_constraint": PlainLanguageTerm(
        technical_key="portfolio_constraint",
        plain_label="Safety Rule",
        short_explanation="A plain rule that stops one idea from becoming too large.",
        why_it_matters="Safety rules help EdgeLab stay cautious when evidence is thin.",
    ),
    "safety_rule": PlainLanguageTerm(
        technical_key="safety_rule",
        plain_label="Safety Rule",
        short_explanation="A simple limit that keeps a practice portfolio from getting reckless.",
        why_it_matters="It turns caution into something the user can see.",
    ),
    "portfolio_monitoring": PlainLanguageTerm(
        technical_key="portfolio_monitoring",
        plain_label="Next Review Notes",
        short_explanation="The next things EdgeLab should re-check before trust increases.",
        why_it_matters="A practice portfolio should say how it could get weaker.",
    ),
    "holding_reason": PlainLanguageTerm(
        technical_key="holding_reason",
        plain_label="Why It Appears",
        short_explanation="The plain-English reason a model holding is included.",
        why_it_matters="Every holding should explain its job in the model.",
    ),
    "what_to_monitor": PlainLanguageTerm(
        technical_key="what_to_monitor",
        plain_label="What EdgeLab Would Watch Next",
        short_explanation="The next condition EdgeLab would re-check in research mode.",
        why_it_matters="Research should define how evidence can weaken.",
    ),
    "what_would_make_us_reconsider": PlainLanguageTerm(
        technical_key="what_would_make_us_reconsider",
        plain_label="What Would Make Us Reconsider",
        short_explanation="Events or evidence gaps that would weaken the model.",
        why_it_matters="Good portfolio research names its failure conditions.",
    ),
    "defensive_research": PlainLanguageTerm(
        technical_key="defensive_research",
        plain_label="Defensive Research",
        short_explanation="A model style that keeps more cash and less concentrated exposure.",
        why_it_matters="It tests restraint and reference exposure before confidence exists.",
    ),
    "core_research": PlainLanguageTerm(
        technical_key="core_research",
        plain_label="Core Research",
        short_explanation="A balanced model style for default portfolio construction tests.",
        why_it_matters="It gives the app a simple baseline model to inspect.",
    ),
    "opportunistic_research": PlainLanguageTerm(
        technical_key="opportunistic_research",
        plain_label="Opportunistic Research",
        short_explanation="A higher-exposure research style that still obeys limits.",
        why_it_matters="It tests whether stronger candidate scores create concentration risk.",
    ),
    "benchmark_comparison": PlainLanguageTerm(
        technical_key="benchmark_comparison",
        plain_label="Comparison Basket",
        short_explanation="A simple basket used for context, not preference.",
        why_it_matters="It helps EdgeLab compare practice tests later without implying action.",
    ),
    "research_model": PlainLanguageTerm(
        technical_key="research_model",
        plain_label="Research-Only Practice Test",
        short_explanation="A pretend setup used for learning and validation.",
        why_it_matters="It keeps research separate from paper or real-money action.",
    ),
    "allocation": PlainLanguageTerm(
        technical_key="allocation",
        plain_label="How Much Goes Here",
        short_explanation="How much of the pretend portfolio goes into one idea or cash.",
        why_it_matters="It explains sizing without finance jargon.",
    ),
    "diversification": PlainLanguageTerm(
        technical_key="diversification",
        plain_label="Not Putting Too Much In One Idea",
        short_explanation="A way to avoid letting one idea dominate the practice portfolio.",
        why_it_matters="It keeps one weak idea from making the whole test look better or worse.",
    ),
    "evidence_details": PlainLanguageTerm(
        technical_key="evidence_details",
        plain_label="Evidence Details",
        short_explanation="A lower section for technical numbers after the plain-English story.",
        why_it_matters="The user should understand EdgeLab's thinking before seeing metrics.",
    ),
    "next_review_item": PlainLanguageTerm(
        technical_key="next_review_item",
        plain_label="Next Review Item",
        short_explanation="The next simple thing EdgeLab should check.",
        why_it_matters="It turns research into a clear next question, not an action instruction.",
    ),
    "intraday": PlainLanguageTerm(
        technical_key="intraday",
        plain_label="Same-Day Market Study",
        short_explanation="A local study of market behavior inside one session.",
        why_it_matters="It tests whether short-window behavior can be described with data.",
        caution="Short-window sample behavior is not proof of a real opportunity.",
    ),
    "first_hour": PlainLanguageTerm(
        technical_key="first_hour",
        plain_label="First-Hour Window",
        short_explanation="The first regular-session hour in the synthetic fixture.",
        why_it_matters="Many intraday ideas depend on early-session behavior.",
    ),
    "opening_benchmark": PlainLanguageTerm(
        technical_key="opening_benchmark",
        plain_label="Opening Reference Level",
        short_explanation="A measured level used to describe the synthetic open.",
        why_it_matters="Reference levels help turn visual chart ideas into data events.",
    ),
    "opening_range": PlainLanguageTerm(
        technical_key="opening_range",
        plain_label="Opening Range",
        short_explanation="The high and low from the first few synthetic first-hour bars.",
        why_it_matters="It gives the detector a simple boundary to test.",
    ),
    "failed_opening_push": PlainLanguageTerm(
        technical_key="failed_opening_push",
        plain_label="Failed Opening Push",
        short_explanation="An early move above a reference level that did not hold.",
        why_it_matters="Failures can be measured without relying on chart intuition.",
    ),
    "gap_fade": PlainLanguageTerm(
        technical_key="gap_fade",
        plain_label="Gap Fade Study",
        short_explanation="A synthetic gap that later moves back toward opening references.",
        why_it_matters="It tests whether gap behavior can be represented as events.",
    ),
    "no_trade_day": PlainLanguageTerm(
        technical_key="no_trade_day",
        plain_label="Sit-Out Day",
        short_explanation="A session where EdgeLab chooses no setup.",
        why_it_matters="Sitting out is a valid result when the measured evidence is unclear.",
    ),
    "hypothetical_intraday_result": PlainLanguageTerm(
        technical_key="hypothetical_intraday_result",
        plain_label="Hypothetical Intraday Result",
        short_explanation="A fixture-only calculation after a detected setup.",
        why_it_matters="It tests workflow math, not real tradability.",
        caution="This is not a recommendation or proof of an edge.",
    ),
    "prop_account": PlainLanguageTerm(
        technical_key="prop_account",
        plain_label="Simulated Funding Account",
        short_explanation="A generic account-rule model used for research arithmetic.",
        why_it_matters="It separates account economics from strategy evidence.",
        caution="The generic rules may not match any real program.",
    ),
    "qualification_target": PlainLanguageTerm(
        technical_key="qualification_target",
        plain_label="Qualification Target",
        short_explanation="A generic profit threshold in the sample account rules.",
        why_it_matters="It shows how account constraints can change interpretation.",
    ),
    "copied_accounts": PlainLanguageTerm(
        technical_key="copied_accounts",
        plain_label="Copied Accounts",
        short_explanation="Multiple accounts receiving the same hypothetical result.",
        why_it_matters="Copied accounts multiply the economics and the mistakes.",
    ),
    "trade_copier": PlainLanguageTerm(
        technical_key="trade_copier",
        plain_label="Copying Tool Concept",
        short_explanation="A future-only concept for mirroring decisions across accounts.",
        why_it_matters="It must be treated as risk multiplication, not edge creation.",
        caution="No copying tool integration exists in this spike.",
    ),
    "loss_limit": PlainLanguageTerm(
        technical_key="loss_limit",
        plain_label="Loss Limit",
        short_explanation="A generic account rule that stops weak sample behavior.",
        why_it_matters="Loss limits can overwhelm attractive-looking gross results.",
    ),
    "payout_split": PlainLanguageTerm(
        technical_key="payout_split",
        plain_label="Payout Split",
        short_explanation="A generic split applied to positive copied-account math.",
        why_it_matters="It is account arithmetic, not evidence of a setup edge.",
    ),
    "synthetic_intraday_data": PlainLanguageTerm(
        technical_key="synthetic_intraday_data",
        plain_label="Synthetic Intraday Sample Data",
        short_explanation="Artificial one-minute session data built into the app.",
        why_it_matters="It lets EdgeLab test structure without live providers.",
        caution="Synthetic intraday data is not real market evidence.",
    ),
    "spike_verdict": PlainLanguageTerm(
        technical_key="spike_verdict",
        plain_label="Research Spike Verdict",
        short_explanation="Whether the synthetic workflow is represented well enough to inspect.",
        why_it_matters="It guides deeper research without claiming profitability.",
    ),
    "paired_instrument_comparison": PlainLanguageTerm(
        technical_key="paired_instrument_comparison",
        plain_label="Paired Instrument Comparison",
        short_explanation="An optional comparison between two fixture-backed symbols.",
        why_it_matters="It can add context, but single-symbol analysis must still work.",
        caution="Paired comparison is skipped when the fixture data is unavailable.",
    ),
}


def get_plain_language_term(technical_key: str) -> PlainLanguageTerm:
    """Return a plain-language term by key."""

    try:
        return PLAIN_LANGUAGE_TERMS[technical_key]
    except KeyError as error:
        raise KeyError(f"Unknown plain-language term: {technical_key}") from error


def plain_label(technical_key: str) -> str:
    """Return the plain label for a technical key."""

    return get_plain_language_term(technical_key).plain_label


def explain(technical_key: str) -> str:
    """Return the short explanation for a technical key."""

    return get_plain_language_term(technical_key).short_explanation


def why_it_matters(technical_key: str) -> str:
    """Return why a technical key matters."""

    return get_plain_language_term(technical_key).why_it_matters


def yes_no(value: bool) -> str:
    """Render booleans as plain English."""

    return "Yes" if value else "No"
