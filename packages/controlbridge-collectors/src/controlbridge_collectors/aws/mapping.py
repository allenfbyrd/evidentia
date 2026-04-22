"""Curated mapping: AWS Config rules + Security Hub controls -> NIST 800-53.

These tables are intentionally conservative. We map what we *know* is
right (the control IDs the AWS Foundational Security Best Practices
standard explicitly references, or that are obvious from the rule's
semantics). Unknown sources fall back to an empty list rather than a
guess — better to under-attribute than to claim false coverage.

Expand this module over time as new rules land; every addition ships
with a code comment naming the primary source (FSBP / CIS / PCI-DSS /
HIPAA). v0.6.0 adds an LLM-assisted mapper for rules not in this
table, gated behind a ``--ai-assist`` flag.
"""

from __future__ import annotations

from typing import Final

# ── AWS Config rule name -> NIST 800-53 control IDs ───────────────────────

#: Maps normalized AWS Config rule names (lowercase, hyphen-separated)
#: to lists of NIST 800-53 Rev 5 control IDs. Exhaustive for the ~25
#: most-common AWS managed rules as of 2025; external rules or custom
#: rules return an empty list from :func:`map_config_rule_to_controls`.
CONFIG_RULE_TO_CONTROLS: Final[dict[str, list[str]]] = {
    # Access control (AC family)
    "access-keys-rotated": ["AC-2", "IA-5"],
    "iam-password-policy": ["IA-5"],
    "iam-root-access-key-check": ["AC-2", "AC-6"],
    "iam-user-mfa-enabled": ["IA-2"],
    "iam-user-no-policies-check": ["AC-2", "AC-6"],
    "mfa-enabled-for-iam-console-access": ["IA-2"],
    "root-account-mfa-enabled": ["IA-2", "AC-6"],
    # Encryption in transit / at rest (SC family)
    "alb-http-to-https-redirection-check": ["SC-8"],
    "elb-tls-https-listeners-only": ["SC-8"],
    "encrypted-volumes": ["SC-28"],
    "rds-storage-encrypted": ["SC-28"],
    "s3-bucket-server-side-encryption-enabled": ["SC-28"],
    "s3-bucket-ssl-requests-only": ["SC-8"],
    # Public exposure (AC + SC families)
    "ec2-security-group-attached-to-eni": ["AC-4", "SC-7"],
    "rds-instance-public-access-check": ["AC-3", "AC-4", "SC-7"],
    "s3-bucket-public-read-prohibited": ["AC-3", "AC-6"],
    "s3-bucket-public-write-prohibited": ["AC-3", "AC-6"],
    "vpc-default-security-group-closed": ["AC-4", "SC-7"],
    # Logging + audit (AU family)
    "cloudtrail-enabled": ["AU-2", "AU-3", "AU-12"],
    "cloud-trail-log-file-validation-enabled": ["AU-9", "AU-10"],
    "cloudwatch-log-group-encrypted": ["SC-28", "AU-9"],
    "multi-region-cloudtrail-enabled": ["AU-2", "AU-12"],
    "s3-bucket-logging-enabled": ["AU-2", "AU-12"],
    # Backup + availability (CP family)
    "backup-plan-min-frequency-and-min-retention-check": ["CP-9"],
    "rds-automatic-minor-version-upgrade-enabled": ["SI-2"],
    "rds-multi-az-support": ["CP-9", "CP-10"],
    # Patching (SI family)
    "ec2-managedinstance-patch-compliance-status-check": ["SI-2"],
    # Configuration management (CM family)
    "ec2-instance-detailed-monitoring-enabled": ["CM-8", "SI-4"],
    "ec2-instance-managed-by-ssm": ["CM-8"],
}

# ── Security Hub FSBP control id -> NIST 800-53 ──────────────────────────

