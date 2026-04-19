# controlbridge-action (skeleton)

This directory holds the **source files** for the separate
`allenfbyrd/controlbridge-action` GitHub Actions repository. It is
checked into the ControlBridge monorepo for review convenience only —
at publish time, these files get moved to their own repo.

## Publishing to a separate repo

```bash
# From the ControlBridge repo root
SKELETON="$(pwd)/scripts/controlbridge-action-skeleton"

# Create a new repo under your GitHub account
gh repo create allenfbyrd/controlbridge-action --public \
  --description "Reusable GitHub Action wrapping the ControlBridge CLI for PR-level compliance-as-code."

# Clone it locally
cd /tmp
gh repo clone allenfbyrd/controlbridge-action
cd controlbridge-action

# Copy the skeleton files
cp -r "$SKELETON"/. .

# Commit + push
git add .
git commit -m "Initial commit: controlbridge-action v1.0.0"
git push -u origin main

# Tag v1.0.0 + floating v1 pointer
git tag -a v1.0.0 -m "v1.0.0 — reusable wrapper for ControlBridge v0.4.0 CLI"
git tag -a v1 -m "Floating v1 pointer"
git push origin v1.0.0 v1

# Submit to GitHub Actions Marketplace via the repo's Settings → Actions → "Publish to Marketplace"
gh release create v1.0.0 --title "v1.0.0 — reusable ControlBridge GitHub Action"
```

## What's in this skeleton

- `action.yml` — composite action definition. Consumers reference it as
  `uses: allenfbyrd/controlbridge-action@v1`.
- `README.md` (lands at repo root) — usage examples, input/output reference.
- `LICENSE` — Apache-2.0, matching the main ControlBridge repo.
- `examples/` — sample consumer workflows for common scenarios:
  - `basic.yml` — minimal single-framework gap analysis + fail-on-regression
  - `multi-framework.yml` — several frameworks with matrix strategy
  - `matrix.yml` — per-environment (staging, prod) checks

## Keeping the skeleton in sync with the shipped repo

When you make changes to `scripts/controlbridge-action-skeleton/` in the
main ControlBridge repo, propagate them to `allenfbyrd/controlbridge-action`
with the same `cp -r` dance, then tag + push a new version. The
floating `v1` tag gets force-updated so existing consumers
(`uses: allenfbyrd/controlbridge-action@v1`) pick up the change.

Major-version bumps (`v2`) are reserved for breaking changes to the
action's input/output interface. Patch-level fixes stay on `v1`.
