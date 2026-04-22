# controlbridge-ai (DEPRECATED)

**This package has been renamed to [`evidentia-ai`](https://pypi.org/project/evidentia-ai/).**

The name change resolves a conflict with an unrelated commercial product.
This v0.5.1 release is a transitional re-export shim that forwards every
import to `evidentia-ai`. It will be **removed in v0.7.0 (~October 2026)**.

## Migration

```bash
pip uninstall controlbridge-ai
pip install evidentia-ai
```

Then update any imports:

```python
# before
import controlbridge_ai
from controlbridge_ai.submodule import Thing

# after
import evidentia_ai
from evidentia_ai.submodule import Thing
```

## Why

See the [v0.6.0 CHANGELOG entry](https://github.com/allenfbyrd/evidentia/blob/main/CHANGELOG.md)
for the full rename rationale.
