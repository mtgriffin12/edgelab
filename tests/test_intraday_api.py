from fastapi.testclient import TestClient

from edgelab.app.main import app

client = TestClient(app)


def test_intraday_instruments_endpoint_lists_dynamic_fixture_symbols() -> None:
    response = client.get("/intraday/instruments")

    assert response.status_code == 200
    symbols = {instrument["symbol"] for instrument in response.json()["instruments"]}
    assert {"ES_SYN", "NQ_SYN", "GEN_SYN"}.issubset(symbols)


def test_intraday_sessions_endpoint_lists_sessions() -> None:
    response = client.get("/intraday/sessions")

    assert response.status_code == 200
    sessions = response.json()["sessions"]
    assert any(session["session_id"] == "generic-symbol-intraday-synthetic" for session in sessions)


def test_intraday_symbol_endpoints_work_for_generic_symbol() -> None:
    paths = [
        "/intraday/GEN_SYN/benchmarks",
        "/intraday/GEN_SYN/events",
        "/intraday/GEN_SYN/setups",
        "/intraday/GEN_SYN/simulation",
    ]

    for path in paths:
        response = client.get(path)
        assert response.status_code == 200
        assert response.json()["symbol"] == "GEN_SYN"


def test_intraday_symbol_endpoints_do_not_require_pair_data() -> None:
    response = client.get("/intraday/GEN_SYN/simulation")

    assert response.status_code == 200
    assert response.json()["simulated_trade_count"] == 1
    assert response.json()["real_money_status"] == "Not allowed"


def test_intraday_card_endpoint_returns_text_plain() -> None:
    response = client.get("/intraday/GEN_SYN/simulation/card")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "## Spike Verdict" in response.text


def test_intraday_missing_fixture_returns_404() -> None:
    response = client.get("/intraday/MISSING/simulation")

    assert response.status_code == 404


def test_intraday_prop_account_endpoints() -> None:
    response = client.get("/intraday/prop-account/sample")
    card_response = client.get("/intraday/prop-account/sample/card")

    assert response.status_code == 200
    assert response.json()["real_money_status"] == "Not allowed"
    assert card_response.status_code == 200
    assert card_response.headers["content-type"].startswith("text/plain")
    assert "Scaling changes economics" in card_response.text
