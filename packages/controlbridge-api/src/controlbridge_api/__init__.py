"""ControlBridge API: FastAPI REST server + bundled React web UI.

The FastAPI application is exposed as :data:`controlbridge_api.app.app` and
can be served directly with uvicorn:

    uvicorn controlbridge_api.app:app --host 127.0.0.1 --port 8000

Typical users reach it via the CLI:

    controlbridge serve [--host HOST] [--port PORT] [--offline]

which is a thin Typer wrapper around :func:`controlbridge_api.cli.serve`.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("controlbridge-api")
except PackageNotFoundError:  # pragma: no cover — only hit in editable repos without install
    __version__ = "0.0.0+unknown"
