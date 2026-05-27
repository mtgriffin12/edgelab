# System Architecture

EdgeLab is organized as small, testable modules with clear boundaries.

## Strategy Idea Generator

Creates candidate strategy ideas. It does not approve strategies and does not generate orders.

## Strategy Specification Engine

Turns ideas into structured strategy specifications with explicit universe, signal, entry, exit, sizing, risk, holding-period, and failure-condition fields.

## Market Data Layer

Provides market data through adapters. Phase 0 includes placeholders only and no real provider integrations.

## Sentiment Intelligence Layer

Stores and exposes timestamped sentiment events. Sentiment is structured data, not model opinion.

## Backtesting Engine

Evaluates strategies against historical data while preserving point-in-time behavior and avoiding look-ahead bias.

## Robustness / Walk-Forward Tester

Tests whether strategy behavior survives out-of-sample periods, regime changes, and parameter sensitivity.

## Strategy Ranking Engine

Ranks strategies using risk-adjusted evidence, robustness, drawdown behavior, and operational suitability.

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
