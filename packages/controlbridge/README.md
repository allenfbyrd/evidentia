# controlbridge

The ControlBridge meta-package: provides the `controlbridge` CLI and the optional REST API.

This package depends on `controlbridge-core`, `controlbridge-ai`, `controlbridge-collectors`, and `controlbridge-integrations`. Installing it pulls in everything needed for a full ControlBridge installation.

## Install

```bash
pip install controlbridge
```

## CLI

```bash
controlbridge --help
cb --help                # short alias

controlbridge init       # scaffold a new project
controlbridge gap analyze --inventory my-controls.yaml --frameworks soc2-tsc
controlbridge risk generate --context system-context.yaml --gaps report.json
```

## REST API

```bash
controlbridge serve      # start FastAPI server on port 8000
```

License: Apache 2.0
