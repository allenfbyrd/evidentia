"""Snowflake evidence collector for Evidentia (v0.7.8 P0.2).

Read-only collector that surfaces compliance-relevant evidence from a
Snowflake account: login history (AC-7, AU-2), user + grant inventory
(AC-2, AC-3, AC-6), masking + row-access policy inventory
(AC-3, SC-28), MFA enforcement (IA-2), network policies (SC-7), and
operator-attested key-rotation status (SC-12).

Public surface::

    from evidentia_collectors.snowflake import SnowflakeCollector

    collector = SnowflakeCollector(
        account="acme-prod",
        user="EVIDENTIA_AUDIT_RO",
        # Password sourced from SNOWFLAKE_PASSWORD env var; pass
        # ``password=...`` explicitly only when bypassing the CLI's
        # env-var injection layer.
    )
    findings, manifest = collector.collect_v2()

Or via context manager (recommended; releases the connection cleanly)::

    with SnowflakeCollector(account="...", user="...") as c:
        findings, manifest = c.collect_v2()

Credentials per `~/.claude/CLAUDE.md` secret-handling protocol:

- The collector NEVER takes a plaintext password in code at the CLI
  surface. The CLI surface (``evidentia collect snowflake``) reads
  the password from the env var named via ``--password-env`` (default
  ``SNOWFLAKE_PASSWORD``) and forwards it to the constructor.
- Programmatic callers pass ``password=os.environ[...]`` themselves;
  never embed the secret in code.
- Production deployments SHOULD use **key-pair authentication**
  rather than passwords. Snowflake is deprecating password auth.
  The collector accepts a ``private_key_path`` kwarg as a forward-
  compatible alternative — set the public key via
  ``ALTER USER <user> SET RSA_PUBLIC_KEY = '<base64>'``.

Required principal privileges:

- ``USAGE`` on the ``SNOWFLAKE`` shared database (the database
  Snowflake automatically provides for ``account_usage`` +
  ``information_schema`` views — typically all roles have this).
- ``IMPORTED PRIVILEGES`` on ``SNOWFLAKE`` (granted to ACCOUNTADMIN
  by default; consider granting to a dedicated audit role).
- ``MONITOR USAGE`` on the account (or ACCOUNTADMIN role) — required
  for ``account_usage`` views to return data instead of empty
  result sets.
- For ``INFORMATION_SCHEMA`` policy queries: ``USAGE`` on each
  database whose policies the collector should inventory; the
  collector iterates over every database the principal can see.

The recommended hardened setup is::

    -- Run as ACCOUNTADMIN once at onboarding:
    USE ROLE ACCOUNTADMIN;
    CREATE ROLE EVIDENTIA_AUDIT_RO;
    GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE
        TO ROLE EVIDENTIA_AUDIT_RO;
    GRANT MONITOR USAGE ON ACCOUNT TO ROLE EVIDENTIA_AUDIT_RO;
    CREATE USER EVIDENTIA_AUDIT_RO
        PASSWORD = '<env-supplied>'
        DEFAULT_ROLE = EVIDENTIA_AUDIT_RO
        DEFAULT_WAREHOUSE = EVIDENTIA_AUDIT_WH;

Driver: ``snowflake-connector-python>=3.10``. Install via the
``[snowflake]`` extra::

    pip install "evidentia-collectors[snowflake]"

Auth modes supported (per the snowflake-connector-python driver):

- Password (``password=`` kwarg sourced from env var by CLI)
- Key-pair (``private_key_path=`` kwarg; preferred for prod)
- OAuth (``token=`` kwarg with externally-issued OAuth token)
- SSO (``authenticator='externalbrowser'``; interactive only —
  not recommended for unattended collection)

The collector does NOT support MFA-prompt auth (interactive flow)
— it's designed for unattended scheduled collection.

Note on `account_usage` view latency: Snowflake's `account_usage`
shared database has a documented data-latency window of up to 45
minutes for most views and up to 3 hours for some (LOGIN_HISTORY +
ACCESS_HISTORY in particular). This means the collector observes a
sliding window of recent-but-not-real-time evidence; for incident-
response use, supplement with `INFORMATION_SCHEMA` views
(real-time but only the last 7 days).
"""

from evidentia_collectors.snowflake.collector import (
    BLIND_SPOTS,
    COLLECTOR_ID,
    SnowflakeAuthError,
    SnowflakeCollector,
    SnowflakeCollectorError,
    SnowflakePermissionError,
    SnowflakeQueryError,
)

__all__ = [
    "BLIND_SPOTS",
    "COLLECTOR_ID",
    "SnowflakeAuthError",
    "SnowflakeCollector",
    "SnowflakeCollectorError",
    "SnowflakePermissionError",
    "SnowflakeQueryError",
]
