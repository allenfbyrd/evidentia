"""Tests for the v0.6.0 controlbridge-* -> evidentia-* rename shim packages.

The shims live in packages/shim-controlbridge*/ and are published at
v0.5.1 to keep pre-rename `pip install controlbridge-*` consumers working
through v0.7.0. Each shim:

1. Emits a DeprecationWarning on import.
2. Inherits the replacement package's __version__.
3. Aliases every submodule so deep imports like
   `from controlbridge_core.models.common import EvidentiaModel` resolve
   to the same object as the equivalent `evidentia_core` import.
4. For the CLI package, the `controlbridge.cli.main.app` entry point
   points at the same Typer app object as `evidentia.cli.main.app`.

These tests guard against regressions in any of those guarantees until
the shim packages are yanked in v0.7.0.
"""

from __future__ import annotations

import importlib
import sys
import warnings

import pytest

SHIM_PAIRS: list[tuple[str, str]] = [
    ("controlbridge", "evidentia"),
    ("controlbridge_core", "evidentia_core"),
    ("controlbridge_ai", "evidentia_ai"),
    ("controlbridge_api", "evidentia_api"),
    ("controlbridge_collectors", "evidentia_collectors"),
    ("controlbridge_integrations", "evidentia_integrations"),
]


@pytest.fixture(autouse=True)
def _reset_shim_cache(monkeypatch):
    """Drop cached shim modules so each test re-triggers the import warning."""
    for old, _ in SHIM_PAIRS:
        for mod in list(sys.modules):
            if mod == old or mod.startswith(f"{old}."):
                monkeypatch.delitem(sys.modules, mod, raising=False)
    yield


@pytest.mark.parametrize("old_name,new_name", SHIM_PAIRS)
def test_shim_emits_deprecation_warning(old_name: str, new_name: str) -> None:
    """Importing any shim package must emit a DeprecationWarning."""
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        importlib.import_module(old_name)
    deprecations = [w for w in captured if issubclass(w.category, DeprecationWarning)]
    assert deprecations, f"{old_name} shim did not emit DeprecationWarning"
    msg = str(deprecations[0].message)
    assert new_name.replace("_", "-") in msg or new_name in msg, (
        f"{old_name} shim warning must mention the replacement name"
    )


@pytest.mark.parametrize("old_name,new_name", SHIM_PAIRS)
def test_shim_version_matches_replacement(old_name: str, new_name: str) -> None:
    """The shim's __version__ is inherited from the replacement package."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        old_mod = importlib.import_module(old_name)
        new_mod = importlib.import_module(new_name)
    assert old_mod.__version__ == new_mod.__version__


def test_controlbridge_core_models_submodule_aliased() -> None:
    """Top-level `controlbridge_core.models` submodule access works."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        import controlbridge_core
        import evidentia_core
    assert controlbridge_core.models is evidentia_core.models


def test_controlbridge_core_deep_submodule_alias() -> None:
    """Deep imports like `from controlbridge_core.models.common import X` work."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from controlbridge_core.models.common import EvidentiaModel as CBModel
        from evidentia_core.models.common import EvidentiaModel as EvModel
    assert CBModel is EvModel


def test_controlbridge_api_router_alias() -> None:
    """Nested subpackage imports work: `controlbridge_api.routers.gaps`."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from controlbridge_api.routers import gaps as cb_gaps
        from evidentia_api.routers import gaps as ev_gaps
    assert cb_gaps is ev_gaps


def test_controlbridge_cli_entry_point_aliased() -> None:
    """The legacy `controlbridge` CLI entry point resolves to evidentia's app."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from controlbridge.cli.main import app as cb_app
        from evidentia.cli.main import app as ev_app
    assert cb_app is ev_app
