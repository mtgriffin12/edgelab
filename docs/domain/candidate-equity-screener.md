# Candidate Equity Screener

The Candidate Equity Screener helps EdgeLab decide which fixture-universe symbols deserve more
research. It is a research triage layer, not a recommendation engine.

## Purpose

Phase 7A combines local evidence that already exists in the app:

- synthetic market-data fixtures,
- synthetic sentiment fixtures,
- sample strategy specifications,
- Strategy Discovery Lab records,
- Strategy Ranking Engine scorecards.

The output is a research candidate card. It should explain why a symbol appeared, what supports
it, what is missing, what would change the system's mind, and why real-money use is not allowed.

## Research Boundaries

- Candidates are not proven opportunities.
- Candidates are not timely signals.
- Candidates are not approved for paper simulation or real-money use.
- The screener does not fetch live quotes or call external providers.
- The screener does not connect to brokers or create orders.
- Candidate scores are for prioritizing research attention only.

## Evidence Discipline

A useful candidate should have more than one reason to exist. For example, it may have a local
market fixture, a sentiment fixture, and matching strategy or discovery records. That still does
not make it trustworthy. It only makes it easier to decide what to inspect next.

Every candidate should show:

- what supports it,
- what evidence is missing,
- risk and data cautions,
- what would weaken or reject the idea,
- real-money status.

## Conservative Status

Candidate status should remain plain and cautious:

- worth more research,
- interesting but incomplete,
- watchlist only,
- insufficient evidence,
- blocked by risk,
- blocked by data quality,
- rejected for now.

No candidate should claim to be proven, profitable, ready for real money, or eligible for live
execution.
