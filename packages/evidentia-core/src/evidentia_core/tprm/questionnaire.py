"""Vendor due-diligence questionnaire generator (v0.7.9 P0.2).

Auto-generates SIG / SIG-Lite / CAIQ-style questionnaires for a
vendor in the inventory. Pre-fills vendor-metadata fields (name,
type, criticality tier, contract dates, regulatory classification,
4th-party disclosures) so the operator only sends the vendor
unanswered control questions, not blank templates.

Format catalogue (per ``QuestionnaireFormat`` enum):

- **``evidentia-generic``** — Apache 2.0 / Evidentia-original
  baseline questionnaire (~20 questions across FFIEC vendor-
  management domains: governance, access control, data handling,
  incident response, business continuity, 4th-party disclosure).
  Use when no specific industry framework is mandated; useful for
  internal ops + smaller vendors that don't warrant a full SIG.

- **``caiq-lite``** — CC BY 4.0 / CSA Consensus Assessments
  Initiative Questionnaire (CAIQ) v4.0.3 representative subset
  (~25 questions). Operators wanting the full 245-question CAIQ
  should download from <https://cloudsecurityalliance.org/research/cloud-controls-matrix/>
  and use the planned ``--from-template`` BYO ingestion path.
  Maps to NIST 800-53 + ISO 27001 + CSA CCM v4.

- **``sig``** / **``sig-lite``** — STUB. Shared Assessments
  paywalls the SIG question content (license terms forbid
  redistribution). Future versions will support a
  ``--from-template <path-to-licensed-xlsx>`` BYO-template
  pattern: operators with Shared Assessments membership supply
  their licensed XLSX, Evidentia pre-fills vendor metadata into
  the standard SIG layout, returns the partially-filled file for
  the vendor to complete. **In v0.7.9 P0.2 first slice these
  emit a clear "BYO-template not yet implemented" error.**

Output formats (per ``--output-format`` flag):

- **``json``** — full Pydantic model dump; machine-consumable
- **``csv``** — flat (one row per question); spreadsheet-friendly

XLSX output is deferred — would require an ``openpyxl`` extra
that brings ~3 MB of binary deps for the formatting machinery.
CSV is sufficient for the spreadsheet-pivot use case.

The ``ingest`` command (vendor responses flow back into Evidentia)
is also deferred to a follow-up sub-slice.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime
from enum import Enum
from importlib import resources
from typing import Any

from pydantic import Field

from evidentia_core.models.common import (
    EvidentiaModel,
    current_version,
    new_id,
    utc_now,
)
from evidentia_core.models.tprm import Vendor
from evidentia_core.tprm.concentration import _csv_safe


class QuestionnaireFormat(str, Enum):
    """Supported questionnaire framework formats.

    The free-text values map to packaged data files under
    `evidentia_core.tprm.data.questionnaires.<value>.json`. Three
    of the five values are SHIPPED (``evidentia-generic``,
    ``caiq-lite``); two are stubs (``sig``, ``sig-lite``) that
    document the future BYO-template path but error today.
    """

    EVIDENTIA_GENERIC = "evidentia-generic"
    CAIQ_LITE = "caiq-lite"
    SIG = "sig"
    SIG_LITE = "sig-lite"


# Format → data-file basename mapping. Stubs (sig/sig-lite) have
# no entry and raise NotImplementedError at generate time.
_PACKAGED_DATA_FORMATS: dict[QuestionnaireFormat, str] = {
    QuestionnaireFormat.EVIDENTIA_GENERIC: "evidentia_generic.json",
    QuestionnaireFormat.CAIQ_LITE: "caiq_lite.json",
}


class Question(EvidentiaModel):
    """One control question in a vendor due-diligence questionnaire."""

    id: str = Field(
        description=(
            "Stable per-format identifier. Format-prefixed (e.g., "
            "'EVG-GOV-01' for evidentia-generic governance question 1, "
            "'CAIQ-AAC-01' for CAIQ Audit Assurance & Compliance #1). "
            "Pinned so operator responses can flow back via the planned "
            "ingest command without column-order drift."
        )
    )
    domain: str = Field(
        description=(
            "Framework-specific control domain (e.g., 'Governance', "
            "'Access Control', 'Data Handling' for evidentia-generic; "
            "'AAC' (Audit Assurance & Compliance), 'BCR' (Business "
            "Continuity & Resilience) for CAIQ)."
        )
    )
    question_text: str = Field(
        description=(
            "Verbatim question presented to the vendor. Authoritative "
            "wording for caiq-lite per CSA CAIQ v4.0.3 publications "
            "(CC BY 4.0); Evidentia-original wording for "
            "evidentia-generic (Apache 2.0)."
        )
    )
    response_options: list[str] = Field(
        default_factory=list,
        description=(
            "Optional structured response choices (e.g., "
            "['Yes', 'No', 'Partial', 'Not Applicable']). Empty list "
            "= free-text response expected."
        ),
    )
    notes: str | None = Field(
        default=None,
        description=(
            "Optional clarifier surfaced to the vendor (e.g., 'Provide "
            "your most recent SOC 2 Type II report period covered')."
        ),
    )


class VendorPreFill(EvidentiaModel):
    """Pre-filled vendor metadata included in the questionnaire output.

    Operators DON'T want to ask the vendor 'what's your legal name?'
    when Evidentia already has it. This block carries the
    questionnaire-time snapshot of the vendor record so the receiving
    party sees the operator's understanding + can flag corrections.
    """

    vendor_id: str
    vendor_name: str
    vendor_type: str
    criticality_tier: str
    relationship_owner: str
    contract_start_date: date
    contract_end_date: date | None = None
    region: str | None = None
    regulatory_classification: list[str] = Field(default_factory=list)
    fourth_party_count: int = 0
    fourth_party_names: list[str] = Field(default_factory=list)


class Questionnaire(EvidentiaModel):
    """Generated vendor due-diligence questionnaire.

    Round-trip: serialise via ``model_dump_json(indent=2)`` to ship
    to the vendor as a structured doc; or render via
    :func:`render_csv_questionnaire` for spreadsheet workflows. The
    ``id`` field carries a UUID so a future ``dd-questionnaire ingest``
    command can correlate responses back to the originating
    questionnaire.
    """

    id: str = Field(default_factory=new_id)
    format: QuestionnaireFormat
    title: str = Field(
        description=(
            "Human-readable header — e.g., 'Evidentia Generic Vendor "
            "DD Questionnaire — <vendor name>'."
        )
    )
    generated_at: datetime = Field(default_factory=utc_now)
    vendor: VendorPreFill = Field(
        description="Snapshot of vendor metadata pre-filled into the questionnaire."
    )
    questions: list[Question] = Field(default_factory=list)
    licensing_attribution: str | None = Field(
        default=None,
        description=(
            "Format-specific attribution required by the source "
            "license (e.g., CSA CC BY 4.0 attribution for caiq-lite)."
        ),
    )
    evidentia_version: str = Field(default_factory=current_version)


# ── data loading ──────────────────────────────────────────────────


def _load_questionnaire_data(fmt: QuestionnaireFormat) -> dict[str, Any]:
    """Load packaged JSON data for a supported format.

    Raises :class:`NotImplementedError` for stub formats
    (``sig`` / ``sig-lite``) until the BYO-template path lands.
    """
    if fmt not in _PACKAGED_DATA_FORMATS:
        raise NotImplementedError(
            f"Questionnaire format {fmt.value!r} is not yet shipped. "
            "SIG / SIG-Lite require a Shared Assessments licensed "
            "template (paywalled content); future versions will "
            "support `--from-template <licensed-xlsx>` BYO ingestion. "
            f"Currently shipped formats: "
            f"{sorted(f.value for f in _PACKAGED_DATA_FORMATS)}."
        )
    fname = _PACKAGED_DATA_FORMATS[fmt]
    with resources.files(
        "evidentia_core.tprm.data.questionnaires"
    ).joinpath(fname).open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    return data  # type: ignore[no-any-return]


# ── prefill ───────────────────────────────────────────────────────


def _build_prefill(vendor: Vendor) -> VendorPreFill:
    """Project a Vendor into the questionnaire's prefill block."""
    return VendorPreFill(
        vendor_id=vendor.id,
        vendor_name=vendor.name,
        vendor_type=str(vendor.type),
        criticality_tier=str(vendor.criticality_tier),
        relationship_owner=vendor.relationship_owner,
        contract_start_date=vendor.contract_start_date,
        contract_end_date=vendor.contract_end_date,
        region=vendor.region,
        regulatory_classification=[
            str(c) for c in vendor.regulatory_classification
        ],
        fourth_party_count=len(vendor.fourth_parties),
        fourth_party_names=[fp.name for fp in vendor.fourth_parties],
    )


