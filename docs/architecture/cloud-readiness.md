# Cloud Readiness

EdgeLab is local-first now and cloud-ready later.

## Principles

- Avoid hardcoded machine-specific paths.
- Keep app configuration environment-driven.
- Keep storage access abstract enough to move from SQLite to Postgres later.
- Keep the API layer stateless where practical.
- Do not deploy to cloud in Phase 0.
- Do not add authentication yet unless needed later.

## Future Cloud Path

A future cloud version may include containerization, managed Postgres, background jobs, scheduled workers, and a hosted dashboard.
