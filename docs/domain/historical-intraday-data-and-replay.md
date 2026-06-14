# Historical Intraday Data and Replay

## Purpose

Phase 7X-2A starts the move from synthetic intraday fixtures toward historical
intraday research. This phase only adds a local CSV import foundation. It does
not add replay mode, live data, vendor integrations, broker connections, prop-firm
integrations, charts, or trade recommendations.

Historical intraday data is research input. It can help EdgeLab decide what to
study next, but it cannot prove that any setup works or is ready for real money.

Real-money status is always Not allowed.

## Why Local CSV Comes First

Local CSV import lets EdgeLab test the shape of historical data before choosing a
vendor. It keeps early work:

- local,
- repeatable,
- credential-free,
- vendor-neutral,
- safe for review.

This avoids locking the app to a paid provider before the normalized bar format,
session metadata, quality checks, and future replay rules are stable.

## Where Historical Files Should Live

Tiny synthetic test fixtures may live under:

`tests/fixtures/historical_intraday/`

Real downloaded or user-supplied historical files should not be committed. They
should live under ignored local paths such as:

- `data/raw/`
- `data/processed/`

Those directories are ignored because real market data may be large, licensed, or
not appropriate for source control.

## Canonical CSV Format

Required columns:

`symbol,raw_timestamp,source_timezone,interval,open,high,low,close,volume,session_type,session_id,provider,dataset_id,adjustment_mode`

Optional columns:

`display_name,point_value,tick_size,tick_value,exchange_or_venue,regular_session_open,regular_session_close`

Rules:

- `symbol` is normalized to uppercase.
- `raw_timestamp` is parsed using `source_timezone`.
- Internal timestamps are normalized to UTC.
- `interval` supports `one_minute` for this phase.
- `session_type` should use `overnight`, `premarket`, `regular_first_hour`, or
  `regular_session`.
- `adjustment_mode` must be explicit: `unadjusted`, `adjusted`,
  `split_adjusted`, or `unknown`.
- Missing required columns produce quality issues.
- Invalid rows produce quality issues where practical instead of crashing the app.

## Timezone Handling

The imported file must state its source timezone. EdgeLab preserves the raw
timestamp text and the source timezone, then normalizes the timestamp to UTC for
internal comparisons. This protects future replay from mixing local market time
with machine time.

## Adjustment Mode Handling

Adjustment mode is recorded for every imported bar. Unadjusted data is preferred
for replay realism, but EdgeLab accepts adjusted, split-adjusted, and unknown
labels as explicit metadata. Unknown adjustment mode is a reason to review the
session before trusting it.

## Session Readiness

Historical sessions are classified before any future replay step:

- Ready for future replay: at least five valid one-minute first-hour bars and no
  critical quality issues.
- Incomplete: some useful data exists, but first-hour coverage is too thin.
- Not usable yet: critical schema, timestamp, or price problems exist.
- Needs review: duplicates, unsorted bars, unknown adjustment mode, or other
  non-critical issues need human review.

Readiness is not a trading signal. It only says whether the data is usable for
the next research step.

## Quality Issues

The local CSV provider reports structured quality issues for missing columns,
blank required values, invalid timestamps, invalid OHLC values, duplicate bars,
unsorted bars, unsupported intervals, and unknown adjustment modes.

Quality warnings should remain visible because weak data can make a pattern look
more meaningful than it is.

## Future Replay Mode

Replay mode is future work. When approved later, it should replay historical bars
bar by bar as if EdgeLab does not know the future. It must avoid look-ahead,
preserve next-bar entry timing after a signal bar, and tell a plain-English story
about what EdgeLab knew at each point.

## Future Vendor Research

Future paid data providers may be investigated later, but Phase 7X-2A does not
add provider SDKs, credentials, or external calls. The current paid-provider
placeholder exists only to show where a future adapter could fit.
