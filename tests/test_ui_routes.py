from fastapi.testclient import TestClient

from edgelab.app.main import app

client = TestClient(app)


def test_ui_home_returns_research_cockpit() -> None:
    response = client.get("/ui")

    assert response.status_code == 200
    assert "Research Cockpit" in response.text
    assert "No live trading enabled" in response.text
    assert "synthetic fixture data" in response.text


def test_lab_bench_returns_strategy_names() -> None:
    response = client.get("/ui/lab-bench")

    assert response.status_code == 200
    assert "Relative Strength Pullback" in response.text
    assert "Earnings Drift With Confirmation" in response.text


def test_strategy_detail_returns_strategy_card_content() -> None:
    response = client.get("/ui/strategies/relative-strength-pullback")

    assert response.status_code == 200
    assert "Why It Exists" in response.text
    assert "Evidence Required" in response.text
    assert "Risk Notes" in response.text


def test_evidence_board_returns_research_limitations() -> None:
    response = client.get("/ui/evidence-board")

    assert response.status_code == 200
    assert "research evidence only" in response.text
    assert "placeholder signal behavior only" in response.text
    assert "not paper-trading eligible" in response.text


def test_sentiment_lens_returns_fixture_context() -> None:
    response = client.get("/ui/sentiment-lens")

    assert response.status_code == 200
    assert "synthetic fixtures" in response.text
    assert "Descriptive context only" in response.text
    assert "trade_bias_context" in response.text or "Context" in response.text


def test_risk_sentinel_returns_no_live_trading_language() -> None:
    response = client.get("/ui/risk-sentinel")

    assert response.status_code == 200
    assert "No live trading is enabled" in response.text
    assert "Cash/no-action is a valid research conclusion" in response.text


def test_journal_returns_phase_summary() -> None:
    response = client.get("/ui/journal")

    assert response.status_code == 200
    assert "Phase 5A local UX shell" in response.text


def test_reports_returns_summaries() -> None:
    response = client.get("/ui/reports")

    assert response.status_code == 200
    assert "Strategy Inventory Summary" in response.text
    assert "Market Data Fixture Summary" in response.text
    assert "Sample Backtest Summary" in response.text


def test_ui_pages_do_not_contain_action_instruction_phrases() -> None:
    paths = [
        "/ui",
        "/ui/lab-bench",
        "/ui/strategies/relative-strength-pullback",
        "/ui/evidence-board",
        "/ui/sentiment-lens",
        "/ui/risk-sentinel",
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
