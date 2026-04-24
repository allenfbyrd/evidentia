"""Schema migration helpers (v0.7.0).

Supports reading evidence JSON written by earlier Evidentia versions
without forcing operators to re-collect everything. Each migration
module handles one hop (e.g., v0.6 → v0.7) and logs a WARN event when
it synthesizes missing fields so auditors see which evidence predates
the enterprise-grade provenance model.
"""
