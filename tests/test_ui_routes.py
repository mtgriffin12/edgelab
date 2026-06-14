import re

from fastapi.testclient import TestClient

from edgelab.app.main import app

client = TestClient(app)


def test_ui_home_returns_research_cockpit() -> None:
    response = client.get("/ui")

    assert response.status_code == 200
    assert "Research Cockpit" in response.text
    assert "No live trading enabled" in response.text
    assert "Synthetic Sample Data" in response.text


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


def test_intraday_lab_returns_research_spike_page() -> None:
    response = client.get("/ui/intraday-lab")

    assert response.status_code == 200
    assert "Intraday Lab" in response.text
    assert "synthetic intraday sample data" in response.text.lower()
    assert "not live" in response.text
    assert "not a signal system" in response.text
    assert "not a recommendation" in response.text
    assert "GEN_SYN" in response.text
    assert "Many-Morning Practice Test" in response.text
    assert "Repeated Pattern Results" in response.text
    assert "Sit-Out Review" in response.text
    assert "Saved Research Runs" in response.text


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
        "/ui/intraday-lab/GEN_SYN",
        "/ui/intraday-lab/prop-account-scaling",
        "/ui/intraday-lab/replay",
        "/ui/intraday-lab/replay/RPLAY/replay-breakout-complete",
        "/ui/intraday-lab/multi-session-summary",
        "/ui/intraday-lab/pattern-results",
        "/ui/intraday-lab/no-trade-analysis",
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
        "/ui/intraday-lab/GEN_SYN",
        "/ui/intraday-lab/prop-account-scaling",
        "/ui/intraday-lab/replay",
        "/ui/intraday-lab/replay/RPLAY/replay-breakout-complete",
        "/ui/intraday-lab/multi-session-summary",
        "/ui/intraday-lab/pattern-results",
        "/ui/intraday-lab/no-trade-analysis",
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
