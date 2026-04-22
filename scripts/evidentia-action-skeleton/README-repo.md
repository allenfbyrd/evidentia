# evidentia-action

Reusable GitHub Action wrapping the [Evidentia](https://github.com/allenfbyrd/evidentia) CLI for PR-level **compliance-as-code**. Drop-in replacement for the [80-line workflow template](https://github.com/allenfbyrd/evidentia/blob/main/docs/github-action/workflow-example.yml):

```yaml
- uses: allenfbyrd/evidentia-action@v1
  with:
    inventory: my-controls.yaml
    frameworks: nist-800-53-rev5-moderate,soc2-tsc
    fail-on-regression: true
```

That's it. On every pull request the action:

1. Runs `evidentia gap analyze` on the PR branch's inventory
2. Runs the same analysis on the base branch
3. Computes a diff (opened / closed / severity-changed / unchanged)
4. Posts the markdown diff as a PR comment (updates in place on subsequent pushes)
5. Exits with status 1 if any new gaps opened or severities increased — blocking merge

No commercial GRC tool does this. Welcome to compliance-as-code.

## Inputs

| Input | Required | Default | Purpose |
|---|---|---|---|
| `inventory` | yes | — | Path to the control inventory file (YAML / JSON / CSV) |
| `frameworks` | yes | — | Comma-separated framework IDs (e.g. `nist-800-53-rev5-moderate,soc2-tsc`) |
| `base-ref` | no | PR base branch | Git ref to diff against |
| `fail-on-regression` | no | `true` | Exit 1 on regression (blocks merge) |
| `comment-tag` | no | `evidentia-gap-diff` | Marker for de-duplicating PR comments |
| `github-token` | no | `${{ github.token }}` | Token used to post PR comments |
| `evidentia-version` | no | `latest` | Pin to a specific Evidentia version |

## Outputs

| Output | Description |
|---|---|
| `gaps-opened` | Number of new gaps introduced |
| `gaps-closed` | Number of gaps closed |
| `severity-increased` | Number of gaps whose severity increased |
| `severity-decreased` | Number of gaps whose severity decreased |
| `is-regression` | `"true"` if any gap opened or severity increased |

## Example workflows

Drop into `.github/workflows/evidentia.yml`:

```yaml
name: Compliance Gap Analysis

on:
  pull_request:
    paths: ["my-controls.yaml"]

jobs:
  gap-analysis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: allenfbyrd/evidentia-action@v1
        with:
          inventory: my-controls.yaml
          frameworks: nist-800-53-rev5-moderate,soc2-tsc
          fail-on-regression: true
```

See [`examples/`](./examples/) for more patterns: multi-framework, matrix-per-environment, etc.

## Versioning

- `@v1` — floating pointer that tracks the latest non-breaking 1.x release. Recommended for most users.
- `@v1.0.0` — pinned to a specific release for reproducible builds.

Major version bumps are reserved for breaking input/output changes. Patch and minor versions update `v1` in place.

## Requirements

- The calling workflow needs `fetch-depth: 0` (or a specific base-ref checkout) so the action can compare against the base branch.
- The default `github-token` has the `issues: write` permission required for posting PR comments. If you use a custom token, grant it `issues: write`.

## License

Apache-2.0 — see [LICENSE](./LICENSE).
