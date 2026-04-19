# Northstar Systems — DoD contractor CMMC L2 example

**Fictional DoD sub-contractor** — 85 employees, CUI-handling scope,
AWS GovCloud only, CMMC 2.0 Level 2 required by contract.

## Why this scenario exists

DoD contracting is a distinct compliance world: the combination of
CMMC + NIST 800-171 + DFARS clauses is rarely exercised by
commercial GRC tools. This example showcases:

- **CMMC Level 2 coverage** — all 110 practices align with NIST
  800-171 Rev 2, so a single inventory entry can satisfy both.
  `controlbridge gap analyze` surfaces this as cross-framework
  efficiency.
- **CMMC-specific control IDs** — `CMMC.L2-3.1.1` style, distinct
  from NIST publication style (`3.1.1`) and NIST-OSCAL style. The
  inventory exercises both `CMMC.L2-3.X.X` and `3.X.X` IDs side by
  side.
- **Intentional DIBCAC-style gaps** — SIEM correlation missing
  (`CMMC.L2-3.3.5` / `3.3.5`), incident-response test cadence
  weak. These are common real-world CMMC assessment findings.

## Files

| File                   | Purpose                                    |
| ---------------------- | ------------------------------------------ |
| `controlbridge.yaml`   | 2-framework scope (CMMC L2 + 800-171 r2)   |
| `my-controls.yaml`     | ~30-control inventory                      |
| `system-context.yaml`  | GovCloud + CUI + DFARS threat model        |

## Quick start

```bash
cd examples/dod-contractor

controlbridge gap analyze --inventory my-controls.yaml --output report.json

# Explain a CMMC control in plain English
controlbridge explain control CMMC.L2-3.3.5 --framework cmmc-2-l2
```

## Cross-framework efficiency

Because CMMC L2 and NIST 800-171 Rev 2 are near-identical in coverage,
the gap analyzer produces a large set of efficiency opportunities
where a single remediation closes gaps in both frameworks. Look for
the "efficiency_opportunities" array in the exported JSON report.
