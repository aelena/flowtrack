# Contributing

FlowTrack is a personal tool published in the open, not a product looking for maintainers. That shapes what is useful to send.

## What is welcome

**Bug reports**, especially anything that loses data or silently does nothing. The most valuable issue anyone has filed against this codebase would have been *"the Unarchive button does not unarchive"* — it was visible, it looked right, and it called the wrong endpoint for months.

**Small fixes** with a test. If it touches the API, add the test first; the suite is fast and there is no excuse.

**Portability reports.** This is developed on Windows against Docker Desktop and has had exactly one user. If the quick start fails on your machine, that is a real bug and I want to know.

## What is probably not welcome

**Features that make it less opinionated.** No Gantt charts, no sprints, no story points, no burndown. The absence of those is the product. `abandonment_criteria` and the two competing completion figures are the point, and anything that softens them is going the wrong way.

**Large refactors** arriving unannounced. Open an issue first — not for ceremony, but because the direction may already be decided and I would rather not waste your evening.

## Running it

See the [README](README.md). Short version:

```bash
cp .env.example .env
docker compose up --build
```

## Before you open a PR

```bash
# Backend
docker compose exec api ruff check .
docker compose exec api ruff format --check .
docker compose exec db psql -U flowtrack -d postgres -c 'CREATE DATABASE flowtrack_test;'
docker compose exec -e TEST_DATABASE_URL=postgresql+asyncpg://flowtrack:flowtrack_secret@db:5432/flowtrack_test \
  api python -m pytest -q

# Frontend
cd frontend && npm ci && npm run lint && npm run build
```

CI runs all of that plus a full `docker compose up --wait` smoke test, so anything green locally should be green there.

**The test suite drops every table.** It defaults to a `flowtrack_test` database and refuses to run against anything whose name does not end in `_test`. Do not disable that guard; it exists because the README once instructed people to point the suite at their real data.

## Changing the schema

Migrations are Alembic, applied automatically on API startup. After editing a model:

```bash
docker compose exec api alembic revision --autogenerate -m "what changed"
```

Read what it generated before committing it — autogenerate is a good first draft and a poor final one, particularly around enum types and server defaults.

Note that the test suite still builds its schema with `create_all` rather than by running migrations. That is faster, and both come from the same metadata, but it does mean a migration can be wrong in a way the tests will not catch. Worth knowing before you trust a green run.

## Style

Ruff decides Python formatting, Prettier decides the frontend. Neither is up for debate — run them and move on.

Commit messages: explain **why**, not what. The diff already says what.

## Licence

Contributions are accepted under the [MIT licence](LICENSE).
