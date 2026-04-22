# controlbridge-integrations (DEPRECATED)

**This package has been renamed to [`evidentia-integrations`](https://pypi.org/project/evidentia-integrations/).**

The name change resolves a conflict with an unrelated commercial product.
This v0.5.1 release is a transitional re-export shim that forwards every
import to `evidentia-integrations`. It will be **removed in v0.7.0 (~October 2026)**.

## Migration

```bash
pip uninstall controlbridge-integrations
pip install evidentia-integrations
```

Then update any imports:

```python
# before
import controlbridge_integrations
from controlbridge_integrations.submodule import Thing

# after
import evidentia_integrations
from evidentia_integrations.submodule import Thing
```

## Why

See the [v0.6.0 CHANGELOG entry](https://github.com/allenfbyrd/evidentia/blob/main/CHANGELOG.md)
for the full rename rationale.
