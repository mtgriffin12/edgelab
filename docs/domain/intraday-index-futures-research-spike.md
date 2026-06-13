# Intraday Index/Futures Research Spike

## Purpose

Phase 7X adds an Intraday Research Spike to test whether EdgeLab can represent
first-hour intraday setups as measurable events. The initial examples use synthetic
S&P 500-style and Nasdaq-style fixtures, plus a generic synthetic symbol, but the
architecture is not limited to those examples.

This is a research lane, not a product pivot. The spike studies whether opening
benchmarks, candle behavior, failed pushes, gap fades, momentum, and sit-out sessions
can be loaded, detected, simulated, and explained without visual chart intuition.

## Boundaries

- No live data.
- No real-time quotes.
- No external APIs.
- No broker integration.
- No prop-firm integration.
- No credentials.
- No charts.
- No paper or live execution.
- No recommendations.
- Real-money status is always Not allowed.

Synthetic fixtures can prove workflow shape, but they cannot prove that any setup is
profitable, timely, durable, or usable with real money.

## Why First-Hour Setups

Some disciplined intraday workflows focus on the first regular-session hour, opening
reference levels, and zero-or-one decisions per day. EdgeLab should only study that
kind of workflow if it can translate the behavior into explicit data:

- prior close,
- overnight and premarket references,
- regular open,
- opening range,
- first-hour high and low,
- candle strength and indecision,
- failure and continuation events.

The edge, if any, must be measurable before it can be trusted.

## Generic Instrument Design

The first fixtures include `ES_SYN` and `NQ_SYN` because they resemble common index
research examples. They are not architectural requirements. The `GEN_SYN` fixture
exists to prove that the provider, detector, simulator, API, and UI can analyze a
single non-ES/NQ fixture-backed symbol.

Future symbols need suitable intraday bars, instrument metadata, price movement
assumptions, tick assumptions where applicable, session metadata, and benchmark rules.

## No-Trade Days

No-trade days are first-class research output. A choppy open, tiny opening range,
conflicting contexts, or missing data should produce a sit-out result rather than a
forced setup. Restraint is part of the research workflow.

## Prop-Account Scaling

The prop-account model is generic arithmetic. It asks how sample P/L would interact
with a hypothetical qualification target, max loss limit, daily loss limit, payout
split, and copied-account count.

Scaling is an economic multiplier, not a trading edge. One copied bad decision across
ten accounts is ten bad decisions. No specific prop firm is modeled as truth.

## Future Path

Future work, if approved separately, would move in this order:

1. Historical intraday data.
2. Replay mode.
3. Live watch mode.
4. Paper signal mode.
5. Autonomous paper mode.
6. Human-approved live mode.
7. Possible autonomous live mode.

Each step needs explicit approval and deterministic risk controls before it can exist.

