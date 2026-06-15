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

## Phase 7X Intraday Fixture Approach

Phase 7X adds local synthetic one-minute intraday fixtures. These fixtures include session labels,
opening benchmark inputs, first-hour bars, source labels, and ingestion timestamps. The fixture
provider lists symbols and sessions dynamically from CSV files so the system is not hard-wired to
S&P 500-style or Nasdaq-style examples.

Intraday fixtures are for workflow validation only. They are not historical market evidence, not
live quotes, and not enough for paper or real-money decisions.

## Phase 7X-2A Historical Intraday CSV Import

Phase 7X-2A adds a local historical intraday CSV import foundation before replay mode or vendor
integrations. The canonical CSV format records symbol, raw timestamp, source timezone, interval,
OHLCV values, session type, session ID, provider label, dataset ID, and adjustment mode. Optional
instrument fields can provide display name, point value, tick size, tick value, venue, and regular
session hours.

Imported timestamps are normalized to UTC while preserving the raw timestamp and source timezone.
Adjustment mode is explicit so unadjusted, adjusted, split-adjusted, and unknown data cannot be
mixed silently. The provider reports quality issues for missing columns, blank values, invalid
timestamps, invalid OHLC rows, duplicate bars, unsorted bars, unsupported intervals, and ambiguous
adjustment metadata.

Tiny synthetic historical fixtures may be committed for tests. Real downloaded historical files
must stay outside source control under ignored local directories such as `data/raw/` or
`data/processed/`.

## Phase 7X-2B Historical Intraday Replay

Phase 7X-2B reuses the local historical CSV import foundation and adds replay state derived from
one session at a time. At each replay step, the engine may only use bars with timestamps at or
before the replay clock. Setup detection receives only visible bars, hypothetical entry uses the
next available bar after the signal bar, and hypothetical exit is recorded only after the exit bar
is visible.

Replay output stores the number of bars visible, the latest visible timestamp, decisions, quality
issues, and plain-English explanations. It does not add multi-session statistics, live watch mode,
external data calls, paid providers, broker execution, or real-money readiness.

## Phase 7X-2C Multi-Session Historical Replay Summaries

Phase 7X-2C derives aggregate summaries from local replay results. It does not create a new data
source. Each session still comes from local CSV-backed historical fixtures, and each replay keeps
the Phase 7X-2B point-in-time visibility rules.

Aggregate fields include sessions found, sessions tested, usable sessions, data-skipped sessions,
setup counts, sit-out counts, pretend result buckets, cost-changed-conclusion flags, setup-family
summaries, sit-out reason summaries, and evidence-detail counts. These outputs are research-only
views over local fixtures and are not proof, live data, provider data, or real-money readiness.

## Phase 7X-2D FirstRate Local CSV Dry Run

Phase 7X-2D adds a FirstRate normalizer for ignored local files under
`data/raw/historical_intraday/firstratedata/`. The normalizer reads FirstRate's
`timestamp,open,high,low,close,volume` format and maps each row into EdgeLab's canonical historical
intraday structure with explicit metadata.

The dry-run path is read-only. It does not write normalized output files, commit real downloaded
data, call external providers, use credentials, or fetch live quotes. Local FirstRate files remain
outside source control, while tiny synthetic FirstRate-style rows in tests cover parser behavior.
FirstRate rows from 16:00:01 through 20:00:00 Eastern are treated as after-hours context, not as
per-row quality issues, so replay readiness stays focused on clean regular first-hour coverage.

## Phase 7X-2E FirstRate Replay Integration

Phase 7X-2E keeps FirstRate files local and ignored, then passes normalized SPY and QQQ sessions
into the existing historical replay and multi-session summary workflow. The integration uses a
read-only in-memory bridge so one request can reuse normalized bars without writing processed files
or creating a background job.

Each FirstRate session now receives first-hour completeness details: expected first-hour timestamps,
actual first-hour bars, missing timestamps, duplicate timestamps, and a plain completeness label.
The check exists because missing first-hour minutes can make a replay story look cleaner than the
local data allows.

This phase does not commit downloaded data, call external providers, use credentials, fetch live
quotes, add paid provider SDKs, create charts, or connect to brokers. Results are research-only and
real-money status remains Not allowed.

## Phase 7X-2F Saved Research Runs

Phase 7X-2F adds a local SQLite saved-run store at
`data/processed/research_runs/edgelab_research_runs.db`. The path is ignored and is only for local
research review. Saved runs contain compact summaries, source-file metadata, assumptions, quality
warnings, and plain-English sections; they do not copy FirstRate CSV rows into the database.

Freshness checks compare the saved source path, file size, modified time, fingerprint,
assumptions, and schema version against the current ignored local file. A changed source file or
saved-result format marks the result as stale and asks for review before relying on it as research.

## Phase 7X-2G Comparative Study Data Use

Phase 7X-2G reads saved-run freshness and recomputes detailed comparison evidence from ignored
local FirstRate files when both SPY and QQQ saved runs are current. Comparative output is not stored
in a new database in this phase. It is cached only in the running Python process using the symbols,
setup family, date range, replay assumptions, code version, and source-file path, size, and modified
time.

No raw FirstRate rows, saved research database files, or processed outputs are committed. The study
does not call external APIs or fetch live data.

## Phase 7X-2H Controlled Variant Study Data Use

Phase 7X-2H uses current saved-run freshness as a source-file gate, then recomputes controlled
variant evidence from ignored local FirstRate files. SPY is the first instrument; QQQ is read only
for the SPY/QQQ disagreement variant. Variant-study results are not saved to SQLite or written to
processed files. Repeat detail-page loads use process-local cache keyed by source-file signatures,
symbols, replay assumptions, variant spec version, and code version.

No real downloaded data, ignored saved-run database files, or processed outputs are committed. The
study does not call external APIs, fetch live data, add provider SDKs, or create recommendations.
