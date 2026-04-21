# CrucibAI Backend Tests

## Running tests without PostgreSQL (SQLite fallback)

Set `CRUCIB_TEST_SQLITE=1` to run the test suite using an in-process document
store instead of a live PostgreSQL connection. This is useful in CI environments
or local dev setups where the Postgres container is not running.

```bash
CRUCIB_TEST_SQLITE=1 pytest tests/test_api_contract.py
```

Example — run just the health-check contract:

```bash
CRUCIB_TEST_SQLITE=1 pytest tests/test_api_contract.py::TestHealthContract::test_health_status_200 -q
```

When `CRUCIB_TEST_SQLITE=1`:
- The `app_client` fixture uses an in-process `_FakeDb` document store.
- Docker / asyncpg startup is skipped entirely.
- All 11 tests in `test_api_contract.py` are green.
- Tests decorated with `@pytest.mark.postgres_only` are skipped automatically.

## Postgres-only tests

Some tests exercise PostgreSQL-specific features (JSONB operators, ARRAY types,
window functions, etc.) and are marked with `@pytest.mark.postgres_only`. They
are skipped automatically when `CRUCIB_TEST_SQLITE=1` is set.

## Default (PostgreSQL) mode

Default behavior is unchanged. Start the local Postgres instance and run:

```bash
docker compose up -d postgres redis
pytest tests/
```

The Postgres container must be reachable at `127.0.0.1:5434`
(matches `docker-compose.yml` defaults).
