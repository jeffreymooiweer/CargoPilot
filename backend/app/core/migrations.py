"""Schema changes that ``create_all`` cannot make.

``Base.metadata.create_all`` creates missing *tables* and never touches the
columns of one that already exists. That was fine while the settings tables
held one JSON document each and nothing else changed shape. The shipment
history is the first thing that wants real columns and will want more of
them — and a page that filters on a column that an older database lacks
breaks every upgrade with "no such column".

So this is the runner: a numbered list of steps, a ``schema_version`` table
that records which have been applied, and one rule for a fresh database.

**A fresh database is stamped, not migrated.** ``create_all`` has already
made every table in its current shape, so a step that adds a column would
find it there and fail. On a database that had no tables at all before
start-up, every step is recorded as applied without running. On any other
database the pending steps run in order, each in its own transaction, and
are recorded as they succeed — so a step that fails halfway leaves the
version where it was and the next start tries again.

**Every step is written to be safe to run twice.** ``add_column`` checks the
column is absent first, and table creation uses ``checkfirst``. That is not
what the version table is for — it is what makes the version table
recoverable when somebody restores a backup taken between two steps.

Steps live here rather than in files per version because there are few of
them and one file is easier to read in order. If that stops being true the
list is the thing to split, not the mechanism.
"""
from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, inspect, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)

_meta = MetaData()
schema_version = Table(
    "schema_version", _meta,
    Column("version", Integer, primary_key=True),
    Column("name", String(120), nullable=False),
    Column("applied_at", DateTime(timezone=True), server_default=func.now()),
)


def column_exists(conn: Connection, table: str, column: str) -> bool:
    inspector = inspect(conn)
    if not inspector.has_table(table):
        return False
    return any(c["name"] == column for c in inspector.get_columns(table))


def add_column(conn: Connection, table: str, definition: str) -> bool:
    """``ALTER TABLE … ADD COLUMN`` when the column is absent.

    ``definition`` is the column as SQL, ``"department_id INTEGER"``; the
    name is its first word. Returns whether anything was done.
    """
    name = definition.split()[0]
    if column_exists(conn, table, name):
        return False
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {definition}"))
    return True


# --- the steps ---------------------------------------------------------------


def _001_shipments(conn: Connection) -> None:
    """The shipment history's table. ``create_all`` makes it on a fresh
    database; this makes it on one that predates v1.173.0."""
    from app.models.shipment import Shipment

    Shipment.__table__.create(conn, checkfirst=True)


def _002_departments(conn: Connection) -> None:
    """Departments (v1.174.0): the table, and the column on users and on
    shipments that says whose work is whose. Both nullable — a user or a
    shipment without a department is the ordinary case."""
    from app.models.user import Department

    Department.__table__.create(conn, checkfirst=True)
    add_column(conn, "users", "department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL")
    add_column(conn, "shipments", "department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL")
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_shipments_department_id ON shipments (department_id)"))


#: In order. Append; never renumber, never remove.
MIGRATIONS: list[tuple[int, str, Callable[[Connection], None]]] = [
    (1, "shipments", _001_shipments),
    (2, "departments", _002_departments),
]


# --- the runner --------------------------------------------------------------


def applied(conn: Connection) -> set[int]:
    if not inspect(conn).has_table(schema_version.name):
        return set()
    rows = conn.execute(text(f"SELECT version FROM {schema_version.name}")).fetchall()
    return {int(row[0]) for row in rows}


def run(engine: Engine, fresh: bool) -> list[int]:
    """Apply the pending steps, or stamp them on a fresh database.

    Returns the versions recorded by this call.
    """
    schema_version.create(engine, checkfirst=True)
    recorded: list[int] = []
    for version, name, step in MIGRATIONS:
        with engine.begin() as conn:
            if version in applied(conn):
                continue
            if fresh:
                logger.info("Schema step %s (%s): stamped, fresh database", version, name)
            else:
                step(conn)
                logger.info("Schema step %s (%s): applied", version, name)
            conn.execute(schema_version.insert().values(version=version, name=name))
        recorded.append(version)
    return recorded


def current(engine: Engine) -> int:
    with engine.connect() as conn:
        done = applied(conn)
    return max(done) if done else 0
