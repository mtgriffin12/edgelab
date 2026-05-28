from fastapi.testclient import TestClient

from edgelab.app.main import app


def test_get_sample_backtest_returns_research_result() -> None:
    client = TestClient(app)

    response = client.get("/backtests/sample")

    assert response.status_code == 200
    assert response.json()["strategy_id"] == "relative-strength-pullback"
    assert response.json()["symbol"] == "SPY"
    assert response.json()["status"] == "completed"
    assert response.json()["conclusion"] == "research_only"


def test_post_run_backtest_returns_result() -> None:
    client = TestClient(app)

    response = client.post(
        "/backtests/run",
        json={
            "strategy_id": "relative-strength-pullback",
            "symbol": "QQQ",
            "initial_capital": 50000,
            "execution_assumptions": {
                "initial_capital": 50000,
                "commission_per_trade": 1,
                "slippage_bps": 5,
                "max_position_pct": 0.2,
                "allow_fractional_shares": True,
                "execution_timing": "next_open",
                "benchmark_symbol": "SPY",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["symbol"] == "QQQ"
    assert "trades" in response.json()
    assert "equity_curve" in response.json()


def test_post_run_backtest_rejects_missing_strategy() -> None:
    client = TestClient(app)

    response = client.post(
        "/backtests/run",
        json={"strategy_id": "missing", "symbol": "SPY"},
    )

    assert response.status_code == 404
