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
