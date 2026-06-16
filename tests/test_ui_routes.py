import re
from html.parser import HTMLParser

from fastapi.testclient import TestClient

from edgelab.app.main import app

client = TestClient(app)


def test_ui_home_returns_research_cockpit() -> None:
    response = client.get("/ui")

    assert response.status_code == 200
    assert "Research Cockpit" in response.text
    assert "No live trading enabled" in response.text
    assert "Synthetic Sample Data" in response.text


def test_primary_navigation_uses_grouped_parent_areas() -> None:
    response = client.get("/ui")

    assert response.status_code == 200
    parser = PrimaryNavParser()
    parser.feed(response.text)

    assert parser.direct_links == ["/ui", "/ui/reports"]
    assert parser.parent_labels == ["Research", "Intraday", "Evidence", "Portfolio"]
    for label in ["Cockpit", "Research", "Intraday", "Evidence", "Portfolio", "Reports"]:
        assert label in parser.visible_nav_text

    expected_links = {
        "/ui/discovery-lab": "Discovery Lab",
        "/ui/rankings": "Rankings",
        "/ui/candidates": "Candidates",
        "/ui/lab-bench": "Lab Bench",
        "/ui/evidence-board": "Evidence Board",
        "/ui/sentiment-lens": "Sentiment Lens",
        "/ui/risk-sentinel": "Risk Sentinel",
        "/ui/journal": "Journal",
        "/ui/portfolios": "Portfolio Tests",
    }
    for href, label in expected_links.items():
        assert href in parser.all_links
        assert label in parser.visible_nav_text
    assert 'document.querySelectorAll(".nav-menu[open]")' in response.text


def test_intraday_navigation_group_keeps_key_destinations_reachable() -> None:
    response = client.get("/ui/intraday-lab/research/failed-early-move")

    assert response.status_code == 200
    parser = PrimaryNavParser()
    parser.feed(response.text)

    expected_intraday_links = {
        "/ui/intraday-lab/research": "Research",
        "/ui/intraday-lab/trading": "Trading",
        "/ui/intraday-lab/research-runs": "Saved Results",
    }
    for href, label in expected_intraday_links.items():
        assert href in parser.all_links
        assert label in parser.visible_nav_text

    for label in [
        "FirstRate Study",
        "SPY vs QQQ Study",
        "Variant Study",
        "Out-of-Sample Check",
        "SPY",
        "QQQ",
    ]:
        assert label not in parser.visible_nav_text

    assert "/ui/intraday-lab/firstrate" not in parser.direct_links
    assert "/ui/intraday-lab/comparative-study" not in parser.direct_links
    assert "/ui/intraday-lab/variant-study" not in parser.direct_links
    assert "/ui/intraday-lab/out-of-sample" not in parser.direct_links
    assert "/ui/intraday-lab/research-runs" not in parser.direct_links


def test_lab_bench_returns_strategy_names() -> None:
    response = client.get("/ui/lab-bench")

    assert response.status_code == 200
    assert "Relative Strength Pullback" in response.text
    assert "Earnings Drift With Confirmation" in response.text
    assert "Allowed to Use Real Money" in response.text
    assert ">No<" in response.text


def test_strategy_detail_returns_strategy_card_content() -> None:
    response = client.get("/ui/strategies/relative-strength-pullback")

    assert response.status_code == 200
    assert "Why It Exists" in response.text
    assert "Evidence Required" in response.text
    assert "Risk Notes" in response.text


def test_evidence_board_returns_research_limitations() -> None:
    response = client.get("/ui/evidence-board")

    assert response.status_code == 200
    assert "Historical Test" in response.text
    assert "This is a historical test using sample data built into the app" in response.text
    assert "It is not proof the strategy" in response.text
    assert "it is not a recommendation" in response.text
    assert "research evidence only" in response.text
    assert "placeholder signal behavior only" in response.text
    assert "not allowed to use paper simulation" in response.text
    assert "Worst Drop" in response.text
    assert "Gain/Loss Ratio" in response.text


