"""Init-wizard router — GUI "Start from scratch" onboarding path.

Wraps :mod:`evidentia_core.init_wizard` for browser use. The client
POSTs industry + hosting + data types; the server returns three
pre-generated YAMLs + a recommended framework list. The browser
previews them, and only writes files to disk (on the server) if the
user clicks "Commit".
"""

from __future__ import annotations

from evidentia_core.init_wizard import (
    generate_evidentia_yaml,
    generate_my_controls_yaml,
    generate_system_context_yaml,
    recommend_frameworks,
)
from fastapi import APIRouter, HTTPException

from evidentia_api.schemas import InitWizardRequest, InitWizardResponse

router = APIRouter()


@router.post("/init/wizard", response_model=InitWizardResponse)
async def init_wizard(payload: InitWizardRequest) -> InitWizardResponse:
    """Generate starter YAMLs from lightweight onboarding context.

    Returns three pre-filled files + a recommended framework list. The
    client previews them in the wizard UI and may edit before committing.
    Writing to disk is a separate endpoint call (future v0.4.1).
    """
    recommended = recommend_frameworks(
        industry=payload.industry,
        hosting=payload.hosting,
        data_classification=payload.data_classification,
        regulatory_requirements=payload.regulatory_requirements,
    )

    cb_yaml = generate_evidentia_yaml(
        organization=payload.organization,
        frameworks=recommended,
        system_name=payload.system_name,
    )

    try:
        my_controls_yaml = generate_my_controls_yaml(
            preset=payload.preset,  # type: ignore[arg-type]
            organization=payload.organization,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    sys_ctx_yaml = generate_system_context_yaml(
        organization=payload.organization,
        system_name=payload.system_name or "Your System",
        data_classification=payload.data_classification,
        hosting=payload.hosting or "(cloud provider + region)",
        regulatory_requirements=payload.regulatory_requirements,
    )

    return InitWizardResponse(
        evidentia_yaml=cb_yaml,
        my_controls_yaml=my_controls_yaml,
        system_context_yaml=sys_ctx_yaml,
        recommended_frameworks=recommended,
    )
