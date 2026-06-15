# System Architecture

EdgeLab is organized as small, testable modules with clear boundaries.

## Strategy Idea Generator

Creates candidate strategy ideas. It does not approve strategies and does not generate orders.

## Strategy Discovery Lab

Classifies known strategy families, adaptive variants, and novel hypotheses before they become
formal strategy specs. Phase 5C stores local in-memory discovery records, baseline requirements,
genealogy, current-regime-fit scaffolding, and experiment ledger entries. It is read-only and does
not run external generation or promote ideas automatically.

## Strategy Specification Engine

Turns ideas into structured strategy specifications with explicit universe, signal, entry, exit, sizing, risk, holding-period, and failure-condition fields.

## Market Data Layer

Provides market data through adapters. Phase 0 includes placeholders only and no real provider integrations.

## Sentiment Intelligence Layer

Stores and exposes timestamped sentiment events. Sentiment is structured data, not model opinion.

## Backtesting Engine

Evaluates strategies against historical data while preserving point-in-time behavior and avoiding look-ahead bias.

Phase 4 starts with a local fixture-based engine that supports one simple placeholder signal for
research evidence generation. It records simulated fills, closed simulated positions, equity curve
points, assumptions, metrics, and quality issues. Unsupported strategies are flagged explicitly
rather than silently approximated.

## Robustness / Walk-Forward Tester

Tests whether strategy behavior survives out-of-sample periods, regime changes, and parameter sensitivity.

## Strategy Ranking Engine

Ranks strategies using risk-adjusted evidence, robustness, drawdown behavior, and operational suitability.

Phase 6 implements a local Strategy Metrics and Ranking Engine. It compares sample strategy specs,
discovery records, and fixture-backed backtest results with conservative, plain-English scorecards.
It ranks research evidence only and does not produce recommendations, external calls, paper
promotion, or live-trading permission.

## Candidate Equity Screener

Surfaces local research candidates from the fixture universe by combining sample market data,
sample sentiment context, sample strategy matches, discovery ideas, and ranking scorecards.
Phase 7A is read-only, in-memory, and fixture-backed. It does not fetch live quotes, create
recommendations, place orders, promote symbols, or claim that a candidate is proven.

## Model Portfolio Engine

Assembles hypothetical research portfolios from fixture-backed candidates. Phase 7B creates local
model portfolios with starting capital, explicit cash, target weights, position reasons,
constraint checks, monitoring notes, and real-money status. It is a bridge toward future paper
portfolio simulation, but it does not create paper orders, broker calls, live signals, or
real-money recommendations.

## Intraday Research Spike

Explores whether first-hour intraday setup behavior can be represented as measurable events rather
than chart intuition. Phase 7X adds a generic fixture-backed intraday package for instruments,
bars, opening benchmarks, candle classification, event detection, setup or sit-out candidates,
hypothetical short-hold simulation, generic prop-account scaling arithmetic, Markdown cards, API
routes, and text/table UI pages.

The initial fixtures include S&P 500-style and Nasdaq-style examples, plus a generic symbol to
prove that ES/NQ are examples rather than architectural requirements. The spike is read-only,
synthetic, local, and research-only. It does not add live data, real-time quotes, broker calls,
prop-firm integrations, charting, paper execution, or live execution.

## Historical Intraday Import Foundation

Loads local historical intraday CSV files through a vendor-neutral provider boundary. Phase 7X-2A
adds normalized historical bars, historical instruments, session summaries, data-source metadata,
provider capabilities, quality issues, and session readiness labels. It is local, read-only, and
research-only. It does not add replay mode, live data, external provider calls, credentials,
broker calls, prop-firm integrations, charting, paper execution, or live execution.

## Historical Intraday Replay Engine

Replays one imported historical intraday session bar by bar using only local CSV-backed data.
Phase 7X-2B converts imported bars into the existing intraday setup detector shape, reveals only
bars whose timestamps are at or before the replay clock, marks setup or sit-out decisions for
research, and records a hypothetical result only after the later exit bar is visible. It is local,
read-only, and research-only. It does not add pattern statistics, live watch mode, external
provider calls, credentials, broker calls, prop-firm integrations, charting, paper execution, or
live execution.

## Historical Intraday Multi-Session Pattern Results

