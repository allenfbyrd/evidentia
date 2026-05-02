"""MS SQL Server evidence collector for Evidentia (v0.7.7 P0.4).

Read-only collector that surfaces compliance-relevant evidence from
a running MS SQL Server / Azure SQL Database / Azure SQL Managed
Instance and emits NIST-mapped SecurityFinding objects.

Public surface::

    from evidentia_collectors.sql.mssql import MSSQLCollector

    collector = MSSQLCollector(
        connection_uri="mssql://user@host:1433/dbname",
        password=os.environ["EVIDENTIA_MSSQL_PASSWORD"],
    )
    findings = collector.collect()

Or via context manager::

    with MSSQLCollector(connection_uri=..., password=...) as c:
        findings, manifest = c.collect_v2()

The connection URI MUST NOT embed a password — pass it explicitly
via the ``password`` kwarg, sourced from the
``EVIDENTIA_MSSQL_PASSWORD`` env var per the secret-handling
protocol. The constructor refuses to start if the URI's userinfo
contains a password.

Driver: ``pyodbc`` + Microsoft ODBC Driver 18 for SQL Server.
Install via the ``[sql-mssql]`` extra::

    pip install "evidentia-collectors[sql-mssql]"

You also need the OS-level driver. On Linux::

    curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
    sudo apt-get install -y msodbcsql18

On Windows the driver ships with SQL Server tooling or as a
standalone download from Microsoft.
"""

from evidentia_collectors.sql.mssql.collector import (
    BLIND_SPOTS,
    COLLECTOR_ID,
    MSSQLCollector,
    MSSQLCollectorError,
    MSSQLConnectionError,
    MSSQLQueryError,
)

__all__ = [
    "BLIND_SPOTS",
    "COLLECTOR_ID",
    "MSSQLCollector",
    "MSSQLCollectorError",
    "MSSQLConnectionError",
    "MSSQLQueryError",
]
