"""Evidentia: open-source GRC tool for gap analysis, risk statements, and evidence collection."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("evidentia")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+unknown"
