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


def test_journal_returns_phase_summary() -> None:
    response = client.get("/ui/journal")

    assert response.status_code == 200
    assert "Phase 5B plain-English UX language" in response.text
    assert "Phase 5C strategy discovery lab" in response.text


def test_reports_returns_summaries() -> None:
    response = client.get("/ui/reports")

    assert response.status_code == 200
    assert "Strategy Inventory Summary" in response.text
    assert "Built-In Market Sample Summary" in response.text
    assert "Sample Historical Test Summary" in response.text


def test_ui_pages_do_not_contain_real_money_action_buttons() -> None:
    response = client.get("/ui/risk-sentinel")

    assert response.status_code == 200
    assert "<button" not in response.text.lower()
    assert "Allowed to Use Real Money" in response.text
    assert "No real-money use is enabled" in response.text


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
        "/ui/journal",
        "/ui/reports",
    ]
    forbidden_phrases = [
        "buy now",
        "sell now",
        "short now",
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
