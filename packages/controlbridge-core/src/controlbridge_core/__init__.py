"""ControlBridge core: data models, OSCAL catalog loaders, and gap analysis engine."""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version("controlbridge-core")
except PackageNotFoundError:  # pragma: no cover — only hit in editable repos without install
    __version__ = "0.0.0+unknown"