def test_sentiment_lens_returns_fixture_context() -> None:
    response = client.get("/ui/sentiment-lens")

    assert response.status_code == 200
    assert "Market Mood Lens" in response.text
    assert "Market mood is context, not a signal to act" in response.text
    assert "synthetic sample data built" in response.text
    assert "not reading live news yet" in response.text
    assert "Descriptive context only" in response.text
    assert "Mixed-Signal Warnings" in response.text


def test_risk_sentinel_returns_no_live_trading_language() -> None:
    response = client.get("/ui/risk-sentinel")

    assert response.status_code == 200
    assert "The system is blocked from real-money use" in response.text
    assert "No real-money use is enabled" in response.text
    assert "Safety rules are designed to stop weak ideas" in response.text
    assert "Doing nothing is an acceptable outcome" in response.text
    assert "Cash/no-action is a valid research conclusion" in response.text


def test_discovery_lab_returns_two_research_lanes() -> None:
    response = client.get("/ui/discovery-lab")

    assert response.status_code == 200
    assert "Strategy Discovery Lab" in response.text
    assert "Known Strategy Library" in response.text
    assert "Edge Innovation Lab" in response.text
    assert "durable edge" in response.text
    assert "no idea is ready for real money" in response.text
    assert "Relative Strength Pullback" in response.text
    assert "Social Euphoria Without Price Confirmation" in response.text


def test_discovery_detail_returns_plain_english_card() -> None:
    response = client.get("/ui/discovery-lab/broad-fear-company-calm-pullback")

    assert response.status_code == 200
    assert "Back to Discovery Lab" in response.text
    assert "Simpler Idea to Beat" in response.text
    assert "Environment Fit" in response.text
    assert "Curve-Fit Risk" in response.text
    assert "What Simpler Idea It Must Beat" in response.text
    assert "What Evidence Is Needed" in response.text


def test_rankings_returns_research_scorecards() -> None:
    response = client.get("/ui/rankings")

    assert response.status_code == 200
    assert "Strategy Rankings" in response.text
    assert "research evidence only" in response.text
    assert "Overall Research Score" in response.text
    assert "Real-Money Status" in response.text
    assert "Relative Strength Pullback" in response.text


def test_candidates_returns_research_candidates() -> None:
    response = client.get("/ui/candidates")

    assert response.status_code == 200
    assert "Candidate Equity Screener" in response.text
    assert "research triage only" in response.text
    assert "Real-Money Status" in response.text
    assert "SPY Research Candidate" in response.text


def test_portfolios_returns_model_portfolios() -> None:
    response = client.get("/ui/portfolios")

    assert response.status_code == 200
    assert "Pretend Portfolio Tests" in response.text
    assert "practice portfolios, not recommendations" in response.text
    assert "sample data built into the app" in response.text
    assert "What EdgeLab is testing" in response.text
    assert "What EdgeLab would do in research mode" in response.text
    assert "Why cash is included" in response.text
    assert "What supports this test" in response.text
    assert "What is missing" in response.text
    assert "Next review item" in response.text
    assert "Evidence details" in response.text
    assert "Not allowed" in response.text
    primary_text = visible_text_before(response.text, "Evidence details")
    for phrase in [
        "target weight",
        "equity exposure",
        "constraints",
        "benchmark",
        "allocation",
    ]:
        assert phrase not in primary_text


