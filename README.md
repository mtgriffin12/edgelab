# EdgeLab

EdgeLab is a local-first trading research and validation app. It helps discover, define, backtest, rank, paper-trade, monitor, and report on trading strategies before any real-money execution is considered.

## What EdgeLab Is

- A research and validation system for US equities and ETFs.
- A decision lab for strategy evidence, risk controls, paper results, and audit trails.
- A local-first Python application designed to become cloud-ready later.

## What EdgeLab Is Not

- Not a live trading bot.
- Not a broker order execution system.
- Not a place to store brokerage credentials or secrets.
- Not a source of real market-data integrations in Phase 0.

## Project Phase

Current phase: **Phase 2 market data ingestion foundation**.

No live trading functionality exists.

## Local Setup

EdgeLab targets Python 3.12 or newer.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If `uv` is available:

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Run the API

```bash
uvicorn edgelab.app.main:app --reload
```

Then visit:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/strategies`
- `http://127.0.0.1:8000/strategies/relative-strength-pullback`
- `http://127.0.0.1:8000/strategies/relative-strength-pullback/card`
- `http://127.0.0.1:8000/market-data/symbols`
- `http://127.0.0.1:8000/market-data/SPY/bars`
- `http://127.0.0.1:8000/market-data/SPY/summary`
- `http://127.0.0.1:8000/market-data/SPY/quality`

The strategy endpoints are read-only and use an in-memory sample registry. The market-data
endpoints are read-only and use synthetic local CSV fixtures only.

## Run Tests

```bash
pytest
```

## Safety Warning

EdgeLab has no live trading functionality. It does not place orders, connect to brokers, request broker credentials, or make real market-data provider calls in this phase.
