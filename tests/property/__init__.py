"""v0.8.2 G2: hypothesis property-based tests.

Property-based tests complement the hand-written test suite by
generating randomized inputs against canonical invariants. They
catch regressions where the unit-test corpus didn't anticipate
a specific input shape.

Test modules:

- :mod:`tests.property.test_normalizer` — invariants on the
  control-id normalizer (idempotence, uppercase output,
  prefix-stripping coverage).
- :mod:`tests.property.test_crosswalk` — invariants on the
  catalogs CrosswalkEngine (empty-engine emptiness, case-
  insensitive lookup, return-shape consistency).

Configuration is via the ``[tool.hypothesis]`` block in the
root ``pyproject.toml``: ``derandomize=True`` keeps CI runs
reproducible across machines + ``deadline=200ms`` per example
keeps the suite fast.
"""