def test_portfolio_detail_returns_plain_english_card() -> None:
    response = client.get("/ui/portfolios/core-research-portfolio")

    assert response.status_code == 200
    assert "Back to Pretend Portfolio Tests" in response.text
    for phrase in [
        "Bottom line",
        "What EdgeLab is pretending to test",
        "What EdgeLab would do in research mode",
        "Why each holding appears",
        "Why cash is included",
        "What is missing",
        "Why this might be wrong",
        "What would make us reconsider",
        "Next review item",
        "Evidence details",
        "Real-money status",
    ]:
        assert phrase in response.text
    assert "Real-money status:</strong>\n    Not allowed" in response.text
    primary_text = visible_text_before(response.text, "Evidence details")
    for phrase in [
        "target weight",
        "equity exposure",
        "constraints",
        "benchmark",
        "allocation",
    ]:
        assert phrase not in primary_text


def test_intraday_lab_returns_simple_product_hub() -> None:
    response = client.get("/ui/intraday-lab")

    assert response.status_code == 200
    assert "Intraday Lab" in response.text
    assert "Intraday Research" in response.text
    assert "Intraday Trading" in response.text
    assert "/ui/intraday-lab/research" in response.text
    assert "/ui/intraday-lab/trading" in response.text
    for phrase in [
        "FirstRate SPY/QQQ Study",
        "SPY vs QQQ Pattern Study",
        "Controlled Variant Study",
        "Out-of-Sample Check",
        "GEN_SYN",
        "Repeated Pattern Results",
        "Sit-Out Review",
    ]:
        assert phrase not in response.text


def test_intraday_research_list_returns_strategy_idea_table() -> None:
    response = client.get("/ui/intraday-lab/research")

    assert response.status_code == 200
    for phrase in [
        "Intraday Research",
        "Bottom line",
        "What EdgeLab tested",
        "What EdgeLab found",
        "Best candidate if any",
        "Current conclusion",
        "Strategy idea",
        "Securities tested",
        "Tests run",
        "Best current pattern candidate",
        "Current conclusion",
        "Next research action",
        "Failed Early Move",
        "Gap Fade",
        "Gap Continuation",
        "First 15-Minute Breakout",
        "First 30-Minute Breakout",
        "Opening Range Reclaim",
        "Strong Open / Weak Follow-Through",
        "SPY/QQQ Divergence",
        "AAPL, AMZN, DIA, EEM, META, MSFT, QQQ, SPY, TSLA, VXX",
        "VXX_1min_firstratedata.csv",
        "Future AI idea intake",
        "does not call AI",
        "Evidence Details",
        "Real-money status: Not allowed",
    ]:
        assert phrase in response.text
    assert "No usable local date range" not in response.text
    assert "Local data problem blocked the test" not in response.text
    primary_text = visible_text_before(response.text, "Evidence Details")
    assert "buy now" not in primary_text
    assert "sell now" not in primary_text
    assert "short now" not in primary_text
    assert "too noisy" not in response.text.lower()
    assert "ready for real money" not in response.text.lower()
    assert "validated edge" not in response.text.lower()


def test_failed_early_move_research_detail_summarizes_all_related_tests() -> None:
    response = client.get("/ui/intraday-lab/research/failed-early-move")

    assert response.status_code == 200
    for phrase in [
        "Failed Early Move",
        "What this strategy tests",
        "What EdgeLab is testing",
        "EdgeLab checks mornings where price made an early push but could not hold it.",
        "What counts as an example",
        "A morning counts when price moves outside the early range, then falls back inside it.",
        "What would count as a useful result",
        "What would count as a failed or unclear result",
        "Result Summary",
        "Securities Tested",
        "SPY",
        "QQQ",
        "AAPL",
        "AMZN",
        "Tests Run",
        "Expanded local universe scan",
        "Checked later in the year",
        "Best Pattern Candidates",
        "No strong candidate yet",
        "Current Conclusion",
        "Next Research Action",
        "Evidence Details",
        "Discovery sprint API",
        "Discovery sprint card",
        "/intraday/discovery-sprint",
        "/intraday/discovery-sprint/card",
        "Examples are mornings where this setup appeared.",
        "Completed examples are examples where EdgeLab could see what happened afterward.",
    ]:
        assert phrase in response.text
    primary_text = visible_text_before(response.text, "Evidence Details")
    for phrase in [
        "FirstRate",
        "variant",
        "holdout",
        "out-of-sample",
        "Real-money status",
    ]:
        assert phrase.lower() not in primary_text
    symbol_route = client.get("/ui/intraday-lab/research/AAPL")
    assert symbol_route.status_code == 404


