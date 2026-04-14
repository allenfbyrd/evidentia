# Meridian Financial — ControlBridge Example

A realistic fintech sample designed to exercise every feature of ControlBridge.

## What's here

| File                   | Purpose                                                   |
| ---------------------- | --------------------------------------------------------- |
| `my-controls.yaml`     | Control inventory (20 controls, mixed states)             |
| `my-controls.csv`      | Same inventory in CSV form (for CSV parser testing)       |
| `system-context.yaml`  | System context for AI risk statement generation           |
| `controlbridge.yaml`   | Project configuration                                     |

## The scenario

**Meridian Financial** is a fictional consumer fintech SaaS serving 1.2M US
customers with savings, debit, and bill-pay products. It's in scope for PCI
DSS 4.0, GLBA, CCPA, SOC 2, and NYDFS Part 500. The 20-control inventory mixes:

- **11 fully implemented** — AC-2, AC-6, CM-2, IA-2, IA-5, SC-7, SC-13, SC-28,
  CC6.1, CC6.6, CC6.7
- **5 partially implemented** — AC-3, CM-6, IR-4, RA-5, SI-2
- **1 planned** — AU-2
- **3 not implemented** — AU-6, SI-4, CC7.1

The design ensures the gap report contains a realistic spread of CRITICAL,
HIGH, and MEDIUM severities and will surface efficiency opportunities where
a single NIST control closes gaps in multiple SOC 2 criteria.

## Quick start

```bash
cd examples/meridian-fintech

controlbridge gap analyze \
  --inventory my-controls.yaml \
  --frameworks nist-800-53-mod,soc2-tsc \
  --output report.json \
  --format json
```

See the top-level project walkthrough for the full command sequence.
