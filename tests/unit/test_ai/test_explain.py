"""Tests for the v0.3.0 plain-English explanation facility.

LLM calls are mocked — these tests exercise the cache semantics,
validation, and generator plumbing without actually hitting an LLM.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from controlbridge_ai.explain.cache import (
    _cache_key,
    clear_cache,
    get_cache_dir,
    load_cached,
    store,
)
from controlbridge_ai.explain.generator import ExplanationGenerator
from controlbridge_ai.explain.models import PlainEnglishExplanation
from controlbridge_core.models.catalog import CatalogControl


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path, monkeypatch):
    """Point the explanation cache at an isolated tmp dir per test."""
    cache = tmp_path / "cache"
    monkeypatch.setenv("CONTROLBRIDGE_EXPLAIN_CACHE_DIR", str(cache))
    yield cache


def _fake_explanation(
    framework_id: str = "nist-800-53-rev5",
    control_id: str = "AC-2",
    control_title: str = "Account Management",
) -> PlainEnglishExplanation:
    return PlainEnglishExplanation(
        framework_id=framework_id,
        control_id=control_id,
        control_title=control_title,
        plain_english=(
            "You need a documented process for creating, modifying, and "
            "removing user accounts across every system that matters."
        ),
        why_it_matters=(
            "Unmanaged accounts are a top attack vector — attackers "
            "frequently exploit former-employee credentials that were "
            "never cleaned up. A single dormant admin account with an "
            "unchanged password is a complete bypass of your IAM "
            "perimeter."
        ),
        what_to_do=[
            "Document a provisioning and deprovisioning procedure",
            "Perform quarterly access reviews with written approvals",
            "Configure automated account deactivation after 90 days inactive",
        ],
        effort_estimate=(
            "Medium — policy documentation plus quarterly review process. "
            "Add 2-4 weeks for orgs over 50 employees that need IAM tooling."
        ),
    )


def _fake_control(
    control_id: str = "AC-2", title: str = "Account Management"
) -> CatalogControl:
    return CatalogControl(
        id=control_id,
        title=title,
        description="The organization employs account management procedures...",
    )


# -----------------------------------------------------------------------------
# cache_key + cache directory resolution
# -----------------------------------------------------------------------------


def test_cache_key_is_deterministic() -> None:
    a = _cache_key("fw", "AC-2", "gpt-4o", 0.1)
    b = _cache_key("fw", "AC-2", "gpt-4o", 0.1)
    assert a == b


def test_cache_key_varies_by_model() -> None:
    a = _cache_key("fw", "AC-2", "gpt-4o", 0.1)
    b = _cache_key("fw", "AC-2", "claude-opus-4", 0.1)
    assert a != b


def test_cache_key_varies_by_temperature() -> None:
    a = _cache_key("fw", "AC-2", "gpt-4o", 0.0)
    b = _cache_key("fw", "AC-2", "gpt-4o", 0.2)
    assert a != b


def test_get_cache_dir_env_override(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CONTROLBRIDGE_EXPLAIN_CACHE_DIR", str(tmp_path))
    assert get_cache_dir() == tmp_path.resolve()


def test_get_cache_dir_explicit_override_wins(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CONTROLBRIDGE_EXPLAIN_CACHE_DIR", str(tmp_path / "env"))
    explicit = tmp_path / "explicit"
    assert get_cache_dir(explicit) == explicit.resolve()


# -----------------------------------------------------------------------------
# load/store roundtrip
# -----------------------------------------------------------------------------


def test_store_then_load_roundtrip() -> None:
    exp = _fake_explanation()
    store(exp, model="gpt-4o", temperature=0.1)
    loaded = load_cached("nist-800-53-rev5", "AC-2", "gpt-4o", 0.1)
    assert loaded is not None
    assert loaded.control_id == "AC-2"
    assert loaded.plain_english == exp.plain_english


def test_load_returns_none_when_missing() -> None:
    assert load_cached("fw", "unseen-control", "gpt-4o", 0.1) is None


def test_cache_miss_on_different_model() -> None:
    exp = _fake_explanation()
    store(exp, model="gpt-4o", temperature=0.1)
    assert (
        load_cached("nist-800-53-rev5", "AC-2", "claude-opus-4", 0.1) is None
    )


def test_corrupt_cache_file_returns_none(tmp_path: Path) -> None:
    """A malformed JSON file in the cache doesn't crash — it's just ignored."""
    cache_path = get_cache_dir() / f"{_cache_key('fw', 'AC-2', 'gpt-4o', 0.1)}.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text("not valid json")
    assert load_cached("fw", "AC-2", "gpt-4o", 0.1) is None


def test_clear_cache_empties_dir() -> None:
    for ctrl_id in ["AC-2", "AC-3", "AU-2"]:
        store(_fake_explanation(control_id=ctrl_id), "gpt-4o", 0.1)
    n = clear_cache()
    assert n == 3
    assert load_cached("nist-800-53-rev5", "AC-2", "gpt-4o", 0.1) is None


def test_clear_cache_on_missing_dir_returns_zero(tmp_path: Path) -> None:
    missing = tmp_path / "never-created"
    # Use explicit override so we don't race with the autouse fixture
    assert clear_cache(missing) == 0


# -----------------------------------------------------------------------------
# ExplanationGenerator — cache hit avoids LLM call
# -----------------------------------------------------------------------------


def test_generator_cache_hit_skips_llm() -> None:
    """If an explanation is already cached, generate() returns it without LLM calls."""
    # Pre-populate the cache for (nist-800-53-rev5, AC-2, gpt-4o, 0.1)
    store(_fake_explanation(), model="gpt-4o", temperature=0.1)

    with patch(
        "controlbridge_ai.explain.generator.get_instructor_client"
    ) as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        gen = ExplanationGenerator(model="gpt-4o", temperature=0.1)
        result = gen.generate(_fake_control(), framework_id="nist-800-53-rev5")
        # Cache hit — the LLM must not have been called
        mock_client.chat.completions.create.assert_not_called()
    assert result.control_id == "AC-2"


def test_generator_cache_miss_calls_llm_and_caches() -> None:
    with patch(
        "controlbridge_ai.explain.generator.get_instructor_client"
    ) as mock_client_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _fake_explanation()
        mock_client_factory.return_value = mock_client
        gen = ExplanationGenerator(model="gpt-4o", temperature=0.1)
        gen.generate(_fake_control(), framework_id="nist-800-53-rev5")
        mock_client.chat.completions.create.assert_called_once()
    # Subsequent call with the same key should hit the cache now
    assert load_cached("nist-800-53-rev5", "AC-2", "gpt-4o", 0.1) is not None


def test_generator_refresh_bypasses_cache() -> None:
    store(_fake_explanation(), model="gpt-4o", temperature=0.1)
    with patch(
        "controlbridge_ai.explain.generator.get_instructor_client"
    ) as mock_client_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _fake_explanation()
        mock_client_factory.return_value = mock_client
        gen = ExplanationGenerator(model="gpt-4o", temperature=0.1)
        gen.generate(
            _fake_control(), framework_id="nist-800-53-rev5", refresh=True
        )
        mock_client.chat.completions.create.assert_called_once()


def test_generator_use_cache_false_bypasses_both_read_and_write() -> None:
    with patch(
        "controlbridge_ai.explain.generator.get_instructor_client"
    ) as mock_client_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _fake_explanation()
        mock_client_factory.return_value = mock_client
        gen = ExplanationGenerator(
            model="gpt-4o", temperature=0.1, use_cache=False
        )
        gen.generate(_fake_control(), framework_id="nist-800-53-rev5")
    # Nothing written to cache
    assert load_cached("nist-800-53-rev5", "AC-2", "gpt-4o", 0.1) is None


def test_generator_echoes_framework_and_control_ids_even_if_llm_drifts() -> None:
    """Defensive: if the LLM returns mismatched echo fields, we overwrite them."""
    llm_output = _fake_explanation(
        framework_id="wrong-fw",
        control_id="WRONG-ID",
        control_title="Wrong title",
    )
    with patch(
        "controlbridge_ai.explain.generator.get_instructor_client"
    ) as mock_client_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = llm_output
        mock_client_factory.return_value = mock_client
        gen = ExplanationGenerator(
            model="gpt-4o", temperature=0.1, use_cache=False
        )
        result = gen.generate(
            _fake_control(control_id="AC-2", title="Account Management"),
            framework_id="nist-800-53-rev5",
        )
    assert result.framework_id == "nist-800-53-rev5"
    assert result.control_id == "AC-2"
    assert result.control_title == "Account Management"


# -----------------------------------------------------------------------------
# PlainEnglishExplanation schema validation
# -----------------------------------------------------------------------------


def test_explanation_model_rejects_too_few_steps() -> None:
    """what_to_do must have 3-8 bullets."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):  # pydantic ValidationError
        PlainEnglishExplanation(
            framework_id="fw",
            control_id="AC-2",
            control_title="Account Management",
            plain_english="A" * 50,
            why_it_matters="B" * 100,
            what_to_do=["only one"],  # too few
            effort_estimate="C" * 30,
        )


def test_explanation_model_rejects_short_plain_english() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PlainEnglishExplanation(
            framework_id="fw",
            control_id="AC-2",
            control_title="Account Management",
            plain_english="too short",  # min 40 chars
            why_it_matters="B" * 100,
            what_to_do=["a", "b", "c"],
            effort_estimate="C" * 30,
        )


def test_explanation_model_rejects_extra_fields() -> None:
    """Strict schema (extra='forbid') — unknown keys from a drifting LLM fail."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PlainEnglishExplanation.model_validate(
            {
                "framework_id": "fw",
                "control_id": "AC-2",
                "control_title": "Account Management",
                "plain_english": "A" * 50,
                "why_it_matters": "B" * 100,
                "what_to_do": ["a", "b", "c"],
                "effort_estimate": "C" * 30,
                "invented_field": "should fail",
            }
        )