def test_strategy_detail_pages_explain_examples_and_current_results() -> None:
    first_15 = client.get("/ui/intraday-lab/research/first-15-minute-breakout")
    reclaim = client.get("/ui/intraday-lab/research/opening-range-reclaim")

    assert first_15.status_code == 200
    assert reclaim.status_code == 200
    for response in [first_15, reclaim]:
        assert "<summary>What this strategy tests</summary>" in response.text
        assert "What EdgeLab is testing" in response.text
        assert "What counts as an example" in response.text
        assert "What would count as a useful result" in response.text
        assert "What would count as a failed or unclear result" in response.text
        assert "How to read the current result" in response.text
        assert "Examples are mornings where this setup appeared." in response.text
        assert (
            "Completed examples are examples where EdgeLab could see what happened afterward."
            in response.text
        )
        assert (
            "The test had both helpful and unhelpful follow-through, so EdgeLab could not "
            "identify a clear pattern."
        ) in response.text

    assert (
        "A morning counts when price breaks above or below the first 15-minute range."
        in first_15.text
    )
    assert (
        "A morning counts when price moves outside the early range, then returns through that "
        "range."
    ) in reclaim.text


def test_all_fixed_intraday_strategy_detail_pages_return_research_summary() -> None:
    strategy_slugs = [
        "failed-early-move",
        "gap-fade",
        "gap-continuation",
        "first-15-minute-breakout",
        "first-30-minute-breakout",
        "opening-range-reclaim",
        "strong-open-weak-follow-through",
        "spy-qqq-divergence",
    ]

    for slug in strategy_slugs:
        response = client.get(f"/ui/intraday-lab/research/{slug}")

        assert response.status_code == 200
        assert "What this strategy tests" in response.text
        assert "Result Summary" in response.text
        assert "Securities Tested" in response.text
        assert "Current Conclusion" in response.text
        assert "Next Research Action" in response.text
        assert "Evidence Details" in response.text
        assert "Real-money status: Not allowed" in response.text
        assert "too noisy" not in response.text.lower()
        assert "ready for real money" not in response.text.lower()
        assert "validated edge" not in response.text.lower()


def test_intraday_trading_placeholder_is_future_only() -> None:
    response = client.get("/ui/intraday-lab/trading")

    assert response.status_code == 200
    assert "No strategy has passed the research gates yet" in response.text
    assert "Live monitoring, broker connections, and trading are not available" in response.text
    assert "<button" not in response.text.lower()
    assert "ready for real money" not in response.text.lower()


def test_comparative_study_ui_routes_return_plain_english_sections() -> None:
    routes = [
        "/ui/intraday-lab/comparative-study",
        "/ui/intraday-lab/comparative-study/spy-qqq",
        "/ui/intraday-lab/comparative-study/spy-qqq/opening-range-failure",
    ]

    for route in routes:
        response = client.get(route)
        assert response.status_code == 200
        assert "SPY vs QQQ" in response.text or "Failed Early Move" in response.text
        for phrase in [
            "Bottom line",
            "What EdgeLab compared",
            "What looked different",
            "Why that might matter",
            "Why this might be misleading",
            "What EdgeLab should test next",
            "Real-money status: Not allowed",
            "Evidence details",
        ]:
            assert phrase in response.text
        assert "failed early move" in response.text.lower()
        primary_text = visible_text_before(response.text, "Evidence details")
        assert "Opening Range Failure" not in primary_text
        assert "Freshness:" not in primary_text
        assert "Helpful afterward" not in primary_text
        assert "Wrong-way afterward" not in primary_text
        assert "Flat afterward" not in primary_text
        assert "spy_more_interesting" not in primary_text
        assert "interesting_but_unproven" not in primary_text
        assert "weak_or_inconsistent" not in primary_text
        assert "trade button" not in response.text.lower()
        assert "buy now" not in response.text.lower()
        assert "sell now" not in response.text.lower()
        assert "short now" not in response.text.lower()
        assert "ready for real money" not in response.text.lower()
        assert "validated edge" not in response.text.lower()
        if route != "/ui/intraday-lab/comparative-study":
            assert "What this is leading toward" in response.text
            assert "Moved as expected" in response.text
            assert "Moved against the test" in response.text
            assert "Did not move enough to matter" in response.text


