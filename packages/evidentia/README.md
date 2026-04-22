# evidentia

The Evidentia meta-package: provides the `evidentia` CLI and the optional REST API.

This package depends on `evidentia-core`, `evidentia-ai`, `evidentia-collectors`, and `evidentia-integrations`. Installing it pulls in everything needed for a full Evidentia installation.

## Install

```bash
pip install evidentia
```

## CLI

```bash
evidentia --help
cb --help                # short alias

evidentia init       # scaffold a new project
evidentia gap analyze --inventory my-controls.yaml --frameworks soc2-tsc
evidentia risk generate --context system-context.yaml --gaps report.json
```

## REST API

```bash
evidentia serve      # start FastAPI server on port 8000
```

License: Apache 2.0
