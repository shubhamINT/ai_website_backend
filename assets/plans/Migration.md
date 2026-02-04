# Database Migrations with Alembic

Alembic has been set up to manage database schema migrations for this project. It is configured to work with asynchronous drivers and auto-discovers models defined in `src/core/database.py`.

## Core Commands

### 1. Create a new migration

Run this whenever you change your database models:

```bash
uv run alembic revision --autogenerate -m "Description of your changes"
```

### 2. Apply migrations

Run this to update your database to the latest schema:

```bash
uv run alembic upgrade head
```

### 3. Check migration status

```bash
uv run alembic current
```

### 4. Rollback last migration

```bash
uv run alembic downgrade -1
```

---

_Note: Ensure your `.env` file has the correct `DATABASE_URL` before running migrations._
