"""Tests for the bundled framework manifest (catalogs/manifest.py)."""

from __future__ import annotations

import pytest
from evidentia_core.catalogs.manifest import (
    MANIFEST_PATH,
    FrameworkManifest,
    FrameworkManifestEntry,
    load_manifest,
)


def test_bundled_manifest_loads() -> None:
    """The shipped manifest.yaml parses into a valid FrameworkManifest."""
    manifest = load_manifest()
    assert isinstance(manifest, FrameworkManifest)
    assert manifest.version == 1
    assert len(manifest.frameworks) >= 2  # at minimum our two v0.1.x frameworks


def test_bundled_manifest_includes_nist_and_soc2() -> None:
    manifest = load_manifest()
    ids = {fw.id for fw in manifest.frameworks}
    assert "nist-800-53-mod" in ids
    assert "soc2-tsc" in ids


def test_manifest_tier_filter() -> None:
    manifest = load_manifest()
    tier_a = manifest.by_tier("A")
    tier_c = manifest.by_tier("C")
    assert any(fw.id == "nist-800-53-mod" for fw in tier_a)
    assert any(fw.id == "soc2-tsc" for fw in tier_c)


def test_manifest_get_by_id() -> None:
    manifest = load_manifest()
    nist = manifest.get("nist-800-53-mod")
    assert nist is not None
    assert nist.tier == "A"
    assert nist.path.endswith(".json")
    assert manifest.get("not-a-real-framework") is None


def test_soc2_tsc_entry_is_licensed_stub() -> None:
    """The SOC 2 stub must advertise its license and placeholder status."""
    manifest = load_manifest()
    soc2 = manifest.get("soc2-tsc")
    assert soc2 is not None
    assert soc2.tier == "C"
    assert soc2.license_required is True
    assert soc2.placeholder is True
    assert soc2.license_url is not None
    assert "aicpa" in soc2.license_url.lower()


def test_manifest_duplicate_id_raises(tmp_path) -> None:
    """Manifest with duplicate framework IDs must fail to load."""
    import yaml

    path = tmp_path / "frameworks.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "frameworks": [
                    {
                        "id": "fw-a",
                        "name": "Framework A",
                        "version": "1.0",
                        "tier": "A",
                        "category": "control",
                        "path": "a.json",
                    },
                    {
                        "id": "fw-a",
                        "name": "Framework A (duplicate)",
                        "version": "1.0",
                        "tier": "A",
                        "category": "control",
                        "path": "a2.json",
                    },
                ],
            }
        )
    )
    # Cache is per-path, so a fresh path isn't cached yet
    with pytest.raises(ValueError, match="Duplicate framework IDs"):
        load_manifest(path)


def test_bundled_manifest_path_constant() -> None:
    """MANIFEST_PATH points at a real file inside the installed package."""
    assert MANIFEST_PATH.exists()
    assert MANIFEST_PATH.suffix == ".yaml"


def test_manifest_entry_forbids_extra_fields() -> None:
    """Extra fields in a manifest entry are rejected."""
    with pytest.raises(ValueError):
        FrameworkManifestEntry(
            id="x",
            name="x",
            version="1.0",
            tier="A",
            category="control",
            path="x.json",
            bogus_field="should-fail",  # type: ignore[call-arg]
        )
