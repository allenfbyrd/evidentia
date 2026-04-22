# controlbridge-api (DEPRECATED)

**This package has been renamed to [`evidentia-api`](https://pypi.org/project/evidentia-api/).**

The name change resolves a conflict with an unrelated commercial product.
This v0.5.1 release is a transitional re-export shim that forwards every
import to `evidentia-api`. It will be **removed in v0.7.0 (~October 2026)**.

## Migration

```bash
pip uninstall controlbridge-api
pip install evidentia-api
```

Then update any imports:

```python
# before
import controlbridge_api
from controlbridge_api.submodule import Thing

# after
import evidentia_api
from evidentia_api.submodule import Thing
```

## Why

See the [v0.6.0 CHANGELOG entry](https://github.com/allenfbyrd/evidentia/blob/main/CHANGELOG.md)
for the full rename rationale.
