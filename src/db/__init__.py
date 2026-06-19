"""Database abstraction layer.

Exports:
  - database.get_engine() — Create DB engine (SQLite or Postgres)
  - database.SessionLocal — SQLAlchemy session factory
  - database.init_db() — Initialize database schema
  - models.Base — SQLAlchemy declarative base
"""