def test_variant_study_ui_routes_return_plain_english_sections() -> None:
    routes = [
        "/ui/intraday-lab/variant-study",
        "/ui/intraday-lab/variant-study/spy",
        "/ui/intraday-lab/variant-study/spy/early-move-failed",
    ]

    for route in routes:
        response = client.get(route)
        assert response.status_code == 200
        assert "Variant" in response.text or "Failed Early Move" in response.text
        for phrase in [
            "Bottom line",
            "What EdgeLab tested",
            "What looked different",
            "Which version, if any, deserves more testing",
            "Why this might be misleading",
            "What EdgeLab should test next",
            "Real-money status: Not allowed",
            "Evidence details",
        ]:
            assert phrase in response.text
        primary_text = visible_text_before(response.text, "Evidence details")
        assert "Opening Range Failure" not in primary_text
        assert "worth_more_testing" not in primary_text
        assert "interesting_but_unproven" not in primary_text
        assert "trade button" not in response.text.lower()
        assert "buy now" not in response.text.lower()
        assert "sell now" not in response.text.lower()
        assert "short now" not in response.text.lower()
        assert "ready for real money" not in response.text.lower()
        assert "validated edge" not in response.text.lower()


def test_out_of_sample_ui_routes_return_plain_english_sections() -> None:
    routes = [
        "/ui/intraday-lab/out-of-sample",
        "/ui/intraday-lab/out-of-sample/spy",
        "/ui/intraday-lab/out-of-sample/spy/early-move-failed",
    ]

    for route in routes:
        response = client.get(route)
        assert response.status_code == 200
        assert "Out-of-Sample Check" in response.text or "first honesty check" in response.text
        for phrase in [
            "Bottom line",
            "What EdgeLab checked",
            "What changed on later data",
            "What this means",
            "What EdgeLab should test next",
            "Why this might be misleading",
            "Real-money status: Not allowed",
            "Evidence details",
        ]:
            assert phrase in response.text
        assert "holdout-style check" in response.text.lower()
        assert "not proof" in response.text.lower()
        primary_text = visible_text_before(response.text, "Evidence details")
        assert "Opening Range Failure" not in primary_text
        assert "too noisy" not in primary_text
        assert "trade button" not in response.text.lower()
        assert "buy now" not in response.text.lower()
        assert "sell now" not in response.text.lower()
        assert "short now" not in response.text.lower()
        assert "ready for real money" not in response.text.lower()
        assert "validated edge" not in response.text.lower()
        assert "paper-mode readiness" not in response.text.lower()


def test_intraday_legacy_evidence_routes_remain_available() -> None:
    routes = [
        "/ui/intraday-lab/firstrate",
        "/ui/intraday-lab/comparative-study",
        "/ui/intraday-lab/comparative-study/spy-qqq/opening-range-failure",
        "/ui/intraday-lab/variant-study",
        "/ui/intraday-lab/variant-study/spy/early-move-failed",
        "/ui/intraday-lab/out-of-sample",
        "/ui/intraday-lab/out-of-sample/spy/early-move-failed",
        "/ui/intraday-lab/research-runs",
    ]

    for route in routes:
        response = client.get(route)
        assert response.status_code == 200
        assert "Detailed evidence page for Failed Early Move research" in response.text


