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
- `data/raw/historical_intraday/firstratedata/`

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
- `session_type` should use `overnight`, `premarket`, `regular_first_hour`,
  `regular_session`, or `after_hours`.
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

## Phase 7X-2D FirstRate Local CSV Normalizer

Phase 7X-2D adds a local dry-run path for FirstRate historical intraday CSV files. FirstRate files
should live under the ignored folder:

`data/raw/historical_intraday/firstratedata/`

The detected FirstRate format is:

`timestamp,open,high,low,close,volume`

EdgeLab adds the metadata needed by its canonical historical intraday model: symbol, source
timezone, interval, session type, session id, provider, dataset id, and adjustment mode. Symbol is
inferred from filenames such as `SPY_1min_firstratedata.csv` unless a caller supplies it directly.
The source timezone assumption is `America/New_York` unless overridden.

FirstRate local times are classified as premarket from 04:00:00 through 09:29:59, regular first
hour from 09:30:00 through 10:29:59, regular session from 10:30:00 through 16:00:00, and
after-hours after 16:00:00 through 20:00:00. Normal after-hours rows are retained as context and
do not create one quality issue per row.

The normalizer is local and read-only. It streams rows for dry-run inspection, reports quality
issues, and does not create processed output files. Real downloaded market data must not be copied
into `tests/fixtures/` or committed to source control.

FirstRate dry-run output remains research-only. Real-money status remains Not allowed. Unknown
adjustment mode is recorded as source metadata, but it does not automatically make every otherwise
clean session unready for replay. Replay and pattern conclusions still require enough clean
sessions, known assumptions, and later validation before trust can increase.

## Phase 7X-2E FirstRate Replay Integration

Phase 7X-2E connects ignored local FirstRate SPY and QQQ files to the existing Past Morning
Practice Test and Many-Morning Practice Test workflows. EdgeLab reuses the Phase 7X-2B replay
engine, so replay still reveals one bar at a time, setup detection receives only visible bars,
pretend starts use the next available bar after the signal bar, and pretend finishes appear only
after the finish bar is visible.

The FirstRate replay bridge reads normalized local FirstRate bars and converts them into the same
replay-compatible shape used by local fixture sessions. It does not duplicate replay logic, write
processed output files, call vendors, fetch live data, use credentials, add charts, or connect to
brokers.

First-hour completeness is reported for every FirstRate session. EdgeLab checks the expected
regular first-hour one-minute timestamps, the actual first-hour bars, missing timestamps, duplicate
timestamps, and a plain label: `complete`, `minor_gaps`, `major_gaps`, or `replay_unsafe`. Minor
gaps can still be replayed if the replay engine can handle the session safely, but the gap must be
visible in the API and UI. Bigger gaps or duplicate first-hour timestamps require caution before
trust increases.

FirstRate replay and many-morning outputs remain research-only. They are not live signals, not
recommendations, and not real-money permission. Real-money status remains Not allowed.

## Future Vendor Research

Future paid data providers may be investigated later, but the current historical intraday phases do
not add provider SDKs, credentials, or external calls. The current paid-provider placeholder exists
only to show where a future adapter could fit.

## Phase 7X-2T MarketData.app SPY/CSGP Local Data Helper

Phase 7X-2T adds a local command-line helper for the SPY/CSGP morning divergence research question.
It plans or runs an explicit MarketData.app historical candle download for recent 1-minute SPY and
CSGP data, normalizes both files to:

`timestamp,open,high,low,close,volume`

The target files are:

`data/raw/historical_intraday/firstratedata/SPY_recent_1min.csv`

`data/raw/historical_intraday/firstratedata/CSGP_recent_1min.csv`

Those files must stay ignored and untracked. The normal app pages do not fetch provider data, tests
do not call the network, and EdgeLab does not store API tokens. The CLI reads the token only from
`MARKETDATA_APP_TOKEN` when a real download is requested.

Dry-run first:

