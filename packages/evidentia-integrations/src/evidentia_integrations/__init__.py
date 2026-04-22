"""Evidentia integrations: output integrations for Jira, ServiceNow, and OSCAL exporters."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("evidentia-integrations")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+unknown"
