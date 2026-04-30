"""Security primitives shared across the Evidentia stack.

The package collects defensive-coding helpers that protect Evidentia's
trust boundaries. Today this is a single module — :mod:`paths` — that
wraps the standard ``pathlib`` resolution dance behind a single
predicate so call sites at API + CLI + collector boundaries can reject
directory-traversal attempts uniformly.

Future modules in this package may include input-sanitization helpers
for other surfaces (URL hosts, regex sources, archive extraction
entries, etc.). The package import keeps the namespace small;
prefer ``from evidentia_core.security.paths import validate_within``
over deep aliasing through this ``__init__``.
"""

from evidentia_core.security.paths import (
    PathTraversalError,
    validate_within,
)

__all__ = [
    "PathTraversalError",
    "validate_within",
]
