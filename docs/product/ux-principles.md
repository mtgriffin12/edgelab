# UX Principles

EdgeLab should not look or behave like a traditional trading platform.

## Philosophy

- Decision lab, not trading terminal.
- Evidence before action.
- Strategy cards, not noisy watchlists.
- Research pipeline, not price-chasing.
- Plain-English explanations before structured metrics.
- Text and tables first.
- No charts in Phase 0.
- Progressive disclosure: show the conclusion first, then evidence, then audit trail.
- Every strategy should have a "why it exists," "why it might fail," and "what evidence supports it."
- Cash/no-trade should be treated as a valid system recommendation.
- The interface should make restraint feel intelligent, not inactive.
- Decision intelligence matters more than traditional finance dashboards.
- Any user-facing page that a college student with no investing experience cannot understand has failed.

## Initial UX Surfaces

- Lab Bench: strategy ideas and structured strategy specs.
- Evidence Board: backtest results, robustness results, and rejection reasons.
- Sentiment Lens: current and historical sentiment context.
- Risk Sentinel: vetoes, drawdown state, exposure limits, and warnings.
- Paper Desk: simulated trades and open paper positions.
- Journal: audit log of signals, decisions, rejected trades, and lessons.
- Reports: Markdown/CSV summaries.

## Phase 5A Local UX Shell

Phase 5A adds a server-rendered local browser cockpit over the existing FastAPI app. The UI is
intentionally text/table first and uses only current local capabilities: sample strategy specs,
synthetic market-data fixtures, synthetic sentiment fixtures, deterministic risk posture, and the
fixture-backed sample backtest.

The initial pages are:

- Cockpit: project state, safety state, known fixtures, and module links.
- Lab Bench: strategy inventory, status, eligibility, and strategy-card links.
- Evidence Board: sample backtest summaries with research-only limitations first.
- Sentiment Lens: descriptive sentiment snapshots from fixture events.
- Risk Sentinel: no-live-trading posture and deterministic veto principles.
- Journal: audit-style project phase summary.
- Reports: text/table summaries of strategies, fixtures, and sample evidence.

The shell does not add charts, trade buttons, authentication, cloud deployment, external APIs,
broker integrations, or execution behavior. Unsupported strategies should remain visibly
unsupported rather than appearing validated.

## Phase 5B Plain-English UX

Phase 5B adds a durable plain-English language layer for research results and safety state. The UI
should use the doctrine in `docs/product/plain-english-ux-language.md`: conclusions before metrics,
plain English before technical terms, direct warnings, and conservative real-money language.

Metric labels should explain what the user needs to know before showing technical terminology. For
example, use "Historical Test" before "backtest," "Worst Drop" before "drawdown," "Gain/Loss Ratio"
before "profit factor," and "Market Mood" before "sentiment."

## Phase 5C Discovery Lab UX

The Strategy Discovery Lab should make idea status plain. Known ideas and novel ideas are both
allowed, but neither should feel trusted without evidence. The page should show the simpler
baseline each idea must beat and make it clear that no idea is ready for real money.

## Phase 6 Ranking UX

The Strategy Rankings page should feel like research triage, not a leaderboard. It should explain
the bottom line before the score, show what helped and hurt, and make weak evidence easy to see.
High return should not visually dominate warnings about worst drop, small sample size, unsupported
logic, or missing baseline evidence.

## Phase 7A Candidate Screener UX

The Candidate Equity Screener should feel like a research intake desk, not a watchlist to act on.
It should explain why a symbol appeared, what evidence is missing, what would change the system's
mind, and why real-money use remains blocked. Candidate tables should make sample-data limits and
reasons to be careful as visible as scores.

## Phase 7B Model Portfolio UX

The portfolio UI should say "Pretend Portfolio Tests" before model portfolio. It should feel like
decision intelligence practice, not a portfolio-theory dashboard. Every portfolio page should show
the bottom line, what EdgeLab is testing, what EdgeLab would do in research mode, why each holding
appears, why cash is included, what is missing, what would change EdgeLab's mind, the next review
item, and real-money status before technical details.

Technical terms such as allocation, equity exposure, benchmark, target weight, target value,
constraint, evidence strength, and diversification belong in an Evidence details section, where
they must be translated into beginner language. Cash should feel like intentional restraint, and
every page should make clear that practice portfolios are not recommendations.
