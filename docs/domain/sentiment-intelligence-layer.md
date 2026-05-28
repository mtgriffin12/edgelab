# Sentiment Intelligence Layer

Sentiment is a first-class signal layer. It is not discretionary model intuition.

## Requirements

- Sentiment must be timestamped.
- Sentiment must support source weighting, relevance, confidence, event type, novelty, and recency decay.
- Sentiment can confirm, veto, size-adjust, or contextualize trades.
- Sentiment must be backtested point-in-time.
- Every sentiment-enhanced strategy must be compared against the same strategy without sentiment.

## Initial Sentiment Categories

- Financial news.
- Social sentiment.
- Analyst/institutional sentiment.
- Options sentiment, future.
- Price/volume-implied sentiment.
- Macro/market-wide sentiment.

## Initial Event Taxonomy

- Earnings beat.
- Earnings miss.
- Guidance raise.
- Guidance cut.
- Analyst upgrade.
- Analyst downgrade.
- Price target raise.
- Price target cut.
- Product launch.
- Regulatory issue.
- Litigation.
- Fraud/accounting concern.
- M&A rumor.
- M&A confirmed.
- Insider buying.
- Insider selling.
- Short-seller report.
- Management change.
- Macro pressure.
- Sector rotation.
- Financing/dilution.
- Debt/liquidity issue.
- Dividend/buyback.

## Phase 3 Fixture Approach

Phase 3 uses local synthetic CSV fixtures as the only sentiment source. No real news, social,
broker, or sentiment provider integrations are included.

Sentiment events are normalized as timestamped data with source type, event type, headline or
summary, sentiment score, relevance, novelty, confidence, source weight, mention metadata, and
ingestion time. These fields support inspection and future point-in-time testing without relying on
model opinion.

The fixture provider supports source-weighted summaries, deterministic recency decay, ticker-level
snapshots, and structured quality issues. Snapshot context is descriptive only: it may describe
bullish, bearish, mixed, neutral, crowding-risk, or insufficient-data context, but it must not create
trade instructions.

Phase 3 does not join sentiment to market data. Divergence flags are derived from sentiment fixture
events only; richer market-data joins are future work.
