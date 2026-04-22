"""AWS evidence collector for Evidentia.

Connects to AWS Config + Security Hub + (in v0.5.1) IAM Access Analyzer,
pulls findings, and returns them as typed
:class:`evidentia_core.models.finding.SecurityFinding` instances
pre-mapped to NIST 800-53 control IDs.

Install: ``pip install 'evidentia-collectors[aws]'`` (pulls in
``boto3``). Credentials come from the standard AWS SDK chain
(environment, ``~/.aws/credentials``, instance profile). Nothing new
to configure beyond what boto3 already does.

Public surface::

    from evidentia_collectors.aws import AwsCollector

    collector = AwsCollector(region="us-east-1")
    findings = collector.collect_all()
    # -> list[SecurityFinding]

Each ``SecurityFinding`` carries ``.control_ids`` populated via the
curated mapping in :mod:`.mapping`. Unmapped sources fall back to
``[]`` (empty list) — gap-analyze workflows then need to rely on the
finding's ``raw_data`` for per-finding control attribution.
"""

from evidentia_collectors.aws.collector import (
    AwsCollector,
    AwsCollectorError,
)
from evidentia_collectors.aws.mapping import (
    map_config_rule_to_controls,
    map_security_hub_control_to_controls,
)

__all__ = [
    "AwsCollector",
    "AwsCollectorError",
    "map_config_rule_to_controls",
    "map_security_hub_control_to_controls",
]
