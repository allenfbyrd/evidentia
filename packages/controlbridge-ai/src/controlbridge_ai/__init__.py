"""ControlBridge AI: LLM-powered risk statement generation and evidence validation."""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version("controlbridge-ai")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+unknown"
