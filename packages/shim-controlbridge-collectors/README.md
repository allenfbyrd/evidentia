# controlbridge-collectors (DEPRECATED)

**This package has been renamed to [`evidentia-collectors`](https://pypi.org/project/evidentia-collectors/).**

The name change resolves a conflict with an unrelated commercial product.
This v0.5.1 release is a transitional re-export shim that forwards every
import to `evidentia-collectors`. It will be **removed in v0.7.0 (~October 2026)**.

## Migration

```bash
pip uninstall controlbridge-collectors
pip install evidentia-collectors
```

Then update any imports:

```python
# before
import controlbridge_collectors
from controlbridge_collectors.submodule import Thing

# after
import evidentia_collectors
from evidentia_collectors.submodule import Thing
```

## Why

See the [v0.6.0 CHANGELOG entry](https://github.com/allenfbyrd/evidentia/blob/main/CHANGELOG.md)
for the full rename rationale.
