"""Oracle Database evidence collector for Evidentia (v0.7.7 P0.5).

Read-only collector that surfaces compliance-relevant evidence
from Oracle Database 19c / 21c / 23c (or Database Free) and emits
NIST-mapped SecurityFinding objects.

Public surface::

    from evidentia_collectors.sql.oracle import OracleCollector

    collector = OracleCollector(
        connection_uri="oracle://user@host:1521/service_name",
        password=os.environ["EVIDENTIA_ORACLE_PASSWORD"],
    )
    findings = collector.collect()

Or via context manager::

    with OracleCollector(connection_uri=..., password=...) as c:
        findings, manifest = c.collect_v2()

The connection URI MUST NOT embed a password — pass it explicitly
via the ``password`` kwarg, sourced from the
``EVIDENTIA_ORACLE_PASSWORD`` env var per the secret-handling
protocol.

Driver: ``oracledb`` (Oracle's modern thin driver, pure Python —
no Oracle Client install required for the default thin mode).
Install via the ``[sql-oracle]`` extra::

    pip install "evidentia-collectors[sql-oracle]"

Required principal privilege: ``GRANT SELECT_CATALOG_ROLE TO
evidentia_reader;`` plus ``GRANT CREATE SESSION TO
evidentia_reader;``. The collector probes session privileges +
DBA-role membership to detect any write capability and emits an
EVIDENTIA-WRITE-PRIV-DETECTED finding (mapped to NIST AC-6) when
the principal exceeds read-only.
"""

from evidentia_collectors.sql.oracle.collector import (
    BLIND_SPOTS,
    COLLECTOR_ID,
    OracleCollector,
    OracleCollectorError,
    OracleConnectionError,
    OracleQueryError,
)

__all__ = [
    "BLIND_SPOTS",
    "COLLECTOR_ID",
    "OracleCollector",
    "OracleCollectorError",
    "OracleConnectionError",
    "OracleQueryError",
]
