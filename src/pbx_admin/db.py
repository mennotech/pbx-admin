"""SQLite access helpers and database lifecycle wiring."""

import os
import sqlite3

import click
from flask import current_app, g


def get_db() -> sqlite3.Connection:
    """Return a per-request SQLite connection stored on the app context."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["SQLITE_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app) -> None:
    """Create the schema (and optionally seed data) for ``app``."""
    path = app.config["SQLITE_PATH"]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        with open(app.config["SCHEMA_PATH"], "r", encoding="utf-8") as fh:
            conn.executescript(fh.read())
        if app.config.get("DB_AUTO_SEED"):
            with open(app.config["SEED_PATH"], "r", encoding="utf-8") as fh:
                conn.executescript(fh.read())
        conn.commit()
    finally:
        conn.close()


@click.command("init-db")
def init_db_command() -> None:
    """flask CLI command: initialize the database."""
    init_db(current_app)
    click.echo("Initialized the database.")


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
