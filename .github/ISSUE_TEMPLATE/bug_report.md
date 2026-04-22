---
name: Bug report
about: Report something that doesn't work as documented
title: "[BUG] "
labels: bug
assignees: ''
---

## Describe the bug

A clear, concise description of what the bug is.

## To reproduce

Steps to reproduce the behavior:

1. Command run: `...`
2. Inventory / catalog / context file used: `...`
3. Expected output: `...`
4. Actual output: `...`

If the bug is reproducible from a minimal example, please paste the YAML /
CSV / JSON here (redact any sensitive data).

```yaml
# minimal reproducing inventory or context
```

## Error output

Paste the full error message or traceback:

```
...
```

## Environment

- Evidentia version: (output of `evidentia version`)
- Python version: (output of `python --version`)
- Operating system: (e.g. Windows 11, macOS 14, Ubuntu 22.04)
- uv version: (output of `uv --version`)
- Installation method: (uv sync / pip / from source)

## Additional context

Anything else that might help — catalogs loaded, LLM provider in use,
relevant config settings, etc.
