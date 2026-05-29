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