# ── core ──────────────────────────────────────────────────────────


def generate_questionnaire(
    vendor: Vendor,
    format: QuestionnaireFormat,
) -> Questionnaire:
    """Generate a due-diligence questionnaire for ``vendor`` in ``format``.

    Args:
        vendor: The vendor inventory record.
        format: One of the :class:`QuestionnaireFormat` values.

    Returns:
        A populated :class:`Questionnaire`.

    Raises:
        NotImplementedError: format is a stub (sig / sig-lite).
    """
    data = _load_questionnaire_data(format)
    questions = [Question.model_validate(q) for q in data["questions"]]
    title_template = data.get(
        "title_template", "Vendor DD Questionnaire — {vendor_name}"
    )
    # Use string `.replace()` rather than `.format(vendor_name=...)`
    # so a vendor name containing `{}` / `{0}` / `{secret}` cannot
    # raise KeyError at render time or, worse, leak adjacent format
    # args via positional/attribute walking. Closes v0.7.9 P0.3+P0.2
    # Continuous-review H-3 (defensive). The template comes from
    # packaged trusted JSON, so it itself can't be malicious — the
    # concern is just that vendor.name is user-supplied free-text.
    title = title_template.replace("{vendor_name}", vendor.name)
    return Questionnaire(
        format=format,
        title=title,
        vendor=_build_prefill(vendor),
        questions=questions,
        licensing_attribution=data.get("licensing_attribution"),
    )


