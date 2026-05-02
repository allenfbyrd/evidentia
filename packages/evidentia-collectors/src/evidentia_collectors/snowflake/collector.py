"""Snowflake evidence collector — main module (v0.7.8 P0.2).

Read-only collector that surfaces compliance-relevant evidence from a
Snowflake account and emits NIST-mapped SecurityFinding objects for
each observation.

See ``evidentia_collectors.snowflake.__init__`` for the public-surface
walkthrough + credential handling protocol.

Mirrors the v0.7.0 enterprise-grade collector pattern:

- Typed exception hierarchy (``SnowflakeCollectorError`` /
  ``SnowflakeAuthError`` / ``SnowflakePermissionError`` /
  ``SnowflakeQueryError``)
- ``CollectionContext`` threaded through every emitted finding
- ``CollectionManifest`` returned by ``collect_v2()`` for completeness
  attestation
- ECS-structured audit logging via
  ``evidentia_core.audit.get_logger("evidentia.collectors.snowflake")``
- Connection-test probe on first connect
- Explicit ``BLIND_SPOTS`` list documenting coverage gaps
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from evidentia_core.audit import (
    CollectionContext,
    CollectionManifest,
    CoverageCount,
    EventAction,
    EventOutcome,
    get_logger,
    new_run_id,
)
from evidentia_core.models.common import (
    Severity,
    current_version,
    utc_now,
)
from evidentia_core.models.finding import FindingStatus, SecurityFinding

from evidentia_collectors.snowflake.mapping import (
    GRANT_ACCOUNTADMIN_MAPPINGS,
    GRANT_INVENTORY_MAPPINGS,
    KEY_ROTATION_OPERATOR_FACT_MAPPINGS,
    LOGIN_FAILED_MAPPINGS,
    LOGIN_INVENTORY_MAPPINGS,
    MASKING_POLICY_INVENTORY_MAPPINGS,
    MFA_DISABLED_MAPPINGS,
    NETWORK_POLICY_INVENTORY_MAPPINGS,
    NETWORK_POLICY_NONE_ASSIGNED_MAPPINGS,
    ROW_ACCESS_POLICY_INVENTORY_MAPPINGS,
    USER_DISABLED_MAPPINGS,
    USER_INVENTORY_MAPPINGS,
    USER_NEVER_LOGGED_IN_MAPPINGS,
)

if TYPE_CHECKING:
    # Type-only import; snowflake-connector-python is in the
    # [snowflake] optional extra. The runtime import is lazy in
    # _ensure_connected so the package itself loads without the
    # driver installed.
    import snowflake.connector  # noqa: F401


_log = get_logger("evidentia.collectors.snowflake")

COLLECTOR_ID = "snowflake-scan"


# ── Typed exception hierarchy ──────────────────────────────────────


class SnowflakeCollectorError(Exception):
    """Base class for all Snowflake collector failures."""


class SnowflakeAuthError(SnowflakeCollectorError):
    """Authentication / SSO / key-pair handshake failure."""


class SnowflakePermissionError(SnowflakeCollectorError):
    """Principal lacks required privileges (e.g. IMPORTED PRIVILEGES
    on SNOWFLAKE database, or MONITOR USAGE on account)."""


class SnowflakeQueryError(SnowflakeCollectorError):
    """A specific SQL query failed (permission denied, missing view,
    malformed). The collector continues with remaining queries; this
    error is recorded in the manifest's ``errors`` list."""


# ── BLIND_SPOTS list ───────────────────────────────────────────────


