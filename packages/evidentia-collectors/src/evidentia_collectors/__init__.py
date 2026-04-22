"""Evidentia collectors: evidence collection agents for cloud and SaaS systems."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("evidentia-collectors")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+unknown"
