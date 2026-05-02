"""SQLite evidence collector for Evidentia (v0.7.7 P0.3).

Smaller surface than the other SQL adapters. SQLite has no built-in
user system, so the collector focuses on file-level + extension-
level evidence: journal mode + synchronous setting (durability
posture; SC-28 evidence), encryption-extension detection (SEE /
SQLCipher / WxSQLite3 — also SC-28), schema integrity (PRAGMA
integrity_check + PRAGMA foreign_key_check; SI-7), and OS-level
file ACLs of the database file (AC-3, with documented BLIND_SPOT
for distributed-fs scenarios).

Public surface::

    from evidentia_collectors.sql.sqlite import SQLiteCollector

    collector = SQLiteCollector(database_path="/var/lib/app/data.db")
    findings = collector.collect()

Or via context manager::

    with SQLiteCollector(database_path=...) as c:
        findings, manifest = c.collect_v2()

No password handling — SQLite has no auth. The collector still
runs a write-privilege probe (open in read-only mode + try a
pragma write) and emits EVIDENTIA-WRITE-PRIV-DETECTED if the
underlying file is writable, mapped to NIST AC-6.

Driver: stdlib ``sqlite3`` module — no optional extra needed.
The ``[sql-sqlite]`` extra is declared empty so users can pin
intent consistently with the other SQL adapters.
"""

from evidentia_collectors.sql.sqlite.collector import (
    BLIND_SPOTS,
    COLLECTOR_ID,
    SQLiteCollector,
    SQLiteCollectorError,
    SQLiteConnectionError,
    SQLiteQueryError,
)

__all__ = [
    "BLIND_SPOTS",
    "COLLECTOR_ID",
    "SQLiteCollector",
    "SQLiteCollectorError",
    "SQLiteConnectionError",
    "SQLiteQueryError",
]