# ── rendering ─────────────────────────────────────────────────────


def render_csv_questionnaire(q: Questionnaire) -> str:
    """Render a Questionnaire as flat CSV.

    Header row carries the prefill vendor metadata (one column per
    field) so the operator can confirm at a glance that the vendor
    they're asking matches their understanding. The question rows
    follow with columns: id / domain / question_text / response_options
    / notes / vendor_response (blank for the vendor to complete).
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    # Header section: vendor prefill as key/value comment lines.
    # Use a leading "#" sentinel so spreadsheet importers can filter
    # them out if desired; csv module handles arbitrary strings fine.
    # User-content cells go through _csv_safe to neutralize formula-
    # injection vectors (vendor name + 4th-party name + region etc.
    # are operator-supplied; the questionnaire CSV is explicitly
    # designed to be sent to the vendor, making formula injection
    # in those fields a real exfil/phish primitive). Closes v0.7.9
    # P0.2/P0.3 Continuous-review H-1 / security M-1.
    writer.writerow(["# Vendor DD Questionnaire"])
    writer.writerow(["# Title", _csv_safe(q.title)])
    writer.writerow(["# Questionnaire ID", q.id])
    writer.writerow(["# Format", str(q.format)])
    writer.writerow(["# Generated at", q.generated_at.isoformat()])
    writer.writerow(["# Vendor ID", q.vendor.vendor_id])
    writer.writerow(["# Vendor name", _csv_safe(q.vendor.vendor_name)])
    writer.writerow(["# Vendor type", q.vendor.vendor_type])
    writer.writerow(["# Criticality tier", q.vendor.criticality_tier])
    writer.writerow(
        ["# Relationship owner", _csv_safe(q.vendor.relationship_owner)]
    )
    writer.writerow(
        ["# Contract start", str(q.vendor.contract_start_date)]
    )
    if q.vendor.contract_end_date:
        writer.writerow(
            ["# Contract end", str(q.vendor.contract_end_date)]
        )
    if q.vendor.region:
        writer.writerow(["# Region", _csv_safe(q.vendor.region)])
    if q.vendor.regulatory_classification:
        writer.writerow(
            [
                "# Regulatory classification",
                _csv_safe(", ".join(q.vendor.regulatory_classification)),
            ]
        )
    if q.vendor.fourth_party_count:
        writer.writerow(
            [
                "# 4th parties",
                _csv_safe(
                    f"{q.vendor.fourth_party_count}: "
                    + ", ".join(q.vendor.fourth_party_names)
                ),
            ]
        )
    if q.licensing_attribution:
        writer.writerow(["# Attribution", q.licensing_attribution])
    writer.writerow([])  # blank separator row
    # Question rows. Question content (text + notes) comes from
    # packaged-data trusted JSON, but we _csv_safe it anyway as
    # defense-in-depth against future user-templated questions.
    writer.writerow(
        [
            "id",
            "domain",
            "question_text",
            "response_options",
            "notes",
            "vendor_response",
        ]
    )
    for question in q.questions:
        writer.writerow(
            [
                question.id,
                question.domain,
                _csv_safe(question.question_text),
                " | ".join(question.response_options),
                _csv_safe(question.notes) if question.notes else "",
                "",  # blank for vendor to fill
            ]
        )
    return buf.getvalue()


# ── catalogue ─────────────────────────────────────────────────────


def shipped_formats() -> list[QuestionnaireFormat]:
    """Return the sorted list of formats with packaged data.

    Used by CLI + REST help text to enumerate valid choices without
    hard-coding the stub-vs-shipped split in three places.
    """
    return sorted(_PACKAGED_DATA_FORMATS.keys(), key=lambda f: f.value)
