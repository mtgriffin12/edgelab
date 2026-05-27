# EdgeLab Agent Guide

EdgeLab is a trading research and validation system, not a live trading bot.

- Never implement live order execution unless explicitly instructed in a future task.
- Never store credentials or secrets.
- Use `.env.example` only for placeholder environment variable names.
- Treat sentiment as timestamped data, not model opinion.
- Prevent look-ahead bias in all backtesting logic.
- Risk controls must be deterministic and able to veto any strategy signal.
- Add or update tests for meaningful behavior changes.
- Update relevant docs when architecture, risk rules, schemas, or assumptions change.
- Prefer simple, testable modules over clever abstractions.
- Run tests before reporting completion.
- Do not overbuild.
