"""FastAPI application factory.

The module-level ``app`` is the canonical instance that uvicorn references.
For testing (TestClient), prefer :func:`create_app` which accepts overrides.

All API routes live under ``/api/*``. Static assets (the bundled React SPA)
are mounted at ``/`` and serve ``index.html`` for every non-``/api/*`` path
to support client-side routing (React Router).

In v0.4.0 the static directory is populated at wheel-build time by the
frontend build hook in ``.github/workflows/release.yml`` (it runs
``npm run build`` in ``packages/controlbridge-ui`` and copies ``dist/*``
into ``src/controlbridge_api/static/``). When the directory is empty at
runtime (e.g. fresh dev install without a build), a placeholder JSON
response is returned instead of 404 so the error is self-explanatory.

Offline mode: the ``controlbridge serve --offline`` CLI entry point sets
``CONTROLBRIDGE_API_OFFLINE=1`` in the subprocess env. This module reads
that at import time to flip the process-wide air-gap guard before any
router handler runs.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from controlbridge_api import __version__

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
"""Absolute path to the bundled SPA assets (populated at build time)."""


def create_app(
    *,
    offline: bool = False,
    dev_mode: bool = False,
    cors_origins: list[str] | None = None,
) -> FastAPI:
    """Build and return a FastAPI application.

    Parameters
    ----------
    offline
        When True, flips the process-wide air-gap guard at app creation.
        Every LLM/network call then refuses non-loopback targets.
    dev_mode
        When True, CORS is permissive to support the Vite dev server
        (http://127.0.0.1:5173) without a proxy.
    cors_origins
        Explicit allow-list override. Default: restrictive localhost-only.
    """
    if offline:
        from controlbridge_core.network_guard import set_offline

        set_offline(True)

    app = FastAPI(
        title="ControlBridge API",
        description=(
            "REST API for the ControlBridge GRC tool. All endpoints mirror "
            "CLI capabilities. Binds to 127.0.0.1 by default for localhost "
            "web-UI use."
        ),
        version=__version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS: dev_mode is permissive for Vite HMR; prod is localhost-only.
    if cors_origins is None:
        cors_origins = (
            [
                "http://127.0.0.1:5173",
                "http://localhost:5173",
                "http://127.0.0.1:8000",
                "http://localhost:8000",
            ]
            if dev_mode
            else ["http://127.0.0.1:8000", "http://localhost:8000"]
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # Attach flags to app state so every router dep can consult them.
    app.state.offline = offline
    app.state.dev_mode = dev_mode

    # Register routers. Each router is a focused module — see routers/*.py.
    # Imports are deferred so module-load errors in one router don't take
    # down the whole server.
    from controlbridge_api.routers import (
        collectors as collectors_router,
    )
    from controlbridge_api.routers import (
        config as config_router,
    )
    from controlbridge_api.routers import (
        doctor as doctor_router,
    )
    from controlbridge_api.routers import (
        explain as explain_router,
    )
    from controlbridge_api.routers import (
        frameworks as frameworks_router,
    )
    from controlbridge_api.routers import (
        gaps as gaps_router,
    )
    from controlbridge_api.routers import (
        health as health_router,
    )
    from controlbridge_api.routers import (
        init_wizard as init_wizard_router,
    )
    from controlbridge_api.routers import (
        integrations as integrations_router,
    )
    from controlbridge_api.routers import (
        llm_status as llm_status_router,
    )
    from controlbridge_api.routers import (
        risks as risks_router,
    )

    app.include_router(health_router.router, prefix="/api", tags=["health"])
    app.include_router(config_router.router, prefix="/api", tags=["config"])
    app.include_router(doctor_router.router, prefix="/api", tags=["doctor"])
    app.include_router(llm_status_router.router, prefix="/api", tags=["llm"])
    app.include_router(
        frameworks_router.router, prefix="/api", tags=["frameworks"]
    )
    app.include_router(gaps_router.router, prefix="/api", tags=["gaps"])
    app.include_router(risks_router.router, prefix="/api", tags=["risks"])
    app.include_router(explain_router.router, prefix="/api", tags=["explain"])
    app.include_router(
        init_wizard_router.router, prefix="/api", tags=["init"]
    )
    app.include_router(
        integrations_router.router, prefix="/api", tags=["integrations"]
    )
    app.include_router(
        collectors_router.router, prefix="/api", tags=["collectors"]
    )

    # Static SPA mount — everything that isn't /api/* falls through to index.html.
    _mount_spa(app)

    return app


def _mount_spa(app: FastAPI) -> None:
    """Mount the bundled React SPA at the root.

    If the static directory is missing or empty (common in fresh dev checkouts
    before ``npm run build`` has been executed), serve a helpful placeholder
    instead of 404 so users can self-diagnose.
    """
    if STATIC_DIR.is_dir() and (STATIC_DIR / "index.html").is_file():
        # Mount static/assets first for JS/CSS/fonts; then SPA fallback.
        assets_dir = STATIC_DIR / "assets"
        if assets_dir.is_dir():
            app.mount(
                "/assets",
                StaticFiles(directory=assets_dir),
                name="spa-assets",
            )

        @app.get("/{full_path:path}", include_in_schema=False)
        async def _spa_fallback(full_path: str, request: Request) -> FileResponse:
            """Serve index.html for every non-API path so React Router owns routing."""
            if full_path.startswith("api/"):
                # Defensive — FastAPI routing should have caught these already.
                return FileResponse(STATIC_DIR / "index.html", status_code=404)
            target = STATIC_DIR / full_path
            if target.is_file():
                return FileResponse(target)
            return FileResponse(STATIC_DIR / "index.html")

    else:
        logger.info(
            "Static SPA directory is empty at %s — serving dev placeholder. "
            "Run `npm run build` in packages/controlbridge-ui/ to populate.",
            STATIC_DIR,
        )

        @app.get("/{full_path:path}", include_in_schema=False)
        async def _dev_placeholder(full_path: str) -> JSONResponse:
            if full_path.startswith("api/"):
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            return JSONResponse(
                status_code=503,
                content={
                    "error": "spa_not_built",
                    "message": (
                        "The ControlBridge web UI is not bundled in this install. "
                        "If you are developing, run `npm install && npm run dev` "
                        "in packages/controlbridge-ui/ and use `controlbridge "
                        "serve --dev`. If you are an end user, please reinstall "
                        "with `pip install --force-reinstall controlbridge[gui]`."
                    ),
                    "api_docs": "/api/docs",
                },
            )


# Read env-var flags set by ``controlbridge serve`` subprocess launch.
# CONTROLBRIDGE_API_OFFLINE=1 -> offline mode
# CONTROLBRIDGE_API_DEV=1     -> permissive CORS for Vite dev server
_env_offline = os.environ.get("CONTROLBRIDGE_API_OFFLINE", "").strip().lower() in {
    "1",
    "true",
    "yes",
}
_env_dev = os.environ.get("CONTROLBRIDGE_API_DEV", "").strip().lower() in {
    "1",
    "true",
    "yes",
}

# Default instance for `uvicorn controlbridge_api.app:app` usage.
app = create_app(offline=_env_offline, dev_mode=_env_dev)
