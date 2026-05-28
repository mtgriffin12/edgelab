# Backtesting Principles

- No look-ahead bias.
- No survivorship bias when avoidable.
- Account for fees, slippage, liquidity, spread, and execution delay.
- Separate in-sample and out-of-sample periods.
- Prefer walk-forward validation over one static backtest.
- Penalize strategies dependent on fragile parameters.
- Compare results before and after costs.
- Record assumptions for every test.

## Phase 4 Fixture Approach

Phase 4 uses synthetic local market-data fixtures and existing sample strategy specifications only.
The backtesting engine is deterministic, auditable, and intended for research evidence rather than
execution.

The initial engine supports a deliberately small placeholder rule: evaluate whether the current
close is above the prior close, then simulate entry on the next available bar according to explicit
execution assumptions. This keeps the implementation point-in-time oriented and avoids look-ahead
bias while the broader strategy language is still maturing.

Backtest output includes simulated fills, closed simulated positions, equity curve records,
execution assumptions, quality issues, and summary metrics. It does not create real orders or
trade instructions.

Real market-data providers, broker integrations, paper execution, live execution, charts, scheduled
jobs, and cloud deployment remain out of scope.
