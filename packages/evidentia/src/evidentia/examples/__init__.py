"""Bundled example data shipped with the ``evidentia`` package.

Currently holds ``sample-inventory.yaml`` — a small, runnable control
inventory so a fresh ``pip install evidentia`` user can execute the
quickstart with zero setup. Resolve it via ``importlib.resources``::

    from importlib.resources import files

    inventory = files("evidentia.examples") / "sample-inventory.yaml"

The file works against the bundled ``nist-800-53-rev5-moderate``
catalog out of the box; see the header comment inside it for the
schema and the full ``evidentia gap analyze`` invocation.
"""

from __future__ import annotations
