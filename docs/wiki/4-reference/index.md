# 4. Reference

Look up CLI verbs, MCP tools, API symbols, configuration options, and bundled catalog + crosswalk listings.

## Pages in this section

Every page below is **auto-generated from the live codebase / data** by
`scripts/wiki/sync_reference.py` (the 5 reference pages) and
`scripts/wiki/sync_api_docs.py` (the 7 API pages). Each carries a "do not edit
directly" banner; edit the underlying code/data and re-run the generator. A
`--check` mode on both scripts (wired into `sync-wiki.yml`) fails on drift.

- **[CLI](cli.md)** — every CLI command + subcommand + flag, introspected from the live Typer app.

- **API reference (`api/`)** — a concise public-surface index per workspace package (symbols + submodules + a pointer to the live MkDocs API site for full signatures):
  - [`evidentia-core`](api/evidentia-core.md)
  - [`evidentia-ai`](api/evidentia-ai.md)
  - [`evidentia-mcp`](api/evidentia-mcp.md)
  - [`evidentia-collectors`](api/evidentia-collectors.md)
  - [`evidentia-api`](api/evidentia-api.md)
  - [`evidentia-eval`](api/evidentia-eval.md)
  - [`evidentia-integrations`](api/evidentia-integrations.md)

- **[MCP tools](mcp-tools.md)** — the MCP tools + signatures + behavior, parsed from the server's `@server.tool()` functions, with the append-only versioning rule per [`docs/api-stability.md`](../../api-stability.md) (NORMATIVE).

- **[Configuration](configuration.md)** — the `evidentia.yaml` schema + every `EVIDENTIA_*` environment variable + the LLM provider keys.

- **[Catalogs](catalogs.md)** — table of the bundled framework catalogs (the count is computed from the manifest), grouped by family + tier.

- **[Crosswalks](crosswalks.md)** — table of the bundled crosswalks + source/target frameworks + verification posture + mapping-row count (all computed from the mapping files).

## How to use this section

Reference is symbol-level; use full-text search (or the table of contents in each page) to jump to a specific command, flag, env var, or symbol. The catalog + crosswalk tables are sortable + filterable in the rendered MkDocs site.
