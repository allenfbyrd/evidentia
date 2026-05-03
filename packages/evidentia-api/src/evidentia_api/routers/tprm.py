"""TPRM router — vendor inventory CRUD endpoints (v0.7.9 P0.1.4).

Surfaces the v0.7.9 P0.1.1 Vendor model + P0.1.2 vendor_store
persistence over HTTP under the ``/api/tprm/vendors`` prefix.

Endpoints (resolved per plan §17.B1-B4):

  - ``GET    /api/tprm/vendors`` — list vendors with optional
    skip/limit pagination + criticality_tier/type filters
  - ``POST   /api/tprm/vendors`` — create a new vendor; server
    fills id / created_at / updated_at / evidentia_version via
    Pydantic default_factory
  - ``GET    /api/tprm/vendors/{vendor_id}`` — fetch single vendor
  - ``PUT    /api/tprm/vendors/{vendor_id}`` — full-replace
    (preserves id + created_at; refreshes updated_at)
  - ``DELETE /api/tprm/vendors/{vendor_id}`` — remove from store

Error normalization follows the v0.7.8 F-V08-DAST-3 fix
(plan §17.B4): manual HTTPException uses status 400 (not 422)
for runtime body-content validation errors so the
``{detail: string}`` response shape matches the OpenAPI
declaration. Pydantic auto-validation 422s (from FastAPI's
request-body parsing) keep their array-shape detail.
"""

from __future__ import annotations

from datetime import date

from evidentia_core.models.tprm import (
    CriticalityTier,
    Vendor,
    VendorType,
)
from evidentia_core.vendor_store import (
    InvalidVendorIdError,
    delete_vendor,
    list_vendors,
    load_vendor_by_id,
    save_vendor,
)
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


# ── helpers ────────────────────────────────────────────────────────


def _filter_vendors(
    vendors: list[Vendor],
    criticality_tier: str | None,
    type_: str | None,
) -> list[Vendor]:
    if criticality_tier:
        vendors = [v for v in vendors if v.criticality_tier == criticality_tier]
    if type_:
        vendors = [v for v in vendors if v.type == type_]
    return vendors


# ── endpoints ──────────────────────────────────────────────────────


@router.get("/tprm/vendors")
async def list_vendors_endpoint(
    skip: int = Query(
        0,
        ge=0,
        description="Number of records to skip (pagination offset).",
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of records to return (1-1000).",
    ),
    criticality_tier: str | None = Query(
        None,
        description=(
            "Filter by criticality tier: critical / high / medium / low."
        ),
    ),
    type_: str | None = Query(
        None,
        alias="type",
        description=(
            "Filter by vendor type: saas / subservice_org / contractor / "
            "data_processor / cloud_provider / open_source."
        ),
    ),
) -> dict[str, object]:
    """List vendors in the inventory.

    Sort order matches `evidentia_core.vendor_store.list_vendors`:
    criticality (critical → low) then name (case-insensitive).
    Pagination is applied AFTER filtering so ``total`` reflects
    the filter-matched count, not the unfiltered store size.
    """
    if criticality_tier and criticality_tier not in {
        e.value for e in CriticalityTier
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown criticality_tier {criticality_tier!r}; valid: "
                f"{sorted(e.value for e in CriticalityTier)}"
            ),
        )
    if type_ and type_ not in {e.value for e in VendorType}:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown type {type_!r}; valid: "
                f"{sorted(e.value for e in VendorType)}"
            ),
        )

    all_vendors = list_vendors()
    filtered = _filter_vendors(all_vendors, criticality_tier, type_)
    total = len(filtered)
    page = filtered[skip : skip + limit]
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "vendors": [v.model_dump(mode="json") for v in page],
    }


