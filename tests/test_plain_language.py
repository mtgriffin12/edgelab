from edgelab.app.plain_language import PLAIN_LANGUAGE_TERMS, get_plain_language_term, plain_label


def test_required_plain_language_terms_exist() -> None:
    required_terms = {
        "backtest",
        "max_drawdown_pct",
        "total_return_pct",
        "profit_factor",
        "win_rate_pct",
        "exposure_pct",
        "equity_curve",
        "slippage",
        "commission",
        "sentiment",
        "weighted_sentiment_score",
        "decayed_sentiment_score",
        "dominant_event_type",
        "divergence_flags",
        "quality_issues",
        "eligible_for_backtesting",
        "eligible_for_paper_trading",
        "eligible_for_live_trading",
        "research_only",
        "unsupported_strategy",
        "insufficient_evidence",
        "fixture_data",
        "synthetic_data",
        "strategy_discovery_lab",
        "known_strategy_library",
        "edge_innovation_lab",
        "baseline_to_beat",
        "current_regime_fit",
        "overfitting_risk_score",
        "novelty_score",
        "complexity_score",
        "ranking",
        "evidence_strength",
        "overall_score",
        "baseline_comparison",
        "top_research_candidate",
        "weak_candidate",
        "promising_research_candidate",
        "overfitting_risk",
        "cost_sensitivity",
        "sample_size",
        "return_quality",
        "worst_drop_control",
        "consistency",
        "candidate",
        "research_candidate",
        "watchlist_only",
        "interesting_but_incomplete",
        "blocked_by_risk",
        "blocked_by_data_quality",
        "research_watchlist",
        "market_context",
        "market_mood_context",
        "what_supports_it",
        "what_is_missing",
        "what_would_change_our_mind",
        "real_money_status",
        "fixture_universe",
    }

    assert required_terms.issubset(PLAIN_LANGUAGE_TERMS)


def test_plain_language_terms_include_explanations() -> None:
    for key, term in PLAIN_LANGUAGE_TERMS.items():
        assert term.technical_key == key
        assert term.plain_label
        assert term.short_explanation
        assert term.why_it_matters


def test_key_technical_terms_map_to_plain_labels() -> None:
    assert plain_label("backtest") == "Historical Test"
    assert plain_label("max_drawdown_pct") == "Worst Drop"
    assert plain_label("profit_factor") == "Gain/Loss Ratio"
    assert plain_label("sentiment") == "Market Mood"
    assert plain_label("quality_issues") == "Reasons to Be Careful"
    assert plain_label("eligible_for_live_trading") == "Allowed to Use Real Money"
    assert plain_label("strategy_discovery_lab") == "Strategy Discovery Lab"
    assert plain_label("baseline_to_beat") == "Simpler Idea to Beat"
    assert plain_label("ranking") == "Research Ranking"
    assert plain_label("overall_score") == "Overall Research Score"
    assert plain_label("candidate") == "Research Candidate"
    assert plain_label("research_watchlist") == "Research Watchlist"


def test_missing_plain_language_term_raises_key_error() -> None:
    try:
        get_plain_language_term("not_a_real_term")
    except KeyError as error:
        assert "Unknown plain-language term" in str(error)
    else:
        raise AssertionError("Expected missing plain-language term to raise KeyError")
