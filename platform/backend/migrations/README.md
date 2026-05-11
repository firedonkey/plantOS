# Database Migrations

Run migrations from the `platform/` directory:

```bash
alembic upgrade head
```

Alembic reads the database URL from the same environment variables as the app:

- `PLANTLAB_DATABASE_URL`
- `DATABASE_URL`
- or `DB_NAME`, `DB_USER`, `DB_PASSWORD`, and `CLOUD_SQL_CONNECTION_NAME`

Local development can keep using SQLite. Production should use PostgreSQL.
