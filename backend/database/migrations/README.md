# Database Migrations

This folder contains SQL migration files for the `resume_builder` MySQL database.

## Files

- `001_initial_schema.sql`: Creates the initial schema:
  - `user`
  - `resume`
  - `occupations`
  - `technology_skills`

## Prerequisites

- MySQL 8+
- Database already created:

```sql
CREATE DATABASE IF NOT EXISTS resume_builder
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;
```

## Run Migration

From MySQL client:

```sql
USE resume_builder;
SOURCE C:/Users/Dell/Desktop/resume-builder/backend/database/migrations/001_initial_schema.sql;
```

## Notes

- The migration uses `CREATE TABLE IF NOT EXISTS`, so it is safe to re-run.
- `resume.user_id` has a foreign key to `user.id` with `ON DELETE CASCADE`.
- Default charset/collation for all tables: `utf8mb4` / `utf8mb4_general_ci`.
