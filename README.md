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

Current phase: **Phase 7X-2G SPY/QQQ Comparative Pattern Study**.

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
- `http://127.0.0.1:8000/ui/intraday-lab`
- `http://127.0.0.1:8000/ui/intraday-lab/replay`
- `http://127.0.0.1:8000/ui/intraday-lab/replay/RPLAY/replay-breakout-complete`
- `http://127.0.0.1:8000/ui/intraday-lab/multi-session-summary`
- `http://127.0.0.1:8000/ui/intraday-lab/pattern-results`
- `http://127.0.0.1:8000/ui/intraday-lab/no-trade-analysis`
- `http://127.0.0.1:8000/ui/intraday-lab/firstrate`
- `http://127.0.0.1:8000/ui/intraday-lab/firstrate/SPY`
- `http://127.0.0.1:8000/ui/intraday-lab/firstrate/SPY/latest-result`
- `http://127.0.0.1:8000/ui/intraday-lab/firstrate/QQQ/latest-result`
- `http://127.0.0.1:8000/ui/intraday-lab/firstrate/SPY/multi-session-summary`
- `http://127.0.0.1:8000/ui/intraday-lab/comparative-study`
- `http://127.0.0.1:8000/ui/intraday-lab/comparative-study/spy-qqq`
- `http://127.0.0.1:8000/ui/intraday-lab/comparative-study/spy-qqq/opening-range-failure`
- `http://127.0.0.1:8000/ui/intraday-lab/research-runs`
- `http://127.0.0.1:8000/ui/intraday-lab/GEN_SYN`
- `http://127.0.0.1:8000/ui/intraday-lab/prop-account-scaling`
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
- `http://127.0.0.1:8000/intraday/instruments`
- `http://127.0.0.1:8000/intraday/sessions`
- `http://127.0.0.1:8000/intraday/GEN_SYN/benchmarks`
- `http://127.0.0.1:8000/intraday/GEN_SYN/events`
- `http://127.0.0.1:8000/intraday/GEN_SYN/setups`
- `http://127.0.0.1:8000/intraday/GEN_SYN/simulation`
- `http://127.0.0.1:8000/intraday/GEN_SYN/simulation/card`
- `http://127.0.0.1:8000/intraday/prop-account/sample`
- `http://127.0.0.1:8000/intraday/prop-account/sample/card`
- `http://127.0.0.1:8000/intraday/history/provider-capabilities`
- `http://127.0.0.1:8000/intraday/history/firstrate/files`
- `http://127.0.0.1:8000/intraday/history/firstrate/dry-run`
- `http://127.0.0.1:8000/intraday/history/firstrate/SPY/sessions`
- `http://127.0.0.1:8000/intraday/history/firstrate/SPY/sessions/SPY-2022-09-30`
- `http://127.0.0.1:8000/intraday/history/firstrate/SPY/sessions/SPY-2022-09-30/replay`
- `http://127.0.0.1:8000/intraday/history/firstrate/SPY/sessions/SPY-2022-09-30/replay/card`
- `http://127.0.0.1:8000/intraday/history/firstrate/SPY/multi-session-summary`
- `http://127.0.0.1:8000/intraday/history/firstrate/SPY/pattern-results`
- `http://127.0.0.1:8000/intraday/history/firstrate/SPY/no-trade-analysis`
- `http://127.0.0.1:8000/intraday/research-runs`
- `http://127.0.0.1:8000/intraday/research-runs/latest?symbol=SPY`
- `http://127.0.0.1:8000/intraday/comparative-study/spy-qqq`
- `http://127.0.0.1:8000/intraday/comparative-study/spy-qqq/opening-range-failure`
- `http://127.0.0.1:8000/intraday/comparative-study/spy-qqq/card`
- `http://127.0.0.1:8000/intraday/history/sessions`
- `http://127.0.0.1:8000/intraday/history/SPY/sessions`
- `http://127.0.0.1:8000/intraday/history/SPY/sessions/spy-2024-01-02-historical`
- `http://127.0.0.1:8000/intraday/history/SPY/sessions/spy-2024-01-02-historical/bars`
- `http://127.0.0.1:8000/intraday/replay/sample`
- `http://127.0.0.1:8000/intraday/replay/RPLAY/replay-breakout-complete`
- `http://127.0.0.1:8000/intraday/replay/RPLAY/replay-breakout-complete/card`
- `http://127.0.0.1:8000/intraday/multi-session-summary`
- `http://127.0.0.1:8000/intraday/multi-session-summary/card`
- `http://127.0.0.1:8000/intraday/pattern-results`
- `http://127.0.0.1:8000/intraday/pattern-results/RPLAY`
- `http://127.0.0.1:8000/intraday/no-trade-analysis`
- `http://127.0.0.1:8000/intraday/no-trade-analysis/RPLAY`

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

