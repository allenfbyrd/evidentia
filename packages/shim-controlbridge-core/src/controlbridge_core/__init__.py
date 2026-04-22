"""DEPRECATED — controlbridge-core has been renamed to evidentia-core.

This transitional shim re-exports everything from `evidentia_core` and aliases
every submodule into `controlbridge_core.*` via `sys.modules`, so pre-rename imports
like `from controlbridge_core.submodule import Foo` continue to work.

The shim will be removed in v0.7.0 (~6 months after v0.6.0 ships).

Migration:
    pip install evidentia-core

Then rewrite `controlbridge_core` to `evidentia_core` in your imports.
"""

from __future__ import annotations

import importlib as _importlib
import pkgutil as _pkgutil
import sys as _sys
import warnings as _warnings

_OLD_PYPI = "controlbridge-core"
_NEW_PYPI = "evidentia-core"
_OLD_MODULE = "controlbridge_core"
_NEW_MODULE = "evidentia_core"

_warnings.warn(
    f"'{_OLD_PYPI}' has been renamed to '{_NEW_PYPI}' to resolve a naming "
    "collision with an unrelated commercial product. Install the replacement "
    f"with `pip install {_NEW_PYPI}` and update imports from "
    f"`{_OLD_MODULE}` to `{_NEW_MODULE}`. This shim will be removed in "
    "v0.7.0. See https://github.com/allenfbyrd/evidentia/blob/main/CHANGELOG.md",
    DeprecationWarning,
    stacklevel=2,
)

_new_pkg = _importlib.import_module(_NEW_MODULE)

# Walk the new package's submodule tree FIRST so every `foo.bar.baz` module
# is present in `sys.modules` and attached as an attribute of its parent.
# We then register each submodule under the old name (both in `sys.modules`
# for import-machinery lookups AND as an attribute of the appropriate
# aliased parent module for attribute-access lookups — Python does NOT
# fall through to `sys.modules` when resolving `pkg.sub` via `.` access).
if hasattr(_new_pkg, "__path__"):
    for _info in _pkgutil.walk_packages(_new_pkg.__path__, prefix=f"{_NEW_MODULE}."):
        try:
            _mod = _importlib.import_module(_info.name)
        except ImportError:
            # Optional extras-gated submodules may fail without the extra
            # installed — safe to skip; the user will get the same
            # ImportError if they try to use that submodule directly.
            continue
        _aliased = _info.name.replace(_NEW_MODULE, _OLD_MODULE, 1)
        _sys.modules[_aliased] = _mod

# Re-export EVERY top-level public attribute the new package exposes, now
# that submodule imports above have populated `evidentia_*`'s namespace.
for _attr in dir(_new_pkg):
    if not _attr.startswith("_"):
        globals()[_attr] = getattr(_new_pkg, _attr)

# Preserve `__version__` (the no-underscore filter above drops dunders).
if hasattr(_new_pkg, "__version__"):
    __version__ = _new_pkg.__version__
