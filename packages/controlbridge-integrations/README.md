# controlbridge-integrations

Output integrations for [ControlBridge](https://github.com/allenfbyrd/controlbridge). Push gaps to ticketing systems and export reports to industry-standard formats.

## Provides

- **Jira integration** — Create issues from ControlGap entries with framework-aware field population
- **ServiceNow integration** — Create GRC records and incidents from gaps and risks
- **OSCAL Assessment Results exporter** — Produce compliant OSCAL JSON for assessment reporting

## Install

```bash
pip install controlbridge-integrations[jira]
pip install controlbridge-integrations[servicenow]
pip install controlbridge-integrations[all]
```

License: Apache 2.0
