"""AWS collector — orchestrates Config + Security Hub evidence pulls.

Requires the ``[aws]`` extra (``pip install 'evidentia-collectors[aws]'``).
Uses the standard AWS SDK credential chain — environment variables,
``~/.aws/credentials``, or (inside EC2/Lambda) the instance profile.

Each collector method returns a list of :class:`SecurityFinding` with
``control_ids`` pre-populated via the curated mapping in
:mod:`evidentia_collectors.aws.mapping`. Unmapped findings get an
empty ``control_ids`` list rather than a guess — callers can layer an
LLM-assisted mapper on top if they want speculative attribution.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from evidentia_core.models.common import Severity
from evidentia_core.models.finding import FindingStatus, SecurityFinding

from evidentia_collectors.aws.mapping import (
    map_config_rule_to_controls,
    map_security_hub_control_to_controls,
)

if TYPE_CHECKING:  # pragma: no cover
    pass

logger = logging.getLogger(__name__)


class AwsCollectorError(Exception):
    """Raised for collector-level failures (missing creds, missing region, etc)."""


class AwsCollector:
    """AWS evidence collector.

    One instance per AWS account + region. Credentials come from the
    standard boto3 chain; no Evidentia-specific auth knob.

    Usage::

        collector = AwsCollector(region="us-east-1")
        findings = collector.collect_all()
        # -> list[SecurityFinding]
    """

    def __init__(
        self,
        *,
        region: str | None = None,
        profile: str | None = None,
        _clients: dict[str, Any] | None = None,
    ) -> None:
        """Construct a collector.

        Parameters
        ----------
        region
            AWS region name, e.g. ``"us-east-1"``. Falls back to the
            default from the AWS SDK chain (env or ``~/.aws/config``).
        profile
            Optional named profile from ``~/.aws/credentials``.
        _clients
            Test-only override — lets unit tests inject already-built
            boto3 clients (typically from ``moto``). Should be a dict
            keyed by service name (``"config"``, ``"securityhub"``,
            ``"sts"``).
        """
        if _clients is not None:
            self._clients = _clients
            self._session: Any | None = None
            self._region = region or "us-east-1"
            return

        try:
            import boto3
        except ImportError as e:  # pragma: no cover
            raise AwsCollectorError(
                "boto3 is not installed. Install the collectors AWS extra: "
                "`pip install 'evidentia-collectors[aws]'`."
            ) from e

        self._session = boto3.Session(region_name=region, profile_name=profile)
        self._region = region or self._session.region_name or "us-east-1"
        self._clients = {}

    def _client(self, service: str) -> Any:
        """Get or lazily build a boto3 client for this service."""
        if service not in self._clients:
            if self._session is None:
                raise AwsCollectorError(
                    f"No boto3 client available for {service!r}; pass _clients "
                    "to the constructor when mocking."
                )
            self._clients[service] = self._session.client(service)
        return self._clients[service]

    @property
    def region(self) -> str:
        return self._region

    # ── test_connection ──────────────────────────────────────────────

    def test_connection(self) -> dict[str, str]:
        """Verify credentials + return caller identity.

        Calls ``sts:GetCallerIdentity``. Raises :class:`AwsCollectorError`
        if credentials are missing or invalid.
        """
        try:
            identity = self._client("sts").get_caller_identity()
        except Exception as e:
            raise AwsCollectorError(f"AWS connection failed: {e}") from e
        return {
            "account": str(identity.get("Account", "")),
            "arn": str(identity.get("Arn", "")),
            "user_id": str(identity.get("UserId", "")),
            "region": self._region,
        }

    # ── AWS Config ──────────────────────────────────────────────────

    def collect_config_findings(self) -> list[SecurityFinding]:
        """Return non-compliant AWS Config rule evaluations as findings.

        Iterates ``describe_compliance_by_config_rule``, then for each
        non-compliant rule fetches the resources via
        ``get_compliance_details_by_config_rule``. Each non-compliant
        resource becomes one :class:`SecurityFinding`.
        """
        client = self._client("config")
        findings: list[SecurityFinding] = []

        paginator = client.get_paginator("describe_compliance_by_config_rule")
        for page in paginator.paginate():
            for rule in page.get("ComplianceByConfigRules", []):
                if not isinstance(rule, dict):
                    continue
                rule_name = str(rule.get("ConfigRuleName", ""))
                compliance = rule.get("Compliance") or {}
                if compliance.get("ComplianceType") != "NON_COMPLIANT":
                    continue
                findings.extend(self._config_rule_findings(client, rule_name))

        return findings

    def _config_rule_findings(
        self, client: Any, rule_name: str
    ) -> list[SecurityFinding]:
        """Expand a non-compliant Config rule into per-resource findings."""
        out: list[SecurityFinding] = []
        control_ids = map_config_rule_to_controls(rule_name)

        paginator = client.get_paginator(
            "get_compliance_details_by_config_rule"
        )
        for page in paginator.paginate(
            ConfigRuleName=rule_name,
            ComplianceTypes=["NON_COMPLIANT"],
        ):
            for result in page.get("EvaluationResults", []):
                if not isinstance(result, dict):
                    continue
                ident = (result.get("EvaluationResultIdentifier") or {}).get(
                    "EvaluationResultQualifier"
                ) or {}
                resource_type = str(ident.get("ResourceType") or "")
                resource_id = str(ident.get("ResourceId") or "")
                annotation = str(result.get("Annotation") or "")
                recorded = result.get("ResultRecordedTime")

                title = f"AWS Config: {rule_name} non-compliant"
                description = (
                    annotation
                    or f"Resource {resource_id} ({resource_type}) is not compliant "
                    f"with rule {rule_name}."
                )

                out.append(
                    SecurityFinding(
                        title=title[:200],
                        description=description[:2000],
                        severity=Severity.MEDIUM,
                        status=FindingStatus.ACTIVE,
                        source_system="aws-config",
                        source_finding_id=f"{rule_name}:{resource_id}",
                        resource_type=resource_type or None,
                        resource_id=resource_id or None,
                        resource_region=self._region,
                        control_ids=control_ids,
                        raw_data={
                            "rule_name": rule_name,
                            "result": _jsonify(result),
                        },
                        first_observed=_to_datetime(recorded),
                        last_observed=_to_datetime(recorded),
                    )
                )
        return out

    # ── Security Hub ────────────────────────────────────────────────

    def collect_security_hub_findings(
        self,
        *,
        workflow_status: list[str] | None = None,
        max_findings: int = 1000,
    ) -> list[SecurityFinding]:
        """Return Security Hub findings as SecurityFinding objects.

        ``workflow_status`` filters to ``["NEW", "NOTIFIED"]`` by
        default — the "active triage" set. Pass ``["NEW", "NOTIFIED",
        "RESOLVED"]`` for historical reporting.
        """
        client = self._client("securityhub")
        findings: list[SecurityFinding] = []

        filters: dict[str, Any] = {
            "WorkflowStatus": [
                {"Value": s, "Comparison": "EQUALS"}
                for s in (workflow_status or ["NEW", "NOTIFIED"])
            ],
            "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
        }

        paginator = client.get_paginator("get_findings")
        seen = 0
        for page in paginator.paginate(Filters=filters):
            for raw in page.get("Findings", []):
                if not isinstance(raw, dict):
                    continue
                if seen >= max_findings:
                    break
                findings.append(self._security_hub_finding(raw))
                seen += 1
            if seen >= max_findings:
                break

        return findings

    def _security_hub_finding(self, raw: dict[str, Any]) -> SecurityFinding:
        """Convert a single Security Hub finding dict to a SecurityFinding."""
        title = str(raw.get("Title") or "")[:200]
        description = str(raw.get("Description") or "")[:2000]
        severity_label = str(
            (raw.get("Severity") or {}).get("Label") or "MEDIUM"
        ).lower()
        severity = _severity_from_label(severity_label)
        source_id = str(raw.get("Id") or "")

        # Resource data: just take the first resource for simplicity.
        resources = raw.get("Resources") or []
        first_resource = resources[0] if resources else {}
        resource_id = str(first_resource.get("Id") or "")
        resource_type = str(first_resource.get("Type") or "")
        region = str(first_resource.get("Region") or self._region)

        # Control IDs: prefer ``Compliance.RelatedRequirements`` if it
        # already carries NIST SP 800-53 refs; otherwise fall back to the
        # Standards control ID via the mapping table.
        compliance = raw.get("Compliance") or {}
        related = [
            str(r) for r in (compliance.get("RelatedRequirements") or []) if isinstance(r, str)
        ]
        control_ids: list[str]
        if any(r.startswith("NIST.800-53") for r in related):
            control_ids = [
                _extract_nist_id(r) for r in related if r.startswith("NIST.800-53")
            ]
            control_ids = [c for c in control_ids if c]
        else:
            generator_id = str(compliance.get("SecurityControlId") or raw.get("GeneratorId") or "")
            control_ids = map_security_hub_control_to_controls(generator_id)

        # ProductFields: account id.
        product_fields = raw.get("ProductFields") or {}
        account = str(raw.get("AwsAccountId") or product_fields.get("aws/securityhub/awsAccountId") or "")

        return SecurityFinding(
            title=title,
            description=description,
            severity=severity,
            status=FindingStatus.ACTIVE
            if str((raw.get("Workflow") or {}).get("Status") or "NEW") != "RESOLVED"
            else FindingStatus.RESOLVED,
            source_system="aws-security-hub",
            source_finding_id=source_id,
            resource_type=resource_type or None,
            resource_id=resource_id or None,
            resource_region=region,
            resource_account=account or None,
            control_ids=control_ids,
            raw_data=_jsonify(raw),
            first_observed=_to_datetime(raw.get("FirstObservedAt"))
            or _to_datetime(raw.get("CreatedAt")),
            last_observed=_to_datetime(raw.get("LastObservedAt"))
            or _to_datetime(raw.get("UpdatedAt")),
        )

    # ── Orchestration ───────────────────────────────────────────────

    def collect_all(
        self, *, include_config: bool = True, include_security_hub: bool = True
    ) -> list[SecurityFinding]:
        """Run every sub-collector and return a merged list."""
        findings: list[SecurityFinding] = []
        if include_config:
            try:
                findings.extend(self.collect_config_findings())
            except Exception:
                logger.exception("AWS Config collector failed")
        if include_security_hub:
            try:
                findings.extend(self.collect_security_hub_findings())
            except Exception:
                logger.exception("AWS Security Hub collector failed")
        return findings


# ── helpers ──────────────────────────────────────────────────────────────


def _severity_from_label(label: str) -> Severity:
    """Map Security Hub severity label -> Evidentia Severity.

    Security Hub uses CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL —
    same enum, just different case.
    """
    lookup = {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
        "informational": Severity.INFORMATIONAL,
    }
    return lookup.get(label.lower(), Severity.MEDIUM)


def _extract_nist_id(related: str) -> str:
    """Pull the control ID out of a NIST-related-requirement string.

    Security Hub emits ``"NIST.800-53.r5 AC-2"`` / ``"NIST.800-53.r5 SC-8(2)"``.
    We return the control ID suffix.
    """
    parts = related.strip().split()
    return parts[-1] if len(parts) >= 2 else ""


def _jsonify(value: Any) -> Any:
    """Best-effort make a boto3 response JSON-serializable.

    boto3 returns datetimes and other native types that don't survive
    a plain ``json.dumps``. Walk the structure + isoformat any dates.
    """
    if isinstance(value, dict):
        return {k: _jsonify(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonify(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _to_datetime(value: Any) -> datetime:
    """Coerce a boto3-returned timestamp (datetime or ISO string) to a datetime."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    from datetime import UTC

    return datetime.now(UTC)