Runs the historical replay engine across many local CSV-backed sessions and aggregates the
research-only outcomes. Phase 7X-2C adds conservative setup-family summaries, sit-out reason
review, cost-sensitivity flags, quality warnings, Markdown cards, API routes, and text/table UI
pages. It reuses the no-look-ahead replay contract from Phase 7X-2B and does not add live data,
external provider calls, credentials, broker calls, prop-firm integrations, charting, scheduling,
paper execution, or live execution.

## FirstRate Historical CSV Normalizer

Normalizes ignored local FirstRate historical intraday CSV files into EdgeLab's canonical
historical intraday shape. Phase 7X-2D reads files from
`data/raw/historical_intraday/firstratedata/`, infers symbols from filenames, applies explicit
metadata, validates rows, and reports dry-run summaries. It is local, read-only, and research-only.
It does not commit real data, create processed outputs, call providers, require credentials, fetch
live data, add charting, or connect to brokers.

## FirstRate Replay Integration

Uses normalized ignored FirstRate SPY and QQQ files as a local historical data provider for the
existing replay engine and multi-session runner. Phase 7X-2E adds FirstRate-specific API and UI
routes plus first-hour completeness reporting, while preserving the Phase 7X-2B no-look-ahead
contract. It does not add live data, provider SDKs, credentials, broker calls, prop-firm
integrations, charting, scheduling, workers, paper execution, or live execution.

## Saved Research Runs

Stores compact local results from deliberate FirstRate many-morning analyses so later page loads can
show the latest saved result quickly. The store is SQLite through the Python standard library, lives
under ignored `data/processed/research_runs/`, and saves summary JSON, evidence details, quality
warnings, and source-file fingerprints only. It does not add external calls, live data, scheduler
work, broker connectivity, or recommendations.

## SPY/QQQ Comparative Pattern Study

Compares failed early moves across SPY and QQQ using current saved local research runs plus ignored
local FirstRate files for detailed replay evidence. The technical setup name remains Opening Range
Failure, but primary UI copy uses the beginner-friendly label. The comparison service is read-only
and uses process-local caching keyed by source-file signatures and replay assumptions. It does not
create saved runs on page load, write processed outputs, call external services, create strategy
variants, promote paper mode, or produce recommendations.

## Controlled Variant Study

Compares a fixed set of pre-declared failed-early-move variants against a broad local baseline.
Phase 7X-2H uses SPY first, while keeping the service/request structure generic enough for future
supported instruments. The service requires current saved local research context, recomputes
variant evidence from ignored local files, and caches results by source-file signatures,
assumptions, variant spec version, and code version. It does not tune thresholds after results,
persist variant outputs, create background work, call external services, promote paper mode, or
produce recommendations.

## Out-of-Sample Gate

Runs a generic time-based stability check for fixed intraday variants. Phase 7X-2I first uses it
for SPY failed early move variants with QQQ as paired context. The service requires current saved
full-symbol research runs, recomputes discovery and holdout-style evidence from ignored local files
in memory, and caches by symbol pair, variant IDs, split dates, replay assumptions, file
signatures, and code version. It does not create saved runs on page load, persist gate outputs,
call external services, promote paper mode, or produce recommendations.

## Intraday Research View Model

Presents intraday work by strategy idea rather than by implementation page. The view model rolls up
saved-result freshness, local file readiness, SPY/QQQ comparison, controlled variant study, and
out-of-sample gate output into one Failed Early Move research summary. It does not add research
logic, persist results, call external services, or change the underlying evidence services.

## Intraday Strategy Discovery Sprint

Runs a deterministic local sprint across a fixed first library of intraday idea families. Phase
7X-2J scans available local historical symbols, applies simple rule families, compares earlier and
later local periods, and returns a plain-English research scoreboard. The future AI boundary is a
schema for proposed locked hypotheses only. The service does not call AI, call external APIs, write
saved research runs, persist sprint results, create background jobs, promote paper mode, or produce
recommendations.

## Paper Trading Simulator

Simulates trades and paper positions without real broker order execution.

## Risk Management Engine

Applies deterministic veto rules. It can reject any signal, strategy, paper action, or future live action.

## Reporting Engine

Produces Markdown, CSV, and structured summaries for reviews and decisions.

## Trade Journal / Audit Log

Records strategy decisions, signals, vetoes, rejected trades, assumptions, and lessons.

## Broker Abstraction Layer

Defines future broker interfaces without credentials, API calls, or orders in Phase 0.

## Live Trading Gatekeeper

Future only. Disabled by default. Live trading requires explicit future authorization and deterministic controls.