def test_intraday_symbol_page_returns_generic_fixture_view() -> None:
    response = client.get("/ui/intraday-lab/GEN_SYN")

    assert response.status_code == 200
    assert "GEN_SYN Intraday Study" in response.text
    assert "Opening benchmarks" in response.text
    assert "Detected events" in response.text
    assert "Hypothetical result" in response.text
    assert "Not allowed" in response.text


def test_intraday_prop_account_route_is_not_captured_as_symbol() -> None:
    response = client.get("/ui/intraday-lab/prop-account-scaling")

    assert response.status_code == 200
    assert "Prop-Account Scaling Study" in response.text
    assert "Copied-account scenarios" in response.text
    assert "GEN_SYN Intraday Study" not in response.text


def test_intraday_replay_landing_returns_historical_sessions() -> None:
    response = client.get("/ui/intraday-lab/replay")

    assert response.status_code == 200
    assert "Past Morning Practice Test" in response.text
    page_text = re.sub(r"\s+", " ", response.text)
    assert (
        "EdgeLab replays past market mornings one minute at a time to see whether it would "
        "have noticed a useful setup without peeking at what happened later."
    ) in page_text
    assert "not live" in response.text
    assert "not a signal system" in response.text
    assert "not a recommendation" in response.text
    assert "real-money status is Not allowed" in response.text
    assert "RPLAY" in response.text


def test_intraday_replay_detail_returns_plain_english_story() -> None:
    response = client.get("/ui/intraday-lab/replay/RPLAY/replay-breakout-complete")

    assert response.status_code == 200
    for phrase in [
        "Bottom line",
        "What EdgeLab would have done in practice mode",
        "Pretend start and finish",
        "Pretend start",
        "Pretend finish",
        "Pretend result",
        "What happened afterward",
        "Why this might be misleading",
        "What EdgeLab should test next",
        "Real-money status",
        "Not allowed",
        "Evidence details",
    ]:
        assert phrase in response.text
    primary_text = visible_text_before(response.text, "Evidence details")
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


def test_intraday_multi_session_summary_returns_plain_english_story() -> None:
    response = client.get("/ui/intraday-lab/multi-session-summary")

    assert response.status_code == 200
    for phrase in [
        "Many-Morning Practice Test",
        "Bottom line",
        "What EdgeLab tested",
        "What usually happened",
        "Whether EdgeLab found anything worth more testing",
        "When EdgeLab sat out",
        "Whether sitting out seemed helpful",
        "Why this might be misleading",
        "What EdgeLab should test next",
        "Real-money status",
        "Not allowed",
        "Evidence details",
    ]:
        assert phrase in response.text
    assert "Not enough examples yet" in response.text
    primary_text = visible_text_before(response.text, "Evidence details")
    for phrase in [
        "win rate",
        "expectancy",
        "sharpe",
        "drawdown",
        "profit factor",
        "slippage",
        "distribution",
        "statistical significance",
        "sample size",
        "volatility",
    ]:
        assert phrase not in primary_text


def test_intraday_pattern_results_returns_plain_english_story() -> None:
    response = client.get("/ui/intraday-lab/pattern-results")

    assert response.status_code == 200
    for phrase in [
        "Repeated Pattern Results",
        "Bottom line",
        "What EdgeLab tested",
        "What usually happened",
        "Why this might be misleading",
        "What EdgeLab should test next",
        "Real-money status",
        "Not allowed",
        "Evidence details",
    ]:
        assert phrase in response.text
    primary_text = visible_text_before(response.text, "Evidence details")
    for phrase in [
        "win rate",
        "expectancy",
        "sharpe",
        "drawdown",
        "profit factor",
        "slippage",
        "distribution",
        "statistical significance",
        "sample size",
        "volatility",
    ]:
        assert phrase not in primary_text


