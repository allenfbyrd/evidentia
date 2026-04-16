"""Tests that FrameworkId access triggers DeprecationWarning (v0.2.0)."""

from __future__ import annotations

import warnings


def test_framework_id_import_warns() -> None:
    """Importing FrameworkId from common.py triggers DeprecationWarning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        # Fresh import path — use module-level __getattr__ via dotted access
        from controlbridge_core.models import common

        _ = common.FrameworkId  # triggers __getattr__
    deprecation_warnings = [
        w for w in caught if issubclass(w.category, DeprecationWarning)
    ]
    assert deprecation_warnings, "Accessing FrameworkId should warn"
    assert any(
        "FrameworkId is deprecated" in str(w.message) for w in deprecation_warnings
    )


def test_framework_id_still_works() -> None:
    """Despite the deprecation, the enum still functions."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from controlbridge_core.models.common import FrameworkId

        assert FrameworkId.NIST_800_53_MOD.value == "nist-800-53-mod"
        assert FrameworkId.SOC2_TSC.value == "soc2-tsc"


def test_base_models_import_does_not_warn() -> None:
    """Base model imports must not trigger DeprecationWarning.

    Regression guard: early implementations fired the warning on
    ``from controlbridge_core.models import ControlBridgeModel`` because
    FrameworkId was bound at package scope. The warning should only
    fire on explicit attribute access.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        from controlbridge_core.models import (  # noqa: F401
            CatalogControl,
            ControlBridgeModel,
            Severity,
        )
    deprecation_warnings = [
        w for w in caught if issubclass(w.category, DeprecationWarning)
    ]
    assert not deprecation_warnings, (
        "Base model imports should not emit DeprecationWarning, got: "
        f"{[str(w.message) for w in deprecation_warnings]}"
    )