```bash
PYTHONPATH=src python -m edgelab.intraday.marketdata_app_downloader --symbols SPY CSGP --months 12 --dry-run
```

Actual local download, only after reviewing the dry-run and setting a token:

```bash
export MARKETDATA_APP_TOKEN="[paste your MarketData.app token]"
PYTHONPATH=src python -m edgelab.intraday.marketdata_app_downloader --symbols SPY CSGP --months 12
```

Use matching SPY and CSGP date ranges. The first target window is trailing 12 months, with optional
18-month and 24-month windows if more local history is needed. If free daily credits are not enough,
run smaller windows or upgrade only if the user chooses.

The SPY/CSGP audit now recognizes the recent filenames above. It still shows the legacy SPY
FirstRate file range separately so old SPY-only data is not mixed with current CSGP data.

This helper does not add live data to the app, real-time quotes, provider SDKs, charting, broker
integration, paper-mode promotion, or recommendations. Real-money status remains Not allowed.

## Phase 7X-2F Saved Research Runs

Phase 7X-2F adds saved local research runs for expensive FirstRate many-morning analysis. EdgeLab
now lets a user run local analysis deliberately, store a compact result in the ignored local
research database, and reopen the latest saved result quickly later.

Saved runs include plain-English bottom line, what EdgeLab tested, what EdgeLab found, whether this
is enough to trust, what to test next, evidence details, source-file metadata, and quality warnings.
They do not include raw CSV rows and do not make the result a recommendation.

Freshness matters because ignored local files can change. If the source file path, size, modified
time, fingerprint, assumptions, or saved-result schema no longer match, EdgeLab labels the saved
result stale instead of treating it as current.

## Phase 7X-2G SPY/QQQ Comparative Pattern Study

Phase 7X-2G adds a local SPY/QQQ Pattern Study focused first on failed early moves. The technical
setup name is Opening Range Failure, but user-facing pages explain it as the first market move
failing to hold. The study checks current saved research runs for SPY and QQQ before comparing
detailed local replay outcomes.
If either saved result is missing or stale, EdgeLab shows a clear review state and asks for "Run
local analysis" instead of creating hidden saved results.

The comparison reviews possible examples, sit-out mornings, what happened afterward, setup
direction context, opening gap buckets, first-hour range-width buckets, data quality, and
first-hour completeness. These details stay under Evidence details in the UI.

The goal is to choose the next controlled research question, such as whether opening gap size or
first-hour range width explains a SPY/QQQ difference. The study does not optimize settings,
generate variants, enable paper mode, produce recommendations, or prove that any pattern works.
Real-money status remains Not allowed.

## Phase 7X-2H Controlled Variant Study

Phase 7X-2H adds a local controlled variant study for SPY's failed early move pattern. The variant
framework is pre-declared and reusable: SPY is the first instrument because current local evidence
points there, not because the framework is permanently SPY-only.

The active variants are the broad baseline, failed push from above, failed selloff from below,
failed quickly, failed later, and SPY/QQQ disagreement. Opening gap and range-width checks are
readiness checks, not optimized variants. If opening gap context is missing or range splits are too
thin, EdgeLab says so instead of forcing a conclusion.

This phase explicitly avoids parameter mining, best-setting searches, and tuning after seeing
results. A future experiment ledger and out-of-sample testing are required before broader variant
generation. The study does not save variant outputs, enable paper mode, create live signals, or
approve real-money use. Real-money status remains Not allowed.

## Phase 7X-2I Generic Out-of-Sample Gate

Phase 7X-2I adds a generic out-of-sample gate and first applies it to SPY's failed early move
variants. The current split is time-based: the discovery period runs from the earliest local SPY
session through the last local session before 2023 Q1, and the holdout-style period runs from the
first local SPY session on or after 2023-01-01 through the latest local session.

The gate requires current saved local SPY and QQQ research runs before it recomputes evidence from
ignored local FirstRate files. It does not auto-create saved runs on page load and does not save
gate results. The process-local cache key includes the symbols, paired symbol, pattern family,
variant IDs, split strategy and dates, replay assumptions, source-file signatures, and gate code
version.