def test_intraday_no_trade_analysis_returns_plain_english_story() -> None:
    response = client.get("/ui/intraday-lab/no-trade-analysis")

    assert response.status_code == 200
    for phrase in [
        "Sit-Out Review",
        "Bottom line",
        "What EdgeLab tested",
        "What usually happened",
        "Why this might be misleading",
        "What EdgeLab should test next",
        "Real-money status",
        "Not allowed",
        "Evidence details",
    ]:
        assert phrase in response.text
    primary_text = visible_text_before(response.text, "Evidence details")
    for phrase in [
        "win rate",
        "expectancy",
        "sharpe",
        "drawdown",
        "profit factor",
        "slippage",
        "distribution",
        "statistical significance",
        "sample size",
        "volatility",
    ]:
        assert phrase not in primary_text


def test_intraday_many_morning_routes_are_not_captured_as_symbol() -> None:
    for path, marker in [
        ("/ui/intraday-lab/multi-session-summary", "Many-Morning Practice Test"),
        ("/ui/intraday-lab/pattern-results", "Repeated Pattern Results"),
        ("/ui/intraday-lab/no-trade-analysis", "Sit-Out Review"),
    ]:
        response = client.get(path)

        assert response.status_code == 200
        assert marker in response.text
        assert "MULTI-SESSION-SUMMARY Intraday Study" not in response.text
        assert "PATTERN-RESULTS Intraday Study" not in response.text
        assert "NO-TRADE-ANALYSIS Intraday Study" not in response.text


def test_intraday_replay_route_is_not_captured_as_symbol() -> None:
    response = client.get("/ui/intraday-lab/replay")

    assert response.status_code == 200
    assert "Past Morning Practice Test" in response.text
    assert "REPLAY Intraday Study" not in response.text


def test_candidate_detail_returns_plain_english_card() -> None:
    response = client.get("/ui/candidates/spy-research-candidate")

    assert response.status_code == 200
    assert "Back to Candidate Screener" in response.text
    assert "What supports it" in response.text
    assert "What is missing" in response.text
    assert "What would change our mind" in response.text
    assert "Not allowed" in response.text


def test_ranking_detail_returns_plain_english_scorecard() -> None:
    response = client.get("/ui/rankings/strategy-relative-strength-pullback")

    assert response.status_code == 200
    assert "Back to Rankings" in response.text
    assert "Why it ranked this way" in response.text
    assert "What helped" in response.text
    assert "What hurt" in response.text
    assert "Evidence still missing" in response.text
    assert "Not allowed" in response.text


def test_journal_returns_phase_summary() -> None:
    response = client.get("/ui/journal")

    assert response.status_code == 200
    assert "Phase 5B plain-English UX language" in response.text
    assert "Phase 5C strategy discovery lab" in response.text
    assert "Phase 6 strategy ranking engine" in response.text


def test_reports_returns_summaries() -> None:
    response = client.get("/ui/reports")

    assert response.status_code == 200
    assert "Strategy Inventory Summary" in response.text
    assert "Built-In Market Sample Summary" in response.text
    assert "Sample Historical Test Summary" in response.text


def test_ui_pages_do_not_contain_real_money_action_buttons() -> None:
    for path in [
        "/ui/risk-sentinel",
        "/ui/intraday-lab",
        "/ui/intraday-lab/research",
        "/ui/intraday-lab/research/failed-early-move",
        "/ui/intraday-lab/trading",
        "/ui/intraday-lab/GEN_SYN",
        "/ui/intraday-lab/prop-account-scaling",
        "/ui/intraday-lab/replay",
        "/ui/intraday-lab/replay/RPLAY/replay-breakout-complete",
        "/ui/intraday-lab/multi-session-summary",
        "/ui/intraday-lab/pattern-results",
        "/ui/intraday-lab/no-trade-analysis",
        "/ui/intraday-lab/out-of-sample",
        "/ui/intraday-lab/out-of-sample/spy",
        "/ui/intraday-lab/out-of-sample/spy/early-move-failed",
    ]:
        response = client.get(path)

        assert response.status_code == 200
        assert "<button" not in response.text.lower()
    risk_response = client.get("/ui/risk-sentinel")
    assert "Allowed to Use Real Money" in risk_response.text
    assert "No real-money use is enabled" in risk_response.text


