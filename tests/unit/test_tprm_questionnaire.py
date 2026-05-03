"""Unit tests for evidentia_core.tprm.questionnaire (v0.7.9 P0.2)."""

from __future__ import annotations

from datetime import date

import pytest
from evidentia_core.models.tprm import (
    CriticalityTier,
    FourthParty,
    RegulatoryClassification,
    Vendor,
    VendorType,
)
from evidentia_core.tprm.questionnaire import (
    Questionnaire,
    QuestionnaireFormat,
    generate_questionnaire,
    render_csv_questionnaire,
    shipped_formats,
)


def _make_vendor(
    name: str = "Acme Cloud",
    type_: VendorType = VendorType.SAAS,
    criticality_tier: CriticalityTier = CriticalityTier.HIGH,
    region: str | None = "us-east-1",
    fourth_parties: list[FourthParty] | None = None,
    regulatory_classification: list[RegulatoryClassification] | None = None,
) -> Vendor:
    return Vendor(
        name=name,
        type=type_,
        criticality_tier=criticality_tier,
        relationship_owner="x@x.com",
        contract_start_date=date(2025, 1, 1),
        region=region,
        fourth_parties=fourth_parties or [],
        regulatory_classification=regulatory_classification or [],
    )


# ── shipped_formats helper ─────────────────────────────────────────


class TestShippedFormats:
    def test_returns_two_formats(self) -> None:
        formats = shipped_formats()
        # caiq-lite + evidentia-generic shipped today; sig + sig-lite are stubs
        assert QuestionnaireFormat.CAIQ_LITE in formats
        assert QuestionnaireFormat.EVIDENTIA_GENERIC in formats
        assert QuestionnaireFormat.SIG not in formats
        assert QuestionnaireFormat.SIG_LITE not in formats


# ── generate happy path ────────────────────────────────────────────


class TestGenerateQuestionnaire:
    def test_evidentia_generic_loads(self) -> None:
        v = _make_vendor()
        q = generate_questionnaire(v, QuestionnaireFormat.EVIDENTIA_GENERIC)
        assert q.format == QuestionnaireFormat.EVIDENTIA_GENERIC.value
        assert "Evidentia Generic" in q.title
        assert q.vendor.vendor_name == "Acme Cloud"
        assert q.vendor.region == "us-east-1"
        assert len(q.questions) >= 15  # ~20 questions ship today
        # Each question carries id + domain + question_text
        for question in q.questions:
            assert question.id
            assert question.domain
            assert question.question_text

    def test_caiq_lite_loads_with_attribution(self) -> None:
        v = _make_vendor()
        q = generate_questionnaire(v, QuestionnaireFormat.CAIQ_LITE)
        assert q.format == QuestionnaireFormat.CAIQ_LITE.value
        assert "CAIQ" in q.title
        # CSA CC BY 4.0 attribution required by the source license
        assert q.licensing_attribution is not None
        assert "CSA" in q.licensing_attribution or "Cloud Security Alliance" in q.licensing_attribution
        assert "CC BY 4.0" in q.licensing_attribution
        assert len(q.questions) >= 20

    def test_evidentia_generic_no_attribution(self) -> None:
        # Apache-2.0 / no third-party license; no required attribution
        v = _make_vendor()
        q = generate_questionnaire(v, QuestionnaireFormat.EVIDENTIA_GENERIC)
        assert q.licensing_attribution is None

    def test_sig_format_raises_not_implemented(self) -> None:
        v = _make_vendor()
        with pytest.raises(NotImplementedError, match="paywalled"):
            generate_questionnaire(v, QuestionnaireFormat.SIG)

    def test_sig_lite_format_raises_not_implemented(self) -> None:
        v = _make_vendor()
        with pytest.raises(NotImplementedError, match="paywalled"):
            generate_questionnaire(v, QuestionnaireFormat.SIG_LITE)


# ── prefill projection ────────────────────────────────────────────


