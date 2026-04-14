# controlbridge-core

Core data models, OSCAL catalog loaders, and the gap analysis engine for [ControlBridge](https://github.com/allenfbyrd/controlbridge).

This package has no AI dependencies and can be installed standalone for environments that need only the gap analysis functionality.

## Provides

- **Pydantic v2 data models** for controls, evidence, risks, gaps, findings, catalogs, and system context
- **OSCAL catalog loader** for NIST 800-53, NIST CSF, and other OSCAL-formatted frameworks
- **Crosswalk engine** for cross-framework control mappings
- **Gap analyzer** that compares a control inventory against framework catalogs
- **Report formatters** for JSON, CSV, Markdown, and OSCAL Assessment Results

## Install

```bash
pip install controlbridge-core
```

License: Apache 2.0
