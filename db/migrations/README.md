# Database migrations

Alembic is the only schema-migration authority. Editorial seed data does not belong in
migrations. Production deployment runs `alembic upgrade head` as an explicit one-shot step
before starting the API.