The saved research run endpoints and `/ui/intraday-lab/research-runs` page store compact local
summaries in an ignored SQLite database under `data/processed/research_runs/`. They do not store
raw CSV rows, call external services, or make results actionable. Freshness checks compare saved
source-file metadata and assumptions against the current ignored local file.

The SPY/QQQ comparative study endpoints and `/ui/intraday-lab/comparative-study` pages compare
failed early moves across current saved local SPY and QQQ research runs. The technical setup name
is Opening Range Failure, but the UI explains it as an early move that could not hold. The detail
comparison may reuse ignored local FirstRate CSV files for per-session evidence, with process-local
caching to avoid repeated work. The study is a guide for the next controlled experiment only. It
does not create recommendations, prove an edge, enable paper mode, or approve real-money use.

The intraday endpoints and `/ui/intraday-lab` page are read-only and local. They study synthetic
first-hour fixture sessions by calculating opening benchmarks, detecting measurable events,
generating setup or sit-out candidates, and calculating one hypothetical short-hold result when
the fixture supports it. Initial examples use S&P 500-style and Nasdaq-style fixtures, but the
provider and API are generic enough to support any fixture-backed symbol with suitable metadata.
The intraday spike does not fetch live data, show charts, connect to brokers, model a real
prop-firm rulebook, or approve paper or real-money use.

The historical intraday endpoints are read-only and local. They import tiny sample CSV fixtures
through a vendor-neutral boundary so EdgeLab can inspect historical session readiness before replay
or broader research. They do not call external APIs, use provider SDKs, fetch live quotes, or
approve paper or real-money use. Real downloaded data should stay outside source control under
ignored paths such as `data/raw/` or `data/processed/`.

The historical replay endpoints are read-only and local. The UI calls this a Past Morning Practice
Test: one imported historical session is reviewed one minute at a time so EdgeLab only uses what was
visible then. It can find a practice setup, sit out, or report not enough data, but it does not
calculate multi-session pattern statistics, watch live data, connect to brokers, use paid providers,
or produce recommendations.

The multi-session historical replay endpoints are read-only and local. The UI calls this a
Many-Morning Practice Test: EdgeLab reuses the same one-morning replay engine across local CSV
sessions, summarizes repeated practice setups, and reviews sit-out reasons in plain English. The
committed fixtures are tiny workflow tests only, so the default conclusion should stay "Not enough
examples yet." This layer does not fetch live data, call provider APIs, use paid provider SDKs,
connect to brokers, add charts, schedule jobs, deploy services, or produce recommendations.

The FirstRate historical import endpoints are read-only and local. They inspect ignored files under
`data/raw/historical_intraday/firstratedata/` with FirstRate's
`timestamp,open,high,low,close,volume` format, normalize rows into EdgeLab's historical intraday
shape, and produce dry-run summaries. Real downloaded market data must not be committed, and this
phase does not write processed files, fetch data, call vendors, connect to brokers, add charts, or
approve paper or real-money use.

The FirstRate replay integration is also read-only and local. It lets EdgeLab replay one local
FirstRate SPY or QQQ morning and summarize many local mornings with the existing no-look-ahead
replay engine. It reports first-hour completeness so missing or duplicate first-hour minutes stay
visible before any replay is trusted. These results are not live signals, not recommendations, and
real-money status remains Not allowed.

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