This is a holdout-style check, not proof. Because the variants were identified after reviewing the
full available sample, the current result is a first honesty check rather than a pure untouched-data
confirmation. A stronger check requires additional historical data or future local data collected
after the rules are locked. The gate does not create recommendations, promote paper mode, create
live signals, or approve real-money use. Real-money status remains Not allowed.

## Phase 7X-2J AI-Assisted Strategy Discovery Sprint

Phase 7X-2J adds a local strategy discovery sprint that compares several simple intraday idea
families across the available ignored local historical files. The first fixed library is Failed
Early Move, Gap Fade, Gap Continuation, First 15-Minute Breakout, First 30-Minute Breakout,
Opening Range Reclaim, Strong Open / Weak Follow-Through, and SPY/QQQ Divergence.

The sprint is intentionally deterministic. It uses fixed local rules, a fixed later-period check,
and a process-local cache keyed by source-file signatures and assumptions. It does not save sprint
outputs, create saved research runs, call AI, call external APIs, fetch live data, use provider
SDKs, schedule work, or create processed output files.

The future AI idea intake is only a schema. A future AI helper may propose a locked hypothesis, but
EdgeLab must reject unsupported rule families, action language, after-the-fact threshold changes,
and chart-only ideas. Local deterministic code remains responsible for any accepted test. Real-money
status remains Not allowed.

## Phase 7X-2K Expanded Free FirstRate Universe

Phase 7X-2K expands the discovery sprint from the first SPY/QQQ sample pair to every matching
ignored FirstRate sample file available locally. General single-security strategy ideas run across
all discovered symbols. SPY/QQQ Divergence remains pair-specific unless a future phase adds a
generic pair-divergence framework.

The Intraday Research scoreboard remains strategy-first. It shows strategy idea, securities tested,
tests run, best current pattern candidate, current conclusion, status, and next research action. It
does not create pages per symbol or per test type.

The sprint reports local data quality by symbol, including file found, row count, date range,
session count, ready sessions, first-hour completeness, and quality issues. Local data problems are
reported as research evidence rather than hidden.

AI idea intake remains only a structured future-safe format. EdgeLab currently tests a fixed
library of deterministic local ideas across the expanded free universe. It does not call AI, fetch
live data, call vendors, save sprint outputs, create recommendations, promote paper mode, or approve
real-money use.

## Phase 7X-2L Structured AI Idea Batch Testing

Phase 7X-2L adds local structured idea batches. A batch is a set of locked hypothesis specs that
EdgeLab can validate before testing. The batch may be written by a person or proposed by an AI tool
outside EdgeLab, but EdgeLab does not call AI, connect to a live model, or ask AI to judge results.

Each idea must name a supported deterministic rule family, the securities to test, required local
data, fixed parameters, useful-result criteria, failure criteria, expected failure modes, and safety
notes. Unsupported rule families are separated instead of approximated. User-authored idea text is
not rejected based on wording.

Supported ideas run against the same ignored local FirstRate universe used by the discovery sprint.
Results use plain labels: Worth testing on more history, Mixed results / no clear answer, Needs
more examples, EdgeLab cannot test this idea with current local rules, Local data problem blocked
the test, and Reject for now. Batch results are computed on demand with process-local caching and
are not saved to the research-run DB in this phase. Current local data can show whether an idea
deserves another research pass, but it cannot prove a trade, approve paper mode, or approve
real-money use.

Phase 7X-2M makes that workflow usable inside EdgeLab. A user can paste a JSON idea batch into
`/ui/intraday-lab/research/idea-batches/new`, validate it, see accepted, rejected, unsupported, and
safety-error groups, then run supported ideas locally. The page shows the current schema and a
copyable example so the user does not have to guess the format. Pasted runs are temporary and are
not saved to the research-run DB. EdgeLab still does not call AI, call external APIs, fetch live
data, use credentials, or create recommendations.
