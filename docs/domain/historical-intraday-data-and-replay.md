# Historical Intraday Data and Replay

## Purpose

Phase 7X-2A started the move from synthetic intraday fixtures toward historical
intraday research with a local CSV import foundation. Phase 7X-2B adds a local
replay engine that inspects one imported session bar by bar. Phase 7X-2C adds a
local many-session summary over that same replay engine. It does not add live
data, vendor integrations, broker connections, prop-firm integrations, charts,
live watch mode, paper trading, or trade recommendations.

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
session metadata, quality checks, and replay rules are stable.

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
internal comparisons. This protects replay from mixing local market time
with machine time.

## Adjustment Mode Handling

Adjustment mode is recorded for every imported bar. Unadjusted data is preferred
for replay realism, but EdgeLab accepts adjusted, split-adjusted, and unknown
labels as explicit metadata. Unknown adjustment mode is a reason to review the
session before trusting it.

## Session Readiness

Historical sessions are classified before replay:

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

## Phase 7X-2B Historical Replay Mode

Replay mode reveals one local historical session bar by bar as if EdgeLab were
watching the morning unfold. It answers:

- what EdgeLab knew at the open,
- what changed during the first hour,
- whether EdgeLab marked a setup for research or sat out,
- what happened afterward once later bars became visible,
- whether the replay was complete, incomplete, or blocked by data quality,
- what EdgeLab should check next.

The replay engine must run without future knowledge. At any replay step, EdgeLab
may only use bars whose timestamps are at or before the replay clock. Setup
detection can occur only after the signal bar is visible. Hypothetical entry uses
the next available bar open after the signal bar. Hypothetical exit is recorded
only after the replay clock reaches the exit bar.

## What EdgeLab Knows When

Before the regular open, EdgeLab may know prior, overnight, or premarket context
only if those bars exist in the local file. At the regular open, it knows the
regular open. After five regular-session one-minute bars, it knows the opening
range. As the session unfolds, it knows first-hour high and low so far. Final
first-hour levels and final hypothetical results are after-the-fact information
and must not be used early.

## Why One Replay Is Not Proof

One replay can show whether the process is honest and understandable. It cannot
prove an edge, profitability, timeliness, or readiness for real money. Replay is
a bridge to future pattern statistics across many clean sessions, not a result
that can stand alone.

## Phase 7X-2C Multi-Session Pattern Results

The Many-Morning Practice Test runs the existing one-session replay engine across
local CSV sessions and summarizes what repeated. It answers:

- how many local mornings were found,
- how many were clean enough to compare,
- which practice setup families appeared,
- whether any setup deserves more testing,
- when EdgeLab sat out,
- whether sitting out looked helpful or questionable,
- what might make the summary misleading,
- what EdgeLab should test next.

The committed historical fixtures are intentionally tiny workflow samples. The
default conclusion should remain "Not enough examples yet" until many more clean
local CSV mornings are available. The summary can help choose the next research
question, but it cannot prove a pattern works, imply timeliness, or approve paper
or real-money use.

Phase 7X-2C keeps the no-look-ahead rules from Phase 7X-2B. Each session replay
only sees bars visible at that replay time, setup detection receives only visible
bars, pretend starts use the next available bar after the signal bar, and pretend
finishes are recorded only once the finish bar is visible.

No-trade analysis is treated as research, not inactivity. A sit-out rule can be
useful, harmful, inconclusive, or need more examples. These labels are plain
review labels only and do not create action instructions.

## Future Vendor Research

Future paid data providers may be investigated later, but the current historical
intraday phases do not add provider SDKs, credentials, or external calls. The
current paid-provider placeholder exists only to show where a future adapter
could fit.
