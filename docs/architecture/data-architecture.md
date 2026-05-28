# Data Architecture

## Initial Principles

- Start with local SQLite.
- Do not add real provider integrations in Phase 0 or Phase 2.
- Use adapters so future data providers can be added.
- Store timestamped data.
- Preserve point-in-time behavior.
- Avoid look-ahead bias.
- Use synthetic local fixtures first so validation behavior can be tested without network calls.

## Data Categories

EdgeLab distinguishes:

- Raw data.
- Normalized data.
- Derived features.
- Sentiment events.
- Strategy results.

Each category should preserve source, timestamp, assumptions, and transformation context when practical.

## Phase 2 Fixture Approach

Phase 2 uses local CSV fixtures as the only market-data source. The fixture provider is read-only,
synthetic, and intended for schema validation, quality checks, summaries, and API inspection.

The normalized bar model validates symbol normalization, explicit interval, positive OHLC values,
non-negative volume, OHLC relationships, source labels, and future timestamp guards. The fixture
provider reports structured quality issues for missing required fields, invalid bars, duplicate
symbol/timestamp/interval rows, unsorted timestamps, and empty datasets.

Real market-data integrations remain future work. Provider adapters should be introduced only after
the local models and quality rules are stable.

## Phase 3 Sentiment Fixture Approach

Phase 3 extends the fixture pattern to sentiment data. Sentiment fixtures are local, synthetic CSV
files used to validate timestamped event schemas, source weighting, recency decay, quality checks,
and read-only API inspection.

Sentiment remains data, not discretionary model opinion. Real news, social, or sentiment providers
remain future work after the local taxonomy and validation rules are stable.
