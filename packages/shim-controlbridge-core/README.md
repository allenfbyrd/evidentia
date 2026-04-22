# controlbridge-core (DEPRECATED)

**This package has been renamed to [`evidentia-core`](https://pypi.org/project/evidentia-core/).**

The name change resolves a conflict with an unrelated commercial product.
This v0.5.1 release is a transitional re-export shim that forwards every
import to `evidentia-core`. It will be **removed in v0.7.0 (~October 2026)**.

## Migration

```bash
pip uninstall controlbridge-core
pip install evidentia-core
```

Then update any imports:

```python
# before
import controlbridge_core
from controlbridge_core.submodule import Thing

# after
import evidentia_core
from evidentia_core.submodule import Thing
```

## Why

See the [v0.6.0 CHANGELOG entry](https://github.com/allenfbyrd/evidentia/blob/main/CHANGELOG.md)
for the full rename rationale.