BLIND_SPOTS: list[dict[str, str]] = [
    {
        "id": "EVIDENTIA-SNOWFLAKE-ACCOUNT-USAGE-LATENCY",
        "title": "account_usage views have up to 3-hour latency",
        "description": (
            "Snowflake's `account_usage` shared database (the source "
            "of LOGIN_HISTORY, USERS, GRANTS_TO_USERS, "
            "GRANTS_TO_ROLES, ACCESS_HISTORY, etc.) has a documented "
            "data-freshness window of up to 45 minutes for most "
            "views and up to 3 hours for LOGIN_HISTORY + "
            "ACCESS_HISTORY. The collector observes recent-but-not-"
            "real-time evidence. For incident-response scenarios "
            "requiring real-time data, supplement with "
            "INFORMATION_SCHEMA equivalents (real-time but limited "
            "to last 7 days)."
        ),
    },
    {
        "id": "EVIDENTIA-SNOWFLAKE-PRIVATE-PREVIEW-FEATURES",
        "title": "Private-preview features not surfaced",
        "description": (
            "Snowflake routinely ships private-preview + private-"
            "GA features (early-stage masking-policy variants, new "
            "RBAC mechanisms, account-replication settings) that "
            "are not exposed through `account_usage` until they "
            "reach public GA. The collector inventories the GA "
            "surface only; preview features are operator-attested."
        ),
    },
    {
        "id": "EVIDENTIA-SNOWFLAKE-CROSS-ACCOUNT-REPLICATION",
        "title": "Cross-account replication targets not enumerated",
        "description": (
            "Snowflake account replication (database replication, "
            "secure-data-sharing, listings) can move data across "
            "accounts. The collector inventories the source "
            "account's local objects; downstream replication "
            "targets must be inventoried by running the collector "
            "against each target account separately."
        ),
    },
    {
        "id": "EVIDENTIA-SNOWFLAKE-INFORMATION-SCHEMA-PER-DB",
        "title": "INFORMATION_SCHEMA views are per-database",
        "description": (
            "INFORMATION_SCHEMA.MASKING_POLICIES, "
            "INFORMATION_SCHEMA.ROW_ACCESS_POLICIES, and "
            "INFORMATION_SCHEMA.NETWORK_POLICIES are per-database "
            "views (only the current database's policies are "
            "listed). The collector iterates over every database "
            "the principal has USAGE on; databases the principal "
            "cannot see are SILENTLY EXCLUDED. For complete coverage "
            "the audit principal must have USAGE on every database."
        ),
    },
    {
        "id": "EVIDENTIA-SNOWFLAKE-PASSWORD-AUTH-DEPRECATION",
        "title": "Password authentication is being deprecated",
        "description": (
            "Snowflake announced deprecation of password authentication "
            "for new users (effective late 2025). Existing users with "
            "password auth still work, but production deployments should "
            "migrate to key-pair authentication. The collector supports "
            "password auth for current-state inventory; new audit "
            "principals SHOULD use key-pair (`private_key_path` kwarg) "
            "to future-proof unattended collection."
        ),
    },
    {
        "id": "EVIDENTIA-SNOWFLAKE-ENCRYPTION-PLATFORM-MANAGED",
        "title": "Account-level encryption keys are platform-managed",
        "description": (
            "Snowflake encrypts all data at rest with platform-managed "
            "AES-256 keys; key rotation is automatic and not exposed "
            "via SQL. For Tri-Secret Secure (BYOK) accounts, the "
            "customer-managed key cadence is operator-controlled but "
            "still not queryable from inside Snowflake. The collector "
            "ingests operator-attested rotation cadence as a manifest-"
            "level fact rather than a per-finding observation."
        ),
    },
    {
        "id": "EVIDENTIA-SNOWFLAKE-LEGACY-ACCOUNT-LOGIN-HISTORY",
        "title": "LOGIN_HISTORY scope window depends on edition",
        "description": (
            "LOGIN_HISTORY retains 365 days for Enterprise+ accounts, "
            "but Standard edition retains a shorter window. The "
            "collector defaults to the last 90 days (industry "
            "standard); operators on Standard edition with shorter "
            "retention may see truncated coverage relative to the "
            "default window."
        ),
    },
]


# ── Constants ──────────────────────────────────────────────────────


# 90 days is the industry-standard window for AC-7 (login history)
# evidence + matches FedRAMP CONMON cadence + matches Snowflake's
# default LOGIN_HISTORY filter widget.
_LOGIN_HISTORY_DEFAULT_WINDOW_DAYS = 90


# Snowflake's reserved built-in role names. Inventoried separately
# from custom roles because grant-to-built-in-role is structurally
# different (e.g. ACCOUNTADMIN can never be revoked from itself).
_BUILT_IN_ROLES = frozenset(
    {
        "ACCOUNTADMIN",
        "SECURITYADMIN",
        "USERADMIN",
        "SYSADMIN",
        "PUBLIC",
        "ORGADMIN",
    }
)


# Roles that should be inventoried with extra scrutiny — these carry
# privileged-account semantics per AC-2(7).
_PRIVILEGED_ROLES = frozenset(
    {
        "ACCOUNTADMIN",
        "SECURITYADMIN",
        "ORGADMIN",
    }
)


# ── Collector ──────────────────────────────────────────────────────


