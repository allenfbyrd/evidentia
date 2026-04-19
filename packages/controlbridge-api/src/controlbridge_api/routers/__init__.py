"""FastAPI routers — one module per logical endpoint group.

Routers are registered in :func:`controlbridge_api.app.create_app`; each
module exposes a ``router: APIRouter`` module-level attribute.
"""