class TestVendorPreFill:
    def test_prefill_carries_4th_parties(self) -> None:
        v = _make_vendor(
            fourth_parties=[
                FourthParty(
                    name="AWS",
                    type=VendorType.CLOUD_PROVIDER,
                    relationship="iaas",
                ),
                FourthParty(
                    name="Stripe",
                    type=VendorType.SAAS,
                    relationship="payments",
                ),
            ],
        )
        q = generate_questionnaire(
            v, QuestionnaireFormat.EVIDENTIA_GENERIC
        )
        assert q.vendor.fourth_party_count == 2
        assert "AWS" in q.vendor.fourth_party_names
        assert "Stripe" in q.vendor.fourth_party_names

    def test_prefill_carries_regulatory_classification(self) -> None:
        v = _make_vendor(
            regulatory_classification=[
                RegulatoryClassification.MODEL,
                RegulatoryClassification.CRITICAL_THIRD_PARTY,
            ],
        )
        q = generate_questionnaire(
            v, QuestionnaireFormat.EVIDENTIA_GENERIC
        )
        assert (
            RegulatoryClassification.MODEL.value
            in q.vendor.regulatory_classification
        )
        assert (
            RegulatoryClassification.CRITICAL_THIRD_PARTY.value
            in q.vendor.regulatory_classification
        )

    def test_prefill_handles_no_region(self) -> None:
        v = _make_vendor(region=None)
        q = generate_questionnaire(
            v, QuestionnaireFormat.EVIDENTIA_GENERIC
        )
        assert q.vendor.region is None

    def test_prefill_handles_indefinite_contract(self) -> None:
        v = _make_vendor()
        # contract_end_date defaults to None
        q = generate_questionnaire(
            v, QuestionnaireFormat.EVIDENTIA_GENERIC
        )
        assert q.vendor.contract_end_date is None


# ── data-file integrity ───────────────────────────────────────────


class TestDataFileIntegrity:
    """Catch data-file regressions: missing keys, dupe IDs, etc."""

    @pytest.mark.parametrize(
        "fmt",
        [
            QuestionnaireFormat.EVIDENTIA_GENERIC,
            QuestionnaireFormat.CAIQ_LITE,
        ],
    )
    def test_question_ids_unique(self, fmt: QuestionnaireFormat) -> None:
        v = _make_vendor()
        q = generate_questionnaire(v, fmt)
        ids = [question.id for question in q.questions]
        assert len(ids) == len(set(ids)), (
            f"Duplicate question IDs in {fmt.value}: "
            f"{[i for i in set(ids) if ids.count(i) > 1]}"
        )

    @pytest.mark.parametrize(
        "fmt",
        [
            QuestionnaireFormat.EVIDENTIA_GENERIC,
            QuestionnaireFormat.CAIQ_LITE,
        ],
    )
    def test_all_questions_carry_required_fields(
        self, fmt: QuestionnaireFormat
    ) -> None:
        v = _make_vendor()
        q = generate_questionnaire(v, fmt)
        for question in q.questions:
            assert question.id
            assert question.domain
            assert question.question_text
            assert isinstance(question.response_options, list)


# ── CSV rendering ──────────────────────────────────────────────────


class TestRenderCsvQuestionnaire:
    def test_csv_includes_prefill_header_section(self) -> None:
        v = _make_vendor(
            fourth_parties=[
                FourthParty(
                    name="AWS",
                    type=VendorType.CLOUD_PROVIDER,
                    relationship="iaas",
                ),
            ],
        )
        q = generate_questionnaire(
            v, QuestionnaireFormat.EVIDENTIA_GENERIC
        )
        csv_str = render_csv_questionnaire(q)
        # Header section uses # comment-prefixed lines for vendor metadata
        assert "# Vendor DD Questionnaire" in csv_str
        assert "# Vendor name" in csv_str
        assert "Acme Cloud" in csv_str
        # 4th-party block
        assert "# 4th parties" in csv_str
        assert "AWS" in csv_str

    def test_csv_includes_question_rows_with_blank_response(self) -> None:
        v = _make_vendor()
        q = generate_questionnaire(
            v, QuestionnaireFormat.EVIDENTIA_GENERIC
        )
        csv_str = render_csv_questionnaire(q)
        # Header row for question columns
        assert (
            "id,domain,question_text,response_options,notes,vendor_response"
            in csv_str
        )
        # Last column should be blank for vendor to fill
        # (every question row ends with the empty vendor_response cell)
        for line in csv_str.split("\n"):
            if line.startswith("EVG-"):
                # Quick sanity: line ends in trailing comma + nothing
                # (csv.writer emits empty-string cells as bare commas)
                assert line.rstrip("\r").endswith(",")

    def test_csv_includes_caiq_attribution(self) -> None:
        v = _make_vendor()
        q = generate_questionnaire(v, QuestionnaireFormat.CAIQ_LITE)
        csv_str = render_csv_questionnaire(q)
        assert "# Attribution" in csv_str
        assert "CSA" in csv_str or "Cloud Security Alliance" in csv_str


# ── JSON round-trip ────────────────────────────────────────────────


class TestQuestionnaireJsonRoundTrip:
    def test_round_trip(self) -> None:
        v = _make_vendor()
        q = generate_questionnaire(
            v, QuestionnaireFormat.EVIDENTIA_GENERIC
        )
        data = q.model_dump(mode="json")
        restored = Questionnaire.model_validate(data)
        assert restored.id == q.id
        assert restored.format == q.format
        assert len(restored.questions) == len(q.questions)
        assert restored.vendor.vendor_name == q.vendor.vendor_name
