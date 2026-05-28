# UX Principles

EdgeLab should not look or behave like a traditional trading platform.

## Philosophy

- Decision lab, not trading terminal.
- Evidence before action.
- Strategy cards, not noisy watchlists.
- Research pipeline, not price-chasing.
- Plain-English explanations paired with structured metrics.
- Text and tables first.
- No charts in Phase 0.
- Progressive disclosure: show the conclusion first, then evidence, then audit trail.
- Every strategy should have a "why it exists," "why it might fail," and "what evidence supports it."
- Cash/no-trade should be treated as a valid system recommendation.
- The interface should make restraint feel intelligent, not inactive.

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