class SnowflakeCollector:
    """Snowflake evidence collector.

    Connects to a Snowflake account, queries `account_usage` +
    `INFORMATION_SCHEMA` views, and emits SecurityFinding objects
    mapped to NIST 800-53 controls.

    Args:
        account: Snowflake account locator (e.g. ``"acme-prod"`` or
            ``"acme-prod.us-east-1"``). The driver appends
            ``.snowflakecomputing.com`` automatically.
        user: Snowflake username for the audit principal.
        password: Optional plaintext password. NEVER pass this from
            the CLI surface; the CLI sources it from the env var
            named via ``--password-env``. Programmatic callers may
            pass ``password=os.environ["SNOWFLAKE_PASSWORD"]``.
        private_key_path: Optional path to a PEM-encoded RSA private
            key for key-pair auth. Preferred over password for
            production deployments.
        warehouse: Optional warehouse name. If omitted, the driver
            uses the user's default warehouse. Audit principals
            should have a dedicated low-cost warehouse.
        role: Optional role name. If omitted, the driver uses the
            user's default role.
        login_history_window_days: How many days back to scan in
            LOGIN_HISTORY. Defaults to 90.

    Raises:
        SnowflakeCollectorError: if `snowflake-connector-python` is
            not installed (install via the [snowflake] extra).
    """

    def __init__(
        self,
        *,
        account: str,
        user: str,
        password: str | None = None,
        private_key_path: str | None = None,
        warehouse: str | None = None,
        role: str | None = None,
        login_history_window_days: int = _LOGIN_HISTORY_DEFAULT_WINDOW_DAYS,
    ) -> None:
        self._account = account
        self._user = user
        self._password = password
        self._private_key_path = private_key_path
        self._warehouse = warehouse
        self._role = role
        self._login_history_window_days = login_history_window_days
        self._connection: Any | None = None
        self._cached_account_id: str | None = None
        self._cached_role: str | None = None
        self._cached_version: str | None = None

    # ── Lifecycle ───────────────────────────────────────────────────

    def __enter__(self) -> SnowflakeCollector:
        self._ensure_connected()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._connection is not None:
            with contextlib.suppress(Exception):
                self._connection.close()
            self._connection = None

    def _ensure_connected(self) -> Any:
        """Lazy-connect on first use. Returns the connection object."""
        if self._connection is not None:
            return self._connection
        try:
            import snowflake.connector
        except ImportError as e:
            raise SnowflakeCollectorError(
                "snowflake-connector-python is not installed. "
                "Install via the [snowflake] extra: "
                'pip install "evidentia-collectors[snowflake]"'
            ) from e

        kwargs: dict[str, Any] = {
            "account": self._account,
            "user": self._user,
        }
        if self._password is not None:
            kwargs["password"] = self._password
        if self._private_key_path is not None:
            kwargs["private_key_file"] = self._private_key_path
        if self._warehouse is not None:
            kwargs["warehouse"] = self._warehouse
        if self._role is not None:
            kwargs["role"] = self._role
        try:
            self._connection = snowflake.connector.connect(**kwargs)
        except Exception as e:
            raise SnowflakeAuthError(
                f"Could not connect to Snowflake "
                f"(driver: {type(e).__name__})"
            ) from e
        return self._connection

    # ── Context + provenance ────────────────────────────────────────

    def test_connection(self) -> dict[str, Any]:
        """Probe the connection + cache account / role / version.

        Returns a dict with ``account``, ``user``, ``role``,
        ``version`` (Snowflake server version), and ``warehouse``.
        """
        conn = self._ensure_connected()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT CURRENT_ACCOUNT(), CURRENT_USER(), "
                "CURRENT_ROLE(), CURRENT_VERSION(), "
                "CURRENT_WAREHOUSE()"
            )
            row = cur.fetchone()
            self._cached_account_id = str(row[0]) if row else None
            self._cached_role = str(row[2]) if row else None
            self._cached_version = str(row[3]) if row else None
            return {
                "account": self._cached_account_id,
                "user": str(row[1]) if row else None,
                "role": self._cached_role,
                "version": self._cached_version,
                "warehouse": str(row[4]) if row and row[4] else None,
            }
        finally:
            cur.close()

    def _build_context(self, run_id: str) -> CollectionContext:
        account = self._cached_account_id or self._account
        role = self._cached_role or self._role or "unknown"
        return CollectionContext(
            collector_id=COLLECTOR_ID,
            collector_version=current_version(),
            run_id=run_id,
            credential_identity=f"snowflake-user:{self._user}",
            source_system_id=f"snowflake:{account}",
            filter_applied={
                "account": account,
                "user": self._user,
                "role": role,
                "login_history_window_days": (
                    self._login_history_window_days
                ),
            },
        )

    # ── Sub-checks ──────────────────────────────────────────────────

    def _login_history_findings(
        self, context: CollectionContext
    ) -> tuple[list[SecurityFinding], CoverageCount]:
        """LOGIN_HISTORY inventory + failed-login surfacing.

        Emits one inventory-summary finding per principal + one
        finding per failed-login row. The inventory finding is
        RESOLVED + INFORMATIONAL (it's evidence-of-collection,
        not a gap); failed-login rows are ACTIVE + LOW (they're
        the substrate for AC-7 enforcement review, not a violation
        on their own).
        """
        conn = self._ensure_connected()
        cur = conn.cursor()
        findings: list[SecurityFinding] = []
        scanned = 0
        try:
            window_start = datetime.now(UTC) - timedelta(
                days=self._login_history_window_days
            )
            cur.execute(
                """
                SELECT
                    USER_NAME,
                    EVENT_TIMESTAMP,
                    CLIENT_IP,
                    REPORTED_CLIENT_TYPE,
                    REPORTED_CLIENT_VERSION,
                    FIRST_AUTHENTICATION_FACTOR,
                    SECOND_AUTHENTICATION_FACTOR,
                    IS_SUCCESS,
                    ERROR_CODE,
                    ERROR_MESSAGE
                FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
                WHERE EVENT_TIMESTAMP >= %s
                ORDER BY EVENT_TIMESTAMP DESC
                """,
                (window_start,),
            )
            rows = cur.fetchall()
            scanned = len(rows)
            successful_by_user: dict[str, int] = {}
            failures_by_user: dict[str, list[Any]] = {}
            for row in rows:
                user_name = str(row[0]) if row[0] else "unknown"
                is_success = bool(row[7])
                if is_success:
                    successful_by_user[user_name] = (
                        successful_by_user.get(user_name, 0) + 1
                    )
                else:
                    failures_by_user.setdefault(user_name, []).append(row)

            # One inventory-summary finding per user observed in window.
            seen_users = set(successful_by_user) | set(failures_by_user)
            for user_name in sorted(seen_users):
                successes = successful_by_user.get(user_name, 0)
                failures = len(failures_by_user.get(user_name, []))
                findings.append(
                    SecurityFinding(
                        title=(
                            f"Login activity inventoried for user "
                            f"{user_name}"
                        ),
                        description=(
                            f"Observed {successes} successful + "
                            f"{failures} failed login(s) for user "
                            f"{user_name} over the last "
                            f"{self._login_history_window_days} "
                            f"days. AU-2 evidence captured; AC-7 "
                            f"enforcement gating is operator-driven."
                        ),
                        severity=Severity.INFORMATIONAL,
                        status=FindingStatus.RESOLVED,
                        source_system="snowflake",
                        source_finding_id=(
                            f"login-history-inventory:{user_name}"
                        ),
                        resource_type="snowflake-user",
                        resource_id=user_name,
                        collection_context=context,
                        control_mappings=LOGIN_INVENTORY_MAPPINGS,
                    )
                )

            # One finding per failed-login row over the window — bounded
            # by Snowflake's row return + the window param. Operators
            # can shrink the window if the volume is impractical for
            # finding-by-finding emission.
            for user_name, fails in failures_by_user.items():
                for row in fails:
                    event_ts = row[1]
                    client_ip = str(row[2]) if row[2] else "unknown"
                    error_code = str(row[8]) if row[8] else "unknown"
                    error_message = str(row[9]) if row[9] else ""
                    findings.append(
                        SecurityFinding(
                            title=(
                                f"Failed Snowflake login for "
                                f"{user_name} from {client_ip}"
                            ),
                            description=(
                                f"User {user_name} failed to "
                                f"authenticate from {client_ip} "
                                f"at {event_ts}. Error code "
                                f"{error_code}: {error_message}. "
                                f"Evidence for AC-7 unsuccessful-"
                                f"logon-attempts review; clusters "
                                f"of failures are an IR-4 incident-"
                                f"handling trigger."
                            ),
                            severity=Severity.LOW,
                            status=FindingStatus.ACTIVE,
                            source_system="snowflake",
                            source_finding_id=(
                                f"login-failed:{user_name}:"
                                f"{event_ts.isoformat() if hasattr(event_ts, 'isoformat') else event_ts}"
                                f":{client_ip}"
                            ),
                            resource_type="snowflake-user",
                            resource_id=user_name,
                            collection_context=context,
                            control_mappings=LOGIN_FAILED_MAPPINGS,
                        )
                    )
        except Exception as e:
            _log.warning(
                action=EventAction.COLLECT_FAILED,
                outcome=EventOutcome.FAILURE,
                message=f"snowflake login_history query failed: {e!r}",
                error={"type": type(e).__name__, "message": str(e)},
            )
            raise SnowflakeQueryError(
                f"LOGIN_HISTORY query failed: {type(e).__name__}"
            ) from e
        finally:
            cur.close()

        return findings, CoverageCount(
            resource_type="snowflake-login-history-row",
            scanned=scanned,
            matched_filter=scanned,
            collected=len(findings),
        )

    def _user_inventory_findings(
        self, context: CollectionContext
    ) -> tuple[list[SecurityFinding], CoverageCount]:
        """USERS inventory + per-user MFA + disabled + never-logged-in.

        Emits one inventory finding per user (RESOLVED + INFORMATIONAL),
        one MFA-disabled finding per user with HAS_MFA = FALSE
        (ACTIVE + MEDIUM), one disabled-account finding per user with
        DISABLED = TRUE (ACTIVE + LOW), and one never-logged-in
        finding per user with no LAST_SUCCESS_LOGIN (ACTIVE + LOW).
        """
        conn = self._ensure_connected()
        cur = conn.cursor()
        findings: list[SecurityFinding] = []
        scanned = 0
        try:
            cur.execute(
                """
                SELECT
                    NAME,
                    LOGIN_NAME,
                    DISPLAY_NAME,
                    EMAIL,
                    DISABLED,
                    HAS_MFA,
                    HAS_PASSWORD,
                    HAS_RSA_PUBLIC_KEY,
                    DEFAULT_ROLE,
                    LAST_SUCCESS_LOGIN,
                    PASSWORD_LAST_SET_TIME
                FROM SNOWFLAKE.ACCOUNT_USAGE.USERS
                WHERE DELETED_ON IS NULL
                """,
            )
            rows = cur.fetchall()
            scanned = len(rows)
            for row in rows:
                user_name = str(row[0]) if row[0] else "unknown"
                disabled = bool(row[4])
                has_mfa = bool(row[5])
                has_password = bool(row[6])
                has_rsa = bool(row[7])
                default_role = str(row[8]) if row[8] else None
                last_login = row[9]

                # Inventory finding (always emitted).
                findings.append(
                    SecurityFinding(
                        title=(
                            f"Snowflake user {user_name} inventoried"
                        ),
                        description=(
                            f"User {user_name} present in "
                            f"account_usage.USERS. "
                            f"Default role: {default_role or 'none'}. "
                            f"MFA enabled: {has_mfa}. "
                            f"Password set: {has_password}. "
                            f"RSA public key set: {has_rsa}. "
                            f"Disabled: {disabled}. "
                            f"AC-2 inventory evidence."
                        ),
                        severity=Severity.INFORMATIONAL,
                        status=FindingStatus.RESOLVED,
                        source_system="snowflake",
                        source_finding_id=f"user-inventory:{user_name}",
                        resource_type="snowflake-user",
                        resource_id=user_name,
                        collection_context=context,
                        control_mappings=USER_INVENTORY_MAPPINGS,
                    )
                )

                # MFA-disabled finding (ACTIVE + MEDIUM) — but only
                # for users with password auth. Key-pair auth bypasses
                # the IA-2(1) MFA requirement when the key is
                # adequately protected.
                if has_password and not has_mfa:
                    findings.append(
                        SecurityFinding(
                            title=(
                                f"Snowflake user {user_name} has no "
                                f"MFA enrolled"
                            ),
                            description=(
                                f"User {user_name} has password auth "
                                f"enabled (HAS_PASSWORD=TRUE) but no "
                                f"MFA enrolled (HAS_MFA=FALSE). "
                                f"For FedRAMP Moderate + financial-"
                                f"services environments, MFA is "
                                f"required for all interactive "
                                f"authentication. Remediation: "
                                f"`ALTER USER {user_name} SET "
                                f"MUST_CHANGE_PASSWORD = TRUE` + "
                                f"MFA enrollment workflow, OR "
                                f"migrate the user to key-pair auth "
                                f"and revoke the password."
                            ),
                            severity=Severity.MEDIUM,
                            status=FindingStatus.ACTIVE,
                            source_system="snowflake",
                            source_finding_id=f"mfa-disabled:{user_name}",
                            resource_type="snowflake-user",
                            resource_id=user_name,
                            collection_context=context,
                            control_mappings=MFA_DISABLED_MAPPINGS,
                        )
                    )

                # Disabled account finding (informational reminder
                # to confirm the disable was authorized + grants
                # cleaned up).
                if disabled:
                    findings.append(
                        SecurityFinding(
                            title=(
                                f"Snowflake user {user_name} is "
                                f"disabled"
                            ),
                            description=(
                                f"User {user_name} is marked "
                                f"DISABLED=TRUE in "
                                f"account_usage.USERS. "
                                f"Confirm the disable was authorized "
                                f"+ all grants have been revoked per "
                                f"AC-2(3) Disable Inactive Accounts. "
                                f"Disabled accounts that retain "
                                f"grants are an attack surface if "
                                f"the disable flag can be flipped "
                                f"without re-running the "
                                f"authorization workflow."
                            ),
                            severity=Severity.LOW,
                            status=FindingStatus.ACTIVE,
                            source_system="snowflake",
                            source_finding_id=(
                                f"user-disabled:{user_name}"
                            ),
                            resource_type="snowflake-user",
                            resource_id=user_name,
                            collection_context=context,
                            control_mappings=USER_DISABLED_MAPPINGS,
                        )
                    )

                # Never-logged-in finding (only for non-disabled users).
                if last_login is None and not disabled:
                    findings.append(
                        SecurityFinding(
                            title=(
                                f"Snowflake user {user_name} has "
                                f"never logged in"
                            ),
                            description=(
                                f"User {user_name} has no recorded "
                                f"successful login in "
                                f"account_usage.USERS.LAST_SUCCESS_LOGIN. "
                                f"May indicate an unused account "
                                f"that should be either documented "
                                f"as a service-only account "
                                f"(programmatic-only, no interactive "
                                f"login expected) or disabled per "
                                f"AC-2(3)."
                            ),
                            severity=Severity.LOW,
                            status=FindingStatus.ACTIVE,
                            source_system="snowflake",
                            source_finding_id=(
                                f"user-never-logged-in:{user_name}"
                            ),
                            resource_type="snowflake-user",
                            resource_id=user_name,
                            collection_context=context,
                            control_mappings=(
                                USER_NEVER_LOGGED_IN_MAPPINGS
                            ),
                        )
                    )
        except Exception as e:
            _log.warning(
                action=EventAction.COLLECT_FAILED,
                outcome=EventOutcome.FAILURE,
                message=f"snowflake users query failed: {e!r}",
                error={"type": type(e).__name__, "message": str(e)},
            )
            raise SnowflakeQueryError(
                f"USERS query failed: {type(e).__name__}"
            ) from e
        finally:
            cur.close()

        return findings, CoverageCount(
            resource_type="snowflake-user",
            scanned=scanned,
            matched_filter=scanned,
            collected=len(findings),
        )

    def _grant_inventory_findings(
        self, context: CollectionContext
    ) -> tuple[list[SecurityFinding], CoverageCount]:
        """GRANTS inventory — focus on privileged-role grants.

        Emits one inventory-summary finding per grantee and one
        ACTIVE finding per ACCOUNTADMIN/SECURITYADMIN/ORGADMIN grant
        (AC-6(7) review trigger). Other grants are inventoried via
        the summary; the auditor reviews the manifest's
        `coverage_counts` to see total grant volume.
        """
        conn = self._ensure_connected()
        cur = conn.cursor()
        findings: list[SecurityFinding] = []
        scanned = 0
        try:
            cur.execute(
                """
                SELECT
                    GRANTEE_NAME,
                    ROLE,
                    GRANTED_TO,
                    GRANTED_BY,
                    CREATED_ON
                FROM SNOWFLAKE.ACCOUNT_USAGE.GRANTS_TO_USERS
                WHERE DELETED_ON IS NULL
                """,
            )
            rows = cur.fetchall()
            scanned = len(rows)
            grants_by_user: dict[str, list[str]] = {}
            for row in rows:
                grantee = str(row[0]) if row[0] else "unknown"
                role = str(row[1]) if row[1] else "unknown"
                grants_by_user.setdefault(grantee, []).append(role)

            for grantee, role_list in sorted(grants_by_user.items()):
                # Inventory-summary finding.
                privileged = sorted(
                    {
                        r
                        for r in role_list
                        if r.upper() in _PRIVILEGED_ROLES
                    }
                )
                privileged_note = (
                    f" (privileged roles: {', '.join(privileged)})"
                    if privileged
                    else ""
                )
                findings.append(
                    SecurityFinding(
                        title=(
                            f"Snowflake grants inventoried for "
                            f"{grantee}"
                        ),
                        description=(
                            f"User {grantee} has {len(role_list)} "
                            f"role grant(s)"
                            f"{privileged_note}. AC-3 + AC-6 "
                            f"inventory evidence."
                        ),
                        severity=Severity.INFORMATIONAL,
                        status=FindingStatus.RESOLVED,
                        source_system="snowflake",
                        source_finding_id=(
                            f"grant-inventory:{grantee}"
                        ),
                        resource_type="snowflake-user",
                        resource_id=grantee,
                        collection_context=context,
                        control_mappings=GRANT_INVENTORY_MAPPINGS,
                    )
                )

                # One finding per privileged-role grant.
                for role in privileged:
                    findings.append(
                        SecurityFinding(
                            title=(
                                f"Privileged-role grant: "
                                f"{grantee} → {role}"
                            ),
                            description=(
                                f"User {grantee} holds the "
                                f"privileged role {role}. "
                                f"This grant should appear on the "
                                f"periodic least-privilege review "
                                f"per AC-6(7). Confirm the grant "
                                f"is appropriate to the user's "
                                f"current role assignment."
                            ),
                            severity=Severity.MEDIUM,
                            status=FindingStatus.ACTIVE,
                            source_system="snowflake",
                            source_finding_id=(
                                f"privileged-grant:{grantee}:{role}"
                            ),
                            resource_type="snowflake-grant",
                            resource_id=f"{grantee}:{role}",
                            collection_context=context,
                            control_mappings=(
                                GRANT_ACCOUNTADMIN_MAPPINGS
                            ),
                        )
                    )
        except Exception as e:
            _log.warning(
                action=EventAction.COLLECT_FAILED,
                outcome=EventOutcome.FAILURE,
                message=f"snowflake grants query failed: {e!r}",
                error={"type": type(e).__name__, "message": str(e)},
            )
            raise SnowflakeQueryError(
                f"GRANTS_TO_USERS query failed: {type(e).__name__}"
            ) from e
        finally:
            cur.close()

        return findings, CoverageCount(
            resource_type="snowflake-grant",
            scanned=scanned,
            matched_filter=scanned,
            collected=len(findings),
        )

    def _network_policy_findings(
        self, context: CollectionContext
    ) -> tuple[list[SecurityFinding], CoverageCount]:
        """Network-policy inventory at the account level.

        Uses SHOW NETWORK POLICIES (account-level). Emits one
        inventory finding per policy and a single ACTIVE finding
        if no account-level policy is in effect (SC-7 baseline gap).
        """
        conn = self._ensure_connected()
        cur = conn.cursor()
        findings: list[SecurityFinding] = []
        scanned = 0
        try:
            cur.execute("SHOW NETWORK POLICIES")
            rows = cur.fetchall()
            scanned = len(rows)

            # Inventory finding per policy.
            for row in rows:
                # SHOW NETWORK POLICIES columns: created_on, name,
                # comment, entries_in_allowed_ip_list,
                # entries_in_blocked_ip_list, owner.
                policy_name = (
                    str(row[1]) if len(row) > 1 and row[1] else "unknown"
                )
                allowed_count = (
                    int(row[3]) if len(row) > 3 and row[3] is not None else 0
                )
                blocked_count = (
                    int(row[4]) if len(row) > 4 and row[4] is not None else 0
                )
                findings.append(
                    SecurityFinding(
                        title=(
                            f"Snowflake network policy {policy_name} "
                            f"inventoried"
                        ),
                        description=(
                            f"Network policy {policy_name} present "
                            f"in account. "
                            f"Allowed IPs: {allowed_count}. "
                            f"Blocked IPs: {blocked_count}. "
                            f"SC-7 boundary-protection evidence."
                        ),
                        severity=Severity.INFORMATIONAL,
                        status=FindingStatus.RESOLVED,
                        source_system="snowflake",
                        source_finding_id=(
                            f"network-policy-inventory:{policy_name}"
                        ),
                        resource_type="snowflake-network-policy",
                        resource_id=policy_name,
                        collection_context=context,
                        control_mappings=(
                            NETWORK_POLICY_INVENTORY_MAPPINGS
                        ),
                    )
                )

            # Probe whether an account-level policy is set.
            try:
                cur.execute(
                    "SHOW PARAMETERS LIKE 'NETWORK_POLICY' "
                    "IN ACCOUNT"
                )
                param_rows = cur.fetchall()
                account_policy: str | None = None
                for prow in param_rows:
                    # SHOW PARAMETERS columns: key, value, default,
                    # level, description, type.
                    if (
                        len(prow) > 1
                        and prow[0]
                        and str(prow[0]).upper() == "NETWORK_POLICY"
                    ):
                        val = str(prow[1]) if prow[1] else ""
                        account_policy = val if val else None
                        break

                if not account_policy:
                    findings.append(
                        SecurityFinding(
                            title=(
                                "No account-level Snowflake "
                                "network policy in effect"
                            ),
                            description=(
                                "The Snowflake account has no "
                                "NETWORK_POLICY parameter set. "
                                "Authentication attempts can "
                                "originate from any IP that can "
                                "reach Snowflake's public "
                                "endpoints. For FedRAMP + "
                                "financial-services environments, "
                                "an account-level policy is the "
                                "baseline expectation. Remediation: "
                                "`ALTER ACCOUNT SET NETWORK_POLICY "
                                "= '<policy_name>'`."
                            ),
                            severity=Severity.MEDIUM,
                            status=FindingStatus.ACTIVE,
                            source_system="snowflake",
                            source_finding_id=(
                                "network-policy-none-assigned"
                            ),
                            resource_type="snowflake-account",
                            resource_id=(
                                self._cached_account_id
                                or self._account
                            ),
                            collection_context=context,
                            control_mappings=(
                                NETWORK_POLICY_NONE_ASSIGNED_MAPPINGS
                            ),
                        )
                    )
            except Exception as e:
                # Permission-related — record + continue.
                _log.info(
                    action=EventAction.COLLECT_STARTED,
                    outcome=EventOutcome.UNKNOWN,
                    message=(
                        f"snowflake account-level network policy "
                        f"probe skipped: {e!r}"
                    ),
                    error={"type": type(e).__name__, "message": str(e)},
                )
        except Exception as e:
            _log.warning(
                action=EventAction.COLLECT_FAILED,
                outcome=EventOutcome.FAILURE,
                message=f"snowflake network policy query failed: {e!r}",
                error={"type": type(e).__name__, "message": str(e)},
            )
            raise SnowflakeQueryError(
                f"SHOW NETWORK POLICIES failed: {type(e).__name__}"
            ) from e
        finally:
            cur.close()

        return findings, CoverageCount(
            resource_type="snowflake-network-policy",
            scanned=scanned,
            matched_filter=scanned,
            collected=len(findings),
        )

    def _policy_inventory_findings(
        self, context: CollectionContext
    ) -> tuple[list[SecurityFinding], CoverageCount]:
        """Masking + row-access policy inventory across all DBs.

        Iterates over every database the principal can see (per
        SHOW DATABASES) and queries each database's
        INFORMATION_SCHEMA for masking + row-access policies.
        """
        conn = self._ensure_connected()
        cur = conn.cursor()
        findings: list[SecurityFinding] = []
        scanned = 0
        try:
            cur.execute("SHOW DATABASES")
            db_rows = cur.fetchall()
            db_names: list[str] = []
            for row in db_rows:
                # SHOW DATABASES columns: created_on, name, ...
                if len(row) > 1 and row[1]:
                    db_names.append(str(row[1]))

            for db in db_names:
                # Masking policies.
                try:
                    cur.execute(
                        f'SELECT POLICY_NAME, POLICY_SCHEMA, '
                        f'POLICY_OWNER FROM '
                        f'"{db}".INFORMATION_SCHEMA.MASKING_POLICIES'
                    )
                    pol_rows = cur.fetchall()
                    scanned += len(pol_rows)
                    for prow in pol_rows:
                        policy_name = (
                            str(prow[0]) if prow[0] else "unknown"
                        )
                        policy_schema = (
                            str(prow[1]) if prow[1] else "unknown"
                        )
                        fqn = f"{db}.{policy_schema}.{policy_name}"
                        findings.append(
                            SecurityFinding(
                                title=(
                                    f"Masking policy {fqn} "
                                    f"inventoried"
                                ),
                                description=(
                                    f"Masking policy {fqn} present "
                                    f"in database {db}. AC-3 + "
                                    f"SC-28 evidence; operator "
                                    f"confirms policy logic matches "
                                    f"the data-classification regime."
                                ),
                                severity=Severity.INFORMATIONAL,
                                status=FindingStatus.RESOLVED,
                                source_system="snowflake",
                                source_finding_id=(
                                    f"masking-policy:{fqn}"
                                ),
                                resource_type=(
                                    "snowflake-masking-policy"
                                ),
                                resource_id=fqn,
                                collection_context=context,
                                control_mappings=(
                                    MASKING_POLICY_INVENTORY_MAPPINGS
                                ),
                            )
                        )
                except Exception as e:
                    _log.info(
                        action=EventAction.COLLECT_STARTED,
                        outcome=EventOutcome.UNKNOWN,
                        message=(
                            f"snowflake masking policy query for db "
                            f"{db!r} failed (likely permission): {e!r}"
                        ),
                        error={
                            "type": type(e).__name__,
                            "message": str(e),
                        },
                    )

                # Row-access policies.
                try:
                    cur.execute(
                        f'SELECT POLICY_NAME, POLICY_SCHEMA, '
                        f'POLICY_OWNER FROM '
                        f'"{db}".INFORMATION_SCHEMA.ROW_ACCESS_POLICIES'
                    )
                    pol_rows = cur.fetchall()
                    scanned += len(pol_rows)
                    for prow in pol_rows:
                        policy_name = (
                            str(prow[0]) if prow[0] else "unknown"
                        )
                        policy_schema = (
                            str(prow[1]) if prow[1] else "unknown"
                        )
                        fqn = f"{db}.{policy_schema}.{policy_name}"
                        findings.append(
                            SecurityFinding(
                                title=(
                                    f"Row-access policy {fqn} "
                                    f"inventoried"
                                ),
                                description=(
                                    f"Row-access policy {fqn} "
                                    f"present in database {db}. "
                                    f"AC-3 + AC-3(7) RBAC "
                                    f"enforcement evidence; "
                                    f"operator reviews policy "
                                    f"logic + role bindings."
                                ),
                                severity=Severity.INFORMATIONAL,
                                status=FindingStatus.RESOLVED,
                                source_system="snowflake",
                                source_finding_id=(
                                    f"row-access-policy:{fqn}"
                                ),
                                resource_type=(
                                    "snowflake-row-access-policy"
                                ),
                                resource_id=fqn,
                                collection_context=context,
                                control_mappings=(
                                    ROW_ACCESS_POLICY_INVENTORY_MAPPINGS
                                ),
                            )
                        )
                except Exception as e:
                    _log.info(
                        action=EventAction.COLLECT_STARTED,
                        outcome=EventOutcome.UNKNOWN,
                        message=(
                            f"snowflake row-access policy query for "
                            f"db {db!r} failed (likely permission): "
                            f"{e!r}"
                        ),
                        error={
                            "type": type(e).__name__,
                            "message": str(e),
                        },
                    )
        except Exception as e:
            _log.warning(
                action=EventAction.COLLECT_FAILED,
                outcome=EventOutcome.FAILURE,
                message=f"snowflake policy inventory query failed: {e!r}",
                error={"type": type(e).__name__, "message": str(e)},
            )
            raise SnowflakeQueryError(
                f"Policy inventory query failed: {type(e).__name__}"
            ) from e
        finally:
            cur.close()

        return findings, CoverageCount(
            resource_type="snowflake-policy",
            scanned=scanned,
            matched_filter=scanned,
            collected=len(findings),
        )

    def _key_rotation_findings(
        self, context: CollectionContext
    ) -> tuple[list[SecurityFinding], CoverageCount]:
        """Operator-attested key-rotation status (single inventory finding).

        Snowflake's account-level encryption keys are platform-managed
        and not directly queryable. This sub-check emits a single
        RESOLVED finding documenting the platform-managed default
        cadence; Tri-Secret Secure / customer-managed-key cadence is
        operator-attested and lives in the manifest's `warnings` list.
        """
        findings = [
            SecurityFinding(
                title=(
                    "Snowflake account encryption keys "
                    "platform-managed"
                ),
                description=(
                    "Snowflake encrypts all data at rest with "
                    "platform-managed AES-256 keys. Per Snowflake's "
                    "documented behavior, automatic key rotation "
                    "occurs at least every 30 days for account-"
                    "level keys. For Tri-Secret Secure (BYOK) "
                    "accounts, the customer-managed key cadence is "
                    "operator-controlled. SC-12 evidence (platform-"
                    "managed default); operator attestation required "
                    "for BYOK cadence."
                ),
                severity=Severity.INFORMATIONAL,
                status=FindingStatus.RESOLVED,
                source_system="snowflake",
                source_finding_id="key-rotation-platform-managed",
                resource_type="snowflake-account",
                resource_id=(
                    self._cached_account_id or self._account
                ),
                collection_context=context,
                control_mappings=(
                    KEY_ROTATION_OPERATOR_FACT_MAPPINGS
                ),
            )
        ]
        return findings, CoverageCount(
            resource_type="snowflake-encryption-key",
            scanned=1,
            matched_filter=1,
            collected=len(findings),
        )

    # ── Public collect API ──────────────────────────────────────────

    def collect(self) -> list[SecurityFinding]:
        """Run all sub-checks and return findings only.

        Backward-compat surface for v0.6.x callers; new callers
        should prefer :meth:`collect_v2` to also receive the
        manifest.
        """
        findings, _manifest = self.collect_v2()
        return findings

    def collect_v2(
        self,
    ) -> tuple[list[SecurityFinding], CollectionManifest]:
        """Run all sub-checks and return (findings, manifest).

        Manifest captures coverage counts per sub-check, errors
        encountered (per-sub-check, non-fatal), and overall
        completeness. is_complete=False if ANY sub-check raised
        SnowflakeQueryError.
        """
        run_id = new_run_id()
        started = utc_now()
        context = self._build_context(run_id)
        # Account is now cached if test_connection was called; if not,
        # call it once so manifest's source_system_ids is populated.
        if self._cached_account_id is None:
            with contextlib.suppress(SnowflakeCollectorError):
                self.test_connection()
            context = self._build_context(run_id)

        all_findings: list[SecurityFinding] = []
        all_coverage: list[CoverageCount] = []
        empty_categories: list[str] = []
        errors: list[str] = []
        warnings: list[str] = [
            "BLIND_SPOT: account_usage views have up to 3-hour "
            "latency; supplement with INFORMATION_SCHEMA for "
            "real-time evidence.",
        ]

        sub_checks: list[
            tuple[
                str,
                Any,  # method
                str,  # category-name for empty_categories
            ]
        ] = [
            (
                "login_history",
                self._login_history_findings,
                "snowflake-login-history-row",
            ),
            (
                "users",
                self._user_inventory_findings,
                "snowflake-user",
            ),
            (
                "grants",
                self._grant_inventory_findings,
                "snowflake-grant",
            ),
            (
                "network_policies",
                self._network_policy_findings,
                "snowflake-network-policy",
            ),
            (
                "policies",
                self._policy_inventory_findings,
                "snowflake-policy",
            ),
            (
                "key_rotation",
                self._key_rotation_findings,
                "snowflake-encryption-key",
            ),
        ]

        is_complete = True
        for name, method, category in sub_checks:
            try:
                sub_findings, coverage = method(context)
            except SnowflakeQueryError as e:
                is_complete = False
                errors.append(f"{name}: {e}")
                continue
            except Exception as e:
                is_complete = False
                errors.append(
                    f"{name}: unexpected {type(e).__name__}: {e}"
                )
                continue

            all_findings.extend(sub_findings)
            all_coverage.append(coverage)
            if coverage.collected == 0:
                empty_categories.append(category)

        finished = utc_now()
        account = self._cached_account_id or self._account
        manifest = CollectionManifest(
            run_id=run_id,
            collector_id=COLLECTOR_ID,
            collector_version=current_version(),
            collection_started_at=started,
            collection_finished_at=finished,
            source_system_ids=[f"snowflake:{account}"],
            filters_applied=context.filter_applied,
            coverage_counts=all_coverage,
            total_findings=len(all_findings),
            is_complete=is_complete,
            incomplete_reason=(
                "; ".join(errors) if not is_complete else None
            ),
            empty_categories=empty_categories,
            warnings=warnings,
            errors=errors,
        )
        return all_findings, manifest
