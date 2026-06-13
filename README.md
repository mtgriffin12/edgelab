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

Current phase: **Phase 7B model portfolio engine**.

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

## Run the Local UI and API

```bash
PYTHONPATH=src .venv/bin/uvicorn edgelab.app.main:app --reload
```

Then visit:

- `http://127.0.0.1:8000/ui`
- `http://127.0.0.1:8000/ui/discovery-lab`
- `http://127.0.0.1:8000/ui/rankings`
- `http://127.0.0.1:8000/ui/candidates`
- `http://127.0.0.1:8000/ui/portfolios`
- `http://127.0.0.1:8000/ui/lab-bench`
- `http://127.0.0.1:8000/ui/evidence-board`
- `http://127.0.0.1:8000/ui/sentiment-lens`
- `http://127.0.0.1:8000/ui/risk-sentinel`
- `http://127.0.0.1:8000/ui/journal`
- `http://127.0.0.1:8000/ui/reports`
- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/strategies`
- `http://127.0.0.1:8000/strategies/relative-strength-pullback`
- `http://127.0.0.1:8000/strategies/relative-strength-pullback/card`
- `http://127.0.0.1:8000/market-data/symbols`
- `http://127.0.0.1:8000/market-data/SPY/bars`
- `http://127.0.0.1:8000/market-data/SPY/summary`
- `http://127.0.0.1:8000/market-data/SPY/quality`
- `http://127.0.0.1:8000/sentiment/symbols`
- `http://127.0.0.1:8000/sentiment/SPY/events`
- `http://127.0.0.1:8000/sentiment/SPY/summary`
- `http://127.0.0.1:8000/sentiment/SPY/snapshot`
- `http://127.0.0.1:8000/sentiment/SPY/quality`
- `http://127.0.0.1:8000/backtests/sample`
- `http://127.0.0.1:8000/discovery/ideas`
- `http://127.0.0.1:8000/discovery/ideas/relative-strength-pullback`
- `http://127.0.0.1:8000/discovery/ideas/relative-strength-pullback/card`
- `http://127.0.0.1:8000/discovery/lanes`
- `http://127.0.0.1:8000/discovery/genealogy/broad-fear-company-calm-pullback`
- `http://127.0.0.1:8000/discovery/ledger`
- `http://127.0.0.1:8000/rankings/sample`
- `http://127.0.0.1:8000/rankings/scorecards`
- `http://127.0.0.1:8000/rankings/scorecards/strategy-relative-strength-pullback`
- `http://127.0.0.1:8000/rankings/scorecards/strategy-relative-strength-pullback/card`
- `http://127.0.0.1:8000/rankings/top-research-candidates`
- `http://127.0.0.1:8000/rankings/weak-candidates`
- `http://127.0.0.1:8000/candidates/sample`
- `http://127.0.0.1:8000/candidates/equities`
- `http://127.0.0.1:8000/candidates/equities/spy-research-candidate`
- `http://127.0.0.1:8000/candidates/equities/spy-research-candidate/card`
- `http://127.0.0.1:8000/candidates/symbols`
- `http://127.0.0.1:8000/candidates/research-watchlist`
- `http://127.0.0.1:8000/portfolios/sample`
- `http://127.0.0.1:8000/portfolios/model`
- `http://127.0.0.1:8000/portfolios/model/core-research-portfolio`
- `http://127.0.0.1:8000/portfolios/model/core-research-portfolio/card`
- `http://127.0.0.1:8000/portfolios/styles`
- `http://127.0.0.1:8000/portfolios/model/core-research-portfolio/monitoring`

The strategy endpoints are read-only and use an in-memory sample registry. The market-data
and sentiment endpoints are read-only and use synthetic local CSV fixtures only. The backtesting
endpoints use local fixtures and produce research evidence only.

The `/ui` routes provide a local browser research cockpit. They are server-rendered, text/table
first, fixture-backed, and read-only. They do not include charts, authentication, broker
connections, external API calls, or trade action buttons.

The UI uses a plain-English language layer so research conclusions appear before technical metric
names. For example, backtests are introduced as historical tests, drawdown as worst drop, and
sentiment as market mood.

The discovery endpoints and `/ui/discovery-lab` page are read-only and in-memory. They separate
known strategy families from adaptive or novel hypotheses, and every differentiated idea must name
the simpler baseline it has to beat.

The ranking endpoints and `/ui/rankings` page are read-only and local. They score research
evidence from sample strategies, discovery records, fixture-backed backtests, and scaffolded
metadata. Rankings help decide what deserves deeper testing; they do not produce recommendations
or real-money permission.

The candidate endpoints and `/ui/candidates` page are read-only and local. They screen the small
built-in fixture universe for equities that may deserve more research by combining sample market
data, sample market mood, strategy matches, discovery ideas, and ranking scorecards. Candidates
are research triage only; they do not use live quotes and never approve real-money use.

The portfolio endpoints and `/ui/portfolios` page are read-only and local. The UI calls them
Pretend Portfolio Tests: practice portfolios built from sample data so EdgeLab can learn how it
might group ideas later. They are not recommendations, do not use live quotes, do not connect to
brokers, and never approve paper or real-money use. Cash is shown as intentional when evidence is
not strong enough.

To run a local fixture-backed backtest:

```bash
curl -X POST http://127.0.0.1:8000/backtests/run \
  -H "Content-Type: application/json" \
  -d '{"strategy_id":"relative-strength-pullback","symbol":"SPY"}'
```

## Run Tests

```bash
pytest
```

## Safety Warning

EdgeLab has no live trading functionality. It does not place orders, connect to brokers, request broker credentials, or make real market-data provider calls in this phase.
