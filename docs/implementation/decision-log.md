# Decision Log

## DEC-001: Standalone Repository

Build EdgeLab as a standalone repo separate from Neo.

## DEC-002: Research Before Live Trading

Build as a research and validation system before any live trading bot.

## DEC-003: Model Portfolio

Use $50,000 as the initial model portfolio assumption.

## DEC-004: Drawdown Tolerance

Use 15% as the initial max drawdown tolerance.

## DEC-005: Performance Objective

Optimize first for percentage return and risk-adjusted performance, not fixed monthly dollar profit.

## DEC-006: Initial Asset Scope

Start with US equities and ETFs.

## DEC-007: Initial Trading Horizon

Start with daily and multi-day swing strategies.

## DEC-008: Data Cost Posture

Use free/low-cost data first, but design provider adapters for paid data later.

## DEC-009: Sentiment Treatment

Treat sentiment as structured timestamped data, not opinion.

## DEC-010: Architecture Posture

Use local-first architecture now, with cloud-readiness later.

## DEC-011: Initial UX

Use text/table UX first; no charts in Phase 0.

## DEC-012: Paper Trading Direction

Use Alpaca paper trading later as the first paper-trading integration.

## DEC-013: Phase 0 Trading Boundary

No live trading functionality in Phase 0.

## DEC-014: Phase 1 Strategy Foundation

Phase 1 implements structured strategy specification and registry before market data, backtesting, sentiment ingestion, paper trading, or live execution.

## DEC-015: Phase 2 Local Fixture Market Data

Phase 2 implements local fixture-based market-data ingestion before real provider integrations.

## DEC-016: Phase 3 Local Fixture Sentiment Intelligence

Phase 3 implements local fixture-based sentiment intelligence before real news, social, or sentiment provider integrations.

## DEC-017: Phase 4 Local Fixture Backtesting

Phase 4 implements a local fixture-based backtesting engine before real data providers or broker integrations.

## DEC-018: Phase 5A Local Research Cockpit

Phase 5A implements a local text/table research cockpit before charts, cloud deployment, authentication, or live integrations.

## DEC-019: Phase 5B Plain-English UX Language

Phase 5B adds a plain-English UX language layer before adding more analytical complexity.

## DEC-020: Phase 5C Strategy Discovery Lab

Phase 5C implements a Strategy Discovery Lab that supports both known strategy families and novel edge hypotheses, with baseline challenger rules and plain-English evidence requirements.

## DEC-021: Phase 6 Strategy Metrics and Ranking Engine

Phase 6 implements a local Strategy Metrics and Ranking Engine that ranks research evidence rather than producing trade recommendations.

## DEC-022: Phase 7A Candidate Equity Screener

Phase 7A implements a local Candidate Equity Screener that surfaces research-only equity candidates from fixture evidence, strategy matches, discovery ideas, and ranking scorecards without live quotes, provider integrations, or real-money permission.

## DEC-023: Phase 7B Model Portfolio Engine

Phase 7B implements a local Model Portfolio Engine that assembles research-only simulated portfolios before paper trading or live execution.

## DEC-024: Phase 7X Intraday Research Spike

Phase 7X implements an Intraday Research Spike to evaluate first-hour setup detection and generic prop-account scaling before any live data, paper trading, or execution integration.

## DEC-025: Phase 7B Pretend Portfolio Tests UX

Phase 7B user-facing portfolio UI uses "Pretend Portfolio Tests" and plain-English decision intelligence before traditional portfolio metrics.

## DEC-026: Phase 7X-2A Historical Intraday CSV Import

Phase 7X-2A implements a local historical intraday CSV import foundation before vendor integrations, replay mode, live data, or execution.

## DEC-027: Phase 7X-2B Historical Intraday Replay

Phase 7X-2B implements historical intraday replay so EdgeLab can inspect one imported session bar by bar without future knowledge.

## DEC-028: Phase 7X-2C Multi-Session Historical Replay Summaries

Phase 7X-2C adds multi-session historical replay summaries and no-trade analysis so EdgeLab can evaluate repeated first-hour patterns without implying real-money readiness.

## DEC-029: Phase 7X-2D FirstRate Historical Intraday CSV Normalizer

Phase 7X-2D adds a FirstRate historical intraday CSV normalizer and local dry-run import path so EdgeLab can inspect real SPY/QQQ CSV samples without committing data or adding vendor integrations.

## DEC-030: Phase 7X-2E FirstRate Replay Integration

Phase 7X-2E connects local ignored FirstRate SPY/QQQ CSV files to replay and multi-session summaries while keeping all outputs research-only and real-money use blocked.

## DEC-031: Phase 7X-2F Saved Research Runs

DEC-031: Phase 7X-2F adds local saved research runs so expensive FirstRate many-morning analyses can be run deliberately and viewed quickly without recomputing on every page load.

