# Model Portfolio Engine

The Model Portfolio Engine builds hypothetical research portfolios from fixture-backed candidates.
It is a bridge from candidate screening toward future paper portfolio testing, not a
recommendation system.

## Purpose

Phase 7B tests portfolio construction logic:

- starting capital,
- explicit cash allocation,
- target holding weights,
- position reasons,
- concentration checks,
- exposure limits,
- monitoring notes,
- plain-English explanations.

The engine uses only local fixture candidates and in-memory model construction.

## User-Facing Concept: Pretend Portfolio Tests

The UI calls this feature Pretend Portfolio Tests. The simple idea is:

- EdgeLab is practicing how it might build portfolios later.
- The data is sample data built into the app.
- The portfolios are not recommendations.
- The page should explain what EdgeLab is testing before showing numbers.
- Real-money status is always Not allowed.

This wording is intentional. The user should not need portfolio theory vocabulary to understand
whether EdgeLab is interested, cautious, or blocked.

## Not A Recommendation

Pretend portfolio tests are not instructions or recommendations. They do not use live quotes,
connect to brokers, create orders, run autonomous paper workflows, or approve real-money use.
Fixture data cannot support real-money decisions.

## Holding Discipline

Every model holding needs:

- why it appears,
- what supports it,
- what is missing,
- what would make EdgeLab reconsider,
- real-money status.

If a holding cannot explain its role, it should not appear in a model portfolio.

## Cash Is Intentional

Cash is the part EdgeLab leaves safely unused because the evidence is not strong enough yet. It
protects the model from pretending weak evidence deserves full participation. Cash/no-action
remains a valid research conclusion when evidence is thin.

## Why Constraints Matter

Position size must be constrained by risk rules, not only by candidate score. Concentration,
minimum cash, total exposure, and maximum holding count should be checked deterministically.

## Future Path

This phase prepares EdgeLab for later work:

- future portfolio action queue,
- paper portfolio simulation,
- human-approved paper workflow,
- eventual live-trading gatekeeper.

Those future steps remain disabled until explicitly built and approved.

Before paper portfolio simulation exists, EdgeLab would need real historical data, explicit paper
mode rules, review gates, safety rules, and proof that the UI still says what is missing before it
shows any paper-mode output.