def test_ui_pages_do_not_contain_action_instruction_phrases() -> None:
    paths = [
        "/ui",
        "/ui/lab-bench",
        "/ui/strategies/relative-strength-pullback",
        "/ui/evidence-board",
        "/ui/sentiment-lens",
        "/ui/risk-sentinel",
        "/ui/discovery-lab",
        "/ui/discovery-lab/broad-fear-company-calm-pullback",
        "/ui/rankings",
        "/ui/rankings/strategy-relative-strength-pullback",
        "/ui/candidates",
        "/ui/candidates/spy-research-candidate",
        "/ui/portfolios",
        "/ui/portfolios/core-research-portfolio",
        "/ui/intraday-lab",
        "/ui/intraday-lab/research",
        "/ui/intraday-lab/research/failed-early-move",
        "/ui/intraday-lab/trading",
        "/ui/intraday-lab/GEN_SYN",
        "/ui/intraday-lab/prop-account-scaling",
        "/ui/intraday-lab/replay",
        "/ui/intraday-lab/replay/RPLAY/replay-breakout-complete",
        "/ui/intraday-lab/multi-session-summary",
        "/ui/intraday-lab/pattern-results",
        "/ui/intraday-lab/no-trade-analysis",
        "/ui/intraday-lab/variant-study",
        "/ui/intraday-lab/variant-study/spy",
        "/ui/intraday-lab/variant-study/spy/early-move-failed",
        "/ui/intraday-lab/out-of-sample",
        "/ui/intraday-lab/out-of-sample/spy",
        "/ui/intraday-lab/out-of-sample/spy/early-move-failed",
        "/ui/journal",
        "/ui/reports",
    ]
    forbidden_phrases = [
        "buy now",
        "sell now",
        "short now",
        "go short",
        "enter short",
        "place an order",
        "submit an order",
        "execute a trade",
        "open a trade",
        "enter a trade",
        "trade now",
    ]

    for path in paths:
        response = client.get(path)
        page = response.text.lower()
        assert response.status_code == 200
        for phrase in forbidden_phrases:
            assert phrase not in page


def visible_text_before(html: str, marker: str) -> str:
    """Return visible-ish text before a marker, ignoring attributes such as href IDs."""

    return re.sub(r"<[^>]+>", " ", html.split(marker)[0]).lower()


class PrimaryNavParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_nav = False
        self.nav_depth = 0
        self.direct_links: list[str] = []
        self.all_links: set[str] = set()
        self.parent_labels: list[str] = []
        self._capture_summary = False
        self._nav_text: list[str] = []

    @property
    def visible_nav_text(self) -> str:
        return " ".join(self._nav_text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "nav" and "primary-nav" in attr_map.get("class", ""):
            self.in_nav = True
            self.nav_depth = 0
            return

        if not self.in_nav:
            return

        if tag == "a":
            href = attr_map.get("href")
            if href:
                self.all_links.add(href)
                if self.nav_depth == 0:
                    self.direct_links.append(href)
        if tag == "summary" and self.nav_depth == 1:
            self._capture_summary = True
        self.nav_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if not self.in_nav:
            return

        if tag == "nav" and self.nav_depth == 0:
            self.in_nav = False
            return

        if tag == "summary":
            self._capture_summary = False
        self.nav_depth = max(0, self.nav_depth - 1)

    def handle_data(self, data: str) -> None:
        if not self.in_nav:
            return

        text = data.strip()
        if not text:
            return

        self._nav_text.append(text)
        if self._capture_summary:
            self.parent_labels.append(text)