## DEC-032: Phase 7X-2G SPY/QQQ Comparative Pattern Study

DEC-032: Phase 7X-2G adds a SPY/QQQ comparative pattern study so EdgeLab can investigate why failed early moves, technically Opening Range Failure, behaved differently across symbols before generating strategy variants.

## DEC-033: Phase 7X-2H SPY Early Move Failed Controlled Variant Study

DEC-033: Phase 7X-2H adds a controlled SPY Early Move Failed variant study so EdgeLab can compare pre-declared versions of one pattern before generating broader strategy experiments. Variants are fixed before review, no parameter mining or post-result tuning is allowed, and a future experiment ledger is required before broader variant generation.

## DEC-034: Phase 7X-2I Generic Out-of-Sample Gate

DEC-034: Phase 7X-2I adds a generic out-of-sample gate for fixed intraday variants, first applied to SPY Early Move Failed variants. The gate requires current saved local SPY and QQQ research runs, recomputes a fixed time-based discovery versus holdout-style split from ignored local FirstRate files, and does not save gate outputs. The current result must be described as a holdout-style check or first honesty check, not proof, validation, paper-mode readiness, live-signal readiness, or real-money readiness.

DEC-034 also simplifies the Intraday Lab IA around strategy ideas and results. Intraday primary navigation now points to Research, Trading, and Saved Results. FirstRate, SPY vs QQQ, variant, out-of-sample, and symbol-specific pages remain available as detailed evidence pages rather than primary product pages.

## DEC-035: Phase 7X-2J AI-Assisted Strategy Discovery Sprint

DEC-035 adds a local strategy discovery sprint over a fixed first library of intraday idea
families: Failed Early Move, Gap Fade, Gap Continuation, First 15-Minute Breakout, First 30-Minute
Breakout, Opening Range Reclaim, Strong Open / Weak Follow-Through, and SPY/QQQ Divergence. The
sprint reads local historical files, ranks only conservative research next steps, and exposes a
future AI idea intake schema for locked hypotheses. This phase does not call AI, optimize prompts,
write saved research runs, create background work, fetch data, promote paper mode, or approve
real-money use.

## DEC-036: Phase 7X-2K Expanded Free FirstRate Universe

DEC-036 expands the local discovery sprint to every matching ignored FirstRate sample file available
under the local raw-data folder. General strategy ideas run across the discovered free universe,
while SPY/QQQ Divergence remains specific to SPY and QQQ. The research scoreboard stays
strategy-first and reports data quality by symbol so local file problems are visible. This phase
does not commit CSV data, call AI, call external APIs, write saved sprint results, create symbol
page sprawl, promote paper mode, or approve real-money use.

## DEC-037: Phase 7X-2L Structured AI Idea Batch Testing

DEC-037 adds structured AI idea batch testing so EdgeLab can evaluate AI-proposed intraday
hypotheses using deterministic local historical tests. EdgeLab may read locked idea specs, but it
does not call AI, connect to a live model, or let AI judge whether an idea advanced. Unsupported
rule families are separated before testing instead of being approximated. User-authored idea text
is not rejected based on wording; supported ideas run locally against ignored FirstRate files, with
results computed on demand and not saved in this phase.

## DEC-038: Phase 7X-2M Idea Batch Paste Runner

DEC-038 adds a paste runner so users can validate and run structured idea batch JSON from the
EdgeLab UI without Codex. The page exposes the required schema, allowed local rule families,
and a copyable example. Pasted batches run temporarily against local historical data only. This
phase does not save pasted batches or results, call AI, call external APIs, fetch live data, promote
paper mode, or approve real-money use.

## DEC-039: Phase 7X-2O Remove Idea-Text Safety Blocks

DEC-039 removes content-based idea-text rejection from the idea batch paste, validate, and run
workflow. The validator still checks JSON shape, required fields, research-only status, real-money
status, data types, supported rule-family classification, and local testability. It no longer scans
user-authored idea text for trading, proof, profit, readiness, or other wording. Unsupported ideas
remain classified as `unsupported_rule`; supported ideas remain temporary local research only.

## DEC-040: Phase 7X-2T MarketData.app SPY/CSGP Local Data Helper

DEC-040 adds an explicit local command-line helper for downloading recent SPY and CSGP 1-minute
candles from MarketData.app and normalizing them into ignored CSV files for the future morning
divergence study. The helper supports dry-run planning without credentials, reads the API token
only from `MARKETDATA_APP_TOKEN` for real downloads, and writes only to local ignored raw-data
paths. Normal app page loads do not call MarketData.app, tests do not use the network, and the
feature does not add live data, provider SDKs, trading, broker integration, paper-mode promotion,
or real-money readiness.
