"""How every SQLite connection is set up.

For every engine in the process: WAL lets the web threads read while the
worker writes; busy_timeout makes a writer wait for the lock instead of
failing at once; SQLite leaves foreign keys off unless asked.
"""

from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine


def init_app(app: Flask) -> None:
    # Once per process, however many apps it makes: the listeners are global.
    if not event.contains(Engine, "connect", _sqlite_pragmas):
        event.listen(Engine, "connect", _sqlite_pragmas)
        event.listen(Engine, "begin", _sqlite_begin)


def _sqlite_pragmas(dbapi_conn, _record):
    if type(dbapi_conn).__module__.startswith("sqlite3"):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
        # The sqlite3 driver starts transactions its own way, which breaks
        # SAVEPOINT: releasing one would commit it. With the driver's handling
        # off, SQLAlchemy begins each transaction itself (below), and
        # db.session.begin_nested() rolls back as it should.
        dbapi_conn.isolation_level = None


def _sqlite_begin(conn):
    if conn.dialect.name == "sqlite":
        conn.exec_driver_sql("BEGIN")
