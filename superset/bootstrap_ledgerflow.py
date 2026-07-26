from __future__ import annotations

import os

from superset import app, db
from superset.models.core import Database

DATABASE_NAME = "LedgerFlow DuckDB"
SQLALCHEMY_URI = os.environ.get(
    "LEDGERFLOW_DUCKDB_URI",
    "duckdb:////app/ledgerflow-data/database/superset.duckdb",
)

with app.app_context():
    database = db.session.query(Database).filter(Database.database_name == DATABASE_NAME).one_or_none()
    if database is None:
        database = Database(database_name=DATABASE_NAME)
        db.session.add(database)
    database.sqlalchemy_uri = SQLALCHEMY_URI
    database.expose_in_sqllab = True
    database.allow_ctas = False
    database.allow_cvas = False
    database.allow_dml = False
    database.extra = '{"metadata_params": {}, "engine_params": {"connect_args": {"read_only": true}}}'
    db.session.commit()
    print(f"LedgerFlow Superset database ready: {DATABASE_NAME} -> {SQLALCHEMY_URI}")
