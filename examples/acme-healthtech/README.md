# Acme Healthtech — HIPAA-covered-entity example

**Fictional B2B2C telehealth platform** — 40K patients, 600 clinicians,
180 independent practices. All PHI processed in AWS HIPAA-eligible
services under BAA.

## Why this scenario exists

The Meridian fintech example primarily exercises NIST + SOC 2. This
Acme scenario showcases ControlBridge's **HIPAA-specific coverage**
and the cross-framework dynamics that emerge when all three HIPAA
rules (Security / Privacy / Breach Notification) are scoped together
with a NIST 800-53 overlay.

Particularly useful for showing:

- **Dotted-section control IDs** — HIPAA uses `164.312(a)(2)(iv)`
  style, which is a different normalization case than NIST's
  `AC-2(1)(a)` and works correctly with the v0.2.1 normalizer.
- **Multi-HIPAA-rule efficiency** — a single inventory entry like
  "we encrypt at rest with AES-256" satisfies `164.312(a)(2)(iv)`
  (Security Rule) AND `164.524` (Privacy — access integrity) AND
  partially `164.404` (Breach — encrypted data may qualify for
  safe-harbor). `controlbridge gap analyze` surfaces this as an
  efficiency opportunity.
- **Known-gap posture** — the inventory has an intentional
  `164.528 Accounting of Disclosures` gap (very common real-world
  HIPAA gap in smaller covered entities) so the gap report ranks it
  high-priority without anything contrived.

## Files

| File                   | Purpose                                                        |
| ---------------------- | -------------------------------------------------------------- |
| `controlbridge.yaml`   | v0.2.1 config, 4 frameworks                                    |
| `my-controls.yaml`     | ~34-control inventory, mixed implementation states             |
| `system-context.yaml`  | Telehealth-specific threat model + sub-processor map           |

## Quick start

```bash
cd examples/acme-healthtech

controlbridge gap analyze --inventory my-controls.yaml --output report.json
```

Expect cross-framework efficiency opportunities where one control
closes gaps in 3-4 frameworks simultaneously (notably on MFA,
encryption, and audit logging).

## LLM-powered "explain" on a HIPAA control

```bash
controlbridge explain control 164.312(d) --framework hipaa-security
```

The plain-English output makes the leap from "Person or Entity
Authentication" legalese to concrete guidance engineers can act on.