#: Maps AWS Security Hub (FSBP v1.0.0 + CIS AWS Foundations v1.4.0)
#: control identifiers to NIST 800-53 Rev 5 control IDs. Security Hub
#: itself surfaces NIST SP 800-53 v5 as an enabled standard — when
#: findings carry explicit related-requirements fields, we use those
#: directly and don't consult this table.
SECURITY_HUB_CONTROL_TO_CONTROLS: Final[dict[str, list[str]]] = {
    # CIS AWS Foundations v1.4.0
    "cis.1.4": ["AC-6", "IA-2"],  # Ensure no root user access key
    "cis.1.5": ["IA-2"],  # Root account MFA
    "cis.1.7": ["IA-2"],  # MFA for every user with a password
    "cis.1.8": ["IA-5"],  # Password length >= 14
    "cis.1.10": ["IA-5"],  # Password reuse prevention
    "cis.1.14": ["AC-2"],  # Access keys rotated every 90 days
    "cis.2.1.1": ["SC-28"],  # S3 default encryption
    "cis.3.1": ["AU-2", "AU-12"],  # CloudTrail in all regions
    "cis.3.4": ["AU-9"],  # CloudTrail log file validation
    # AWS Foundational Security Best Practices
    "fsbp.acm.1": ["SC-17"],  # ACM cert renewal
    "fsbp.cloudtrail.1": ["AU-2", "AU-12"],  # CloudTrail enabled
    "fsbp.cloudtrail.4": ["AU-9"],  # CloudTrail validation
    "fsbp.ec2.2": ["AC-4", "SC-7"],  # Security group least-priv
    "fsbp.ec2.6": ["AU-12"],  # VPC flow logs
    "fsbp.iam.1": ["AC-6", "IA-2"],  # Root access key
    "fsbp.iam.4": ["AC-2"],  # Root access key
    "fsbp.iam.6": ["IA-2"],  # Root MFA
    "fsbp.iam.8": ["AC-2"],  # Unused creds 90d
    "fsbp.rds.2": ["AC-3", "SC-7"],  # RDS public access
    "fsbp.rds.3": ["SC-28"],  # RDS encryption at rest
    "fsbp.rds.4": ["SC-8"],  # RDS snapshot encryption
    "fsbp.s3.1": ["AC-3"],  # Block Public Access
    "fsbp.s3.2": ["AC-3"],  # S3 public read
    "fsbp.s3.3": ["AC-3"],  # S3 public write
    "fsbp.s3.5": ["SC-8"],  # S3 SSL-only
    "fsbp.s3.6": ["AU-2"],  # S3 logging
}


def map_config_rule_to_controls(rule_name: str) -> list[str]:
    """Return NIST 800-53 control IDs for an AWS Config rule name.

    Normalizes case + strips common AWS-managed-rule prefixes so both
    hyphenated identifiers (``s3-bucket-public-read-prohibited``) and
    camelCase (``S3BucketPublicReadProhibited``) hit the same mapping.
    Unknown rules return an empty list.
    """
    normalized = _normalize_rule_name(rule_name)
    return list(CONFIG_RULE_TO_CONTROLS.get(normalized, []))


def map_security_hub_control_to_controls(control_id: str) -> list[str]:
    """Return NIST 800-53 control IDs for a Security Hub control identifier.

    ``control_id`` is the ``ControlId`` / ``StandardsControlArn`` suffix
    ("1.4", "IAM.6", "S3.3"). We normalize to lowercase dotted form and
    look up via :data:`SECURITY_HUB_CONTROL_TO_CONTROLS`. Unknown
    controls return an empty list.
    """
    normalized = _normalize_security_hub_id(control_id)
    return list(SECURITY_HUB_CONTROL_TO_CONTROLS.get(normalized, []))


def _normalize_rule_name(raw: str) -> str:
    """Lowercase + hyphen-separate a Config rule name.

    ``S3BucketPublicReadProhibited`` -> ``s3-bucket-public-read-prohibited``
    ``s3-bucket-public-read-prohibited`` -> unchanged.
    """
    if not raw:
        return ""
    out: list[str] = []
    for i, ch in enumerate(raw):
        if ch.isupper() and i > 0 and raw[i - 1] != "-":
            out.append("-")
        out.append(ch.lower())
    return "".join(out).replace("_", "-")


def _normalize_security_hub_id(raw: str) -> str:
    """Normalize a Security Hub control id to lowercase dotted form.

    The AWS Security Hub API returns things like ``"IAM.6"`` (bare FSBP
    id) or ``"1.4"`` (bare CIS id). Our table keys are prefixed
    ``"fsbp.iam.6"`` / ``"cis.1.4"`` to disambiguate across standards.
    This normalizer adds the standard prefix where needed.
    """
    cleaned = raw.strip().lower()
    # If it already has our prefix, leave it.
    if cleaned.startswith(("fsbp.", "cis.")):
        return cleaned
    # CIS controls are dotted numeric ("1.4", "2.1.1", "3.1").
    if cleaned and cleaned[0].isdigit():
        return f"cis.{cleaned}"
    # FSBP controls have a named section prefix ("iam.6", "s3.3").
    return f"fsbp.{cleaned}"
