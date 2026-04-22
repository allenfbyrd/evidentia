"""Evidentia AI: LLM-powered risk statement generation and evidence validation."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("evidentia-ai")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+unknown"
