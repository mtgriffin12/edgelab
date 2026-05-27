# Data Architecture

## Initial Principles

- Start with local SQLite.
- Do not add real provider integrations in Phase 0.
- Use adapters so future data providers can be added.
- Store timestamped data.
- Preserve point-in-time behavior.
- Avoid look-ahead bias.

## Data Categories

EdgeLab distinguishes:

- Raw data.
- Normalized data.
- Derived features.
- Sentiment events.
- Strategy results.

Each category should preserve source, timestamp, assumptions, and transformation context when practical.
