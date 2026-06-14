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
        "comparative_study",
        "early_move_failed",
        "failed_early_push",
        "opening_range_failure",
        "symbol_difference",
        "too_noisy_to_compare",
        "not_enough_evidence",
        "moved_as_expected",
        "moved_against_the_test",
        "did_not_move_enough",
        "current_saved_result",
        "stale_saved_result",
        "future_signal_shape",
        "practice_setup_found",
        "what_looked_different",
        "what_to_compare_next",
        "spy_vs_qqq_pattern_study",
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
        "pretend_portfolio_test",
        "practice_portfolio",
        "model_portfolio",
        "target_weight",
        "target_value",
        "cash_allocation",
        "equity_exposure",
        "portfolio_constraint",
        "safety_rule",
        "portfolio_monitoring",
        "holding_reason",
        "what_to_monitor",
        "what_would_make_us_reconsider",
        "evidence_details",
        "next_review_item",
        "defensive_research",
        "core_research",
        "opportunistic_research",
        "benchmark_comparison",
        "research_model",
        "allocation",
        "diversification",
        "intraday",
        "first_hour",
        "opening_benchmark",
        "opening_range",
        "failed_opening_push",
        "gap_fade",
        "no_trade_day",
        "hypothetical_intraday_result",
        "prop_account",
        "qualification_target",
        "copied_accounts",
        "trade_copier",
        "loss_limit",
        "payout_split",
        "synthetic_intraday_data",
        "historical_intraday_data",
        "local_csv_import",
        "session_readiness",
        "data_quality_issue",
        "source_timezone",
        "adjustment_mode",
        "ready_for_replay",
        "incomplete_session",
        "unusable_session",
        "historical_replay",
        "past_morning_practice_test",
        "practice_setup",
        "pretend_start",
        "pretend_finish",
        "pretend_result",
        "keep_watching",
        "not_enough_data",
        "what_happened_afterward",
        "why_this_might_be_misleading",
        "what_to_test_next",
        "replay_clock",
        "bars_visible",
        "what_edgelab_knew",
        "setup_marked_for_research",
        "sit_out",
        "no_future_peeking",
        "replay_result",
        "many_morning_test",
        "pattern_results",
        "sit_out_analysis",
        "useful_pattern",
        "not_enough_examples",
        "interesting_but_unproven",
        "weak_or_inconsistent",
        "worth_more_testing",
        "what_usually_happened",
        "what_edgelab_avoided",
        "what_edgelab_missed",
        "spike_verdict",
        "paired_instrument_comparison",
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
    assert plain_label("pretend_portfolio_test") == "Pretend Portfolio Test"
    assert plain_label("model_portfolio") == "Pretend Portfolio Test"
    assert plain_label("cash_allocation") == "Cash Left Safely Unused"
    assert plain_label("portfolio_constraint") == "Safety Rule"
    assert plain_label("evidence_details") == "Evidence Details"
    assert plain_label("intraday") == "Same-Day Market Study"
    assert plain_label("synthetic_intraday_data") == "Synthetic Intraday Sample Data"
    assert plain_label("historical_intraday_data") == "Historical Same-Day Sample Data"
    assert plain_label("local_csv_import") == "Local CSV Import"
    assert plain_label("session_readiness") == "Ready for Future Replay"
    assert plain_label("historical_replay") == "Past Morning Practice Test"
    assert plain_label("past_morning_practice_test") == "Past Morning Practice Test"
    assert plain_label("pretend_start") == "Pretend Start"
    assert plain_label("pretend_finish") == "Pretend Finish"
    assert plain_label("pretend_result") == "Pretend Result"
    assert plain_label("no_future_peeking") == "No Future Peeking"
    assert plain_label("many_morning_test") == "Many-Morning Practice Test"
    assert plain_label("pattern_results") == "Repeated Pattern Results"
    assert plain_label("sit_out_analysis") == "Sit-Out Review"
    assert plain_label("not_enough_examples") == "Not Enough Examples"
    assert plain_label("worth_more_testing") == "Worth More Testing"
    assert plain_label("spike_verdict") == "Research Spike Verdict"
    assert plain_label("comparative_study") == "Comparison Study"
    assert plain_label("opening_range_failure") == "Early Move Failed"
    assert plain_label("early_move_failed") == "Early Move Failed"
    assert plain_label("failed_early_push") == "Failed Early Push"
    assert plain_label("moved_as_expected") == "Moved as Expected"
    assert plain_label("moved_against_the_test") == "Moved Against the Test"
    assert plain_label("did_not_move_enough") == "Did Not Move Enough"
    assert plain_label("future_signal_shape") == "Future Watch Message"
    assert plain_label("sit_out") == "Sit Out"
    assert plain_label("keep_watching") == "Keep Watching"
    assert plain_label("spy_vs_qqq_pattern_study") == "SPY vs QQQ Pattern Study"


def test_missing_plain_language_term_raises_key_error() -> None:
    try:
        get_plain_language_term("not_a_real_term")
    except KeyError as error:
        assert "Unknown plain-language term" in str(error)
    else:
        raise AssertionError("Expected missing plain-language term to raise KeyError")
