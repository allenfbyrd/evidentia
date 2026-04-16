"""OSCAL catalog loader.

Loads NIST-published OSCAL JSON catalogs from bundled data files
and parses them into indexed ControlCatalog objects.

Supported catalog formats:
- OSCAL Catalog JSON (NIST 800-53, CSF 2.0)
- ControlBridge framework JSON (SOC 2, ISO 27001, CIS, CMMC, PCI DSS)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from controlbridge_core.models.catalog import CatalogControl, ControlCatalog

logger = logging.getLogger(__name__)

# Path to bundled data directory
DATA_DIR = Path(__file__).parent / "data"


def load_oscal_catalog(catalog_path: Path) -> ControlCatalog:
    """Load an OSCAL Catalog JSON file into a ControlCatalog.

    Parses the OSCAL catalog structure with groups → controls → enhancements.
    """
    with open(catalog_path, encoding="utf-8") as f:
        data = json.load(f)

    catalog_data = data.get("catalog", data)
    metadata = catalog_data.get("metadata", {})

    controls: list[CatalogControl] = []
    families: list[str] = []

    for group in catalog_data.get("groups", []):
        family_title = group.get("title", "")
        families.append(family_title)

        for oscal_control in group.get("controls", []):
            control = _parse_oscal_control(oscal_control, family_title)
            controls.append(control)

    framework_id = _detect_framework_id(catalog_path, metadata)
    framework_name = metadata.get("title", catalog_path.stem)
    version = metadata.get("version", "unknown")

    catalog = ControlCatalog(
        framework_id=framework_id,
        framework_name=framework_name,
        version=version,
        source=f"OSCAL: {catalog_path.name}",
        controls=controls,
        families=families,
    )

    logger.info(
        "Loaded catalog '%s': %d controls in %d families",
        framework_name,
        catalog.control_count,
        len(families),
    )
    return catalog


def _parse_oscal_control(oscal_control: dict, family: str) -> CatalogControl:
    """Parse a single OSCAL control into a CatalogControl."""
    control_id = oscal_control.get("id", "").upper()
    title = oscal_control.get("title", "")

    # Extract description from parts
    description = ""
    for part in oscal_control.get("parts", []):
        if part.get("name") == "statement":
            description = _extract_prose(part)
            break

    # Extract assessment objectives
    objectives: list[str] = []
    for part in oscal_control.get("parts", []):
        if part.get("name") == "assessment-objective":
            objectives.append(_extract_prose(part))

    # Parse enhancements (nested controls)
    enhancements: list[CatalogControl] = []
    for sub_control in oscal_control.get("controls", []):
        enhancement = _parse_oscal_control(sub_control, family)
        enhancements.append(enhancement)

    # Extract priority from properties
    priority = None
    for prop in oscal_control.get("props", []):
        if prop.get("name") == "priority":
            priority = prop.get("value")

    # Extract baseline impact from properties
    baseline_impact: list[str] = []
    for prop in oscal_control.get("props", []):
        if prop.get("name") in ("baseline", "impact"):
            value = prop.get("value", "")
            if value:
                baseline_impact.append(value)

    # Extract related controls from links
    related: list[str] = []
    for link in oscal_control.get("links", []):
        if link.get("rel") == "related":
            related.append(link.get("href", "").replace("#", "").upper())

    # Extract parameters
    parameters: dict[str, str] = {}
    for param in oscal_control.get("params", []):
        param_id = param.get("id", "")
        default_value = ""
        if "select" in param:
            choices = param["select"].get("choice", [])
            default_value = " | ".join(choices) if choices else ""
        elif "guidelines" in param:
            guidelines = param["guidelines"]
            if guidelines:
                default_value = guidelines[0].get("prose", "")
        parameters[param_id] = default_value

    return CatalogControl(
        id=control_id,
        title=title,
        description=description,
        family=family,
        priority=priority,
        baseline_impact=baseline_impact,
        enhancements=enhancements,
        related_controls=related,
        assessment_objectives=objectives,
        parameters=parameters,
    )


def _extract_prose(part: dict) -> str:
    """Recursively extract prose text from an OSCAL part."""
    prose = part.get("prose", "")
    for sub_part in part.get("parts", []):
        sub_prose = _extract_prose(sub_part)
        if sub_prose:
            prose += "\n" + sub_prose
    return prose.strip()


def _detect_framework_id(path: Path, metadata: dict) -> str:
    """Detect the framework ID from the file path or metadata."""
    stem = path.stem.lower()
    if "800-53" in stem and "rev5" in stem:
        return "nist-800-53-rev5"
    if "800-53" in stem and "mod" in stem:
        return "nist-800-53-mod"
    if "800-53" in stem and "high" in stem:
        return "nist-800-53-high"
    if "csf" in stem and "2.0" in stem:
        return "nist-csf-2.0"
    return stem


def load_controlbridge_catalog(catalog_path: Path) -> ControlCatalog:
    """Load a ControlBridge-format framework catalog.

    Used for frameworks that don't have OSCAL catalogs published by NIST
    (SOC 2, ISO 27001, CIS, CMMC, PCI DSS). These are stored as
    ControlBridge JSON format with a simplified structure.
    """
    with open(catalog_path, encoding="utf-8") as f:
        data = json.load(f)

    controls = [CatalogControl(**c) for c in data.get("controls", [])]

    return ControlCatalog(
        framework_id=data["framework_id"],
        framework_name=data["framework_name"],
        version=data.get("version", "1.0"),
        source=data.get("source", f"ControlBridge: {catalog_path.name}"),
        controls=controls,
        families=data.get("families", []),
        # Tier / licensing metadata added in v0.1.1 for Tier-C stub
        # catalogs (e.g., SOC 2 TSC). Defaults preserve the v0.1.0 shape
        # for plain ControlBridge-format catalogs that omit these fields.
        tier=data.get("tier"),
        license_required=data.get("license_required", False),
        license_terms=data.get("license_terms"),
        license_url=data.get("license_url"),
        placeholder=data.get("placeholder", False),
    )


def load_catalog(framework_id: str, custom_path: Path | None = None) -> ControlCatalog:
    """Load a catalog by framework ID.

    First checks for a custom path, then looks in the bundled data directory.
    Auto-detects format (OSCAL vs ControlBridge) based on file contents.
    """
    if custom_path:
        path = custom_path
    else:
        # Bundled catalog files. v0.1.1 ships 2; v0.2.0 will move this
        # dispatch to a manifest-driven loader. Must mirror registry.py's
        # FRAMEWORK_METADATA — adding here without a catalog JSON on disk
        # produces a FileNotFoundError at load time.
        framework_files = {
            "nist-800-53-mod": "nist-800-53-mod.json",
            "soc2-tsc": "soc2-tsc.json",
        }
        filename = framework_files.get(framework_id)
        if not filename:
            raise ValueError(
                f"Unknown framework '{framework_id}'. "
                f"Available: {', '.join(framework_files.keys())}"
            )
        path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Catalog file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Auto-detect format
    if "catalog" in data:
        return load_oscal_catalog(path)
    return load_controlbridge_catalog(path)