@router.post("/tprm/vendors", response_model=Vendor, status_code=201)
async def create_vendor(payload: Vendor) -> Vendor:
    """Create a new vendor record.

    Body shape is the full Vendor model (resolved per §17.B2).
    Server fills ``id`` / ``created_at`` / ``updated_at`` /
    ``evidentia_version`` via Pydantic default_factory when the
    client omits them. ``next_review_due`` is auto-computed from
    ``last_due_diligence_review`` + criticality cadence when the
    client provides the former and omits the latter.
    """
    if payload.last_due_diligence_review and payload.next_review_due is None:
        payload.next_review_due = payload.compute_next_review_due()
    save_vendor(payload)
    return payload


@router.get("/tprm/vendors/{vendor_id}", response_model=Vendor)
async def get_vendor(vendor_id: str) -> Vendor:
    """Fetch a single vendor by ID."""
    try:
        vendor = load_vendor_by_id(vendor_id)
    except InvalidVendorIdError as exc:
        # Match the v0.7.8 F-V08-DAST-1 widening pattern: shape
        # violations + not-found both normalize to 404 from the
        # client's perspective.
        raise HTTPException(
            status_code=404,
            detail=f"Vendor {vendor_id!r} not found.",
        ) from exc
    if vendor is None:
        raise HTTPException(
            status_code=404,
            detail=f"Vendor {vendor_id!r} not found.",
        )
    return vendor


@router.put("/tprm/vendors/{vendor_id}", response_model=Vendor)
async def replace_vendor(vendor_id: str, payload: Vendor) -> Vendor:
    """Replace a vendor record by ID (full update).

    Preserves the original ``id`` + ``created_at`` even if the
    client supplies different values — the path parameter is
    authoritative for identity, and ``created_at`` is immutable
    once the record exists. ``updated_at`` is refreshed by
    `vendor_store.save_vendor` regardless.
    """
    try:
        existing = load_vendor_by_id(vendor_id)
    except InvalidVendorIdError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Vendor {vendor_id!r} not found.",
        ) from exc
    if existing is None:
        raise HTTPException(
            status_code=404,
            detail=f"Vendor {vendor_id!r} not found.",
        )
    # Authoritatively pin id + created_at; refresh
    # next_review_due if the anchor changed.
    payload.id = existing.id
    payload.created_at = existing.created_at
    if payload.last_due_diligence_review:
        payload.next_review_due = payload.compute_next_review_due()
    save_vendor(payload)
    return payload


@router.delete("/tprm/vendors/{vendor_id}", status_code=204)
async def delete_vendor_endpoint(vendor_id: str) -> None:
    """Delete a vendor by ID.

    Returns 204 on successful delete, 404 on shape-violation OR
    well-formed-unknown ID. No body in either case (HEAD-like
    semantics for DELETE).
    """
    try:
        removed = delete_vendor(vendor_id)
    except InvalidVendorIdError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Vendor {vendor_id!r} not found.",
        ) from exc
    if not removed:
        raise HTTPException(
            status_code=404,
            detail=f"Vendor {vendor_id!r} not found.",
        )


# ── helper endpoint: cadence preview ──────────────────────────────


@router.get("/tprm/vendors/{vendor_id}/next-review-due")
async def preview_next_review_due(vendor_id: str) -> dict[str, str | None]:
    """Compute (without persisting) the next review due date.

    Returns ``{"next_review_due": "<YYYY-MM-DD>"}`` or
    ``{"next_review_due": null}`` if the vendor has no
    ``last_due_diligence_review`` anchor. Useful for UI previews
    that want to show "if you set the DD review to today, your
    next review would be on…".
    """
    try:
        vendor = load_vendor_by_id(vendor_id)
    except InvalidVendorIdError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Vendor {vendor_id!r} not found.",
        ) from exc
    if vendor is None:
        raise HTTPException(
            status_code=404,
            detail=f"Vendor {vendor_id!r} not found.",
        )
    computed: date | None = vendor.compute_next_review_due()
    return {
        "next_review_due": computed.isoformat() if computed else None,
    }
