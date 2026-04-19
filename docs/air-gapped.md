# Air-gapped deployments

ControlBridge v0.4.0 adds a first-class air-gapped mode: the `--offline` flag refuses any outbound network call to a non-loopback / non-RFC-1918 host, before the network IO is issued. Paired with a local LLM (Ollama, vLLM, a self-hosted OpenAI-compatible endpoint), you can run every ControlBridge feature entirely on your own infrastructure.

This document covers the design, configuration, and verification of air-gapped deployments.

## Why air-gapped?

Several high-LTV audiences cannot send compliance data to third-party SaaS:

- **CMMC / FedRAMP** — Federal contractors handling CUI face contractual prohibitions on offloading assessment data.
- **Healthcare** — HIPAA-covered entities managing PHI need to avoid any BAA that isn't already in place.
- **Air-gapped environments** — Classified networks, isolated OT / SCADA, some financial back offices.
- **Enterprise procurement** — CISOs who've been burned by data-residency surprises and want hard technical guarantees.

ControlBridge's architecture makes this natural: the CLI and web UI are local, gap arithmetic runs on-device, and the only optional network calls are LLM API requests. Point `CONTROLBRIDGE_LLM_MODEL` at Ollama and you're done.

> *"The only open-source GRC tool that runs entirely on your infrastructure."*

## What `--offline` guards

`controlbridge_core.network_guard` audits every outbound call through the module-level flag. When `--offline` is set (CLI root flag, or `controlbridge serve --offline`), the following are enforced:

| Subsystem | Guard | Allowed targets |
|---|---|---|
| LLM client | `check_llm_model(model, api_base)` wraps `litellm.completion` / `acompletion` | `ollama/*`, `ollama_chat/*`, `vllm/*`, `text-completion-openai/*` model prefixes; any `api_base` with a loopback / RFC-1918 / link-local / IPv6-unique-local hostname |
| Catalog loader | `check_url(url)` on any URL-based fetch | Loopback / RFC-1918 only (v0.4.0 loads only from bundled + user-dir catalogs; URL-based `catalog import` is a future feature that will already be guarded) |
| AI telemetry | n/a | LiteLLM + Instructor do not emit telemetry; nothing to block |
| Gap store | n/a | On-disk under `platformdirs.user_data_dir` — local filesystem only |
| Web UI bind | CLI warning | `controlbridge serve` binds to `127.0.0.1` by default; `--host 0.0.0.0` emits a security warning but is permitted |

Allowed hosts in offline mode:

- IPv4 loopback (`127.0.0.0/8`)
- IPv4 link-local (`169.254.0.0/16`)
- IPv4 private (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
- IPv6 loopback (`::1`)
- IPv6 link-local (`fe80::/10`)
- IPv6 unique-local (`fc00::/7`)
- Hostname `localhost` / `localhost.localdomain`

Any other target raises `controlbridge_core.network_guard.OfflineViolationError` with a structured `{subsystem, target, remediation}` payload that the CLI and GUI surface to the user.

## Quick start — Ollama on your laptop

```bash
# 1. Install Ollama (https://ollama.com)
# 2. Pull a model with a big enough context window for control text
ollama pull llama3.1:8b

# 3. Configure ControlBridge to use it
export CONTROLBRIDGE_LLM_MODEL=ollama/llama3.1:8b

# 4. Verify air-gap posture
controlbridge doctor --check-air-gap
#  LLM client     AIR-GAP READY   model=ollama/llama3.1:8b (local prefix)
#  Catalog loader AIR-GAP READY   v0.4.0 loads only from bundled + user-dir catalogs
#  ...

# 5. Run analysis in offline mode
controlbridge --offline gap analyze --inventory my-controls.yaml \
  --framework nist-800-53-rev5-moderate

# 6. Generate risk statements offline (LLM calls hit Ollama only)
controlbridge --offline risk generate --gap-id GAP-0001 \
  --context system-context.yaml
```

## Self-hosted OpenAI-compatible endpoint (vLLM, LocalAI, TabbyAPI)

For organizations running an internal inference server on private infrastructure:

```bash
# vLLM exposes an OpenAI-compatible endpoint on a private IP
export CONTROLBRIDGE_LLM_MODEL=gpt-4o-compatible
export CONTROLBRIDGE_LLM_API_BASE=http://10.50.1.20:8000/v1

# The guard checks the api_base host, not the model string — any cloud
# model name paired with an RFC-1918 api_base is fine in offline mode.
controlbridge --offline doctor --check-air-gap
#  LLM client     AIR-GAP READY   api_base=http://10.50.1.20:8000/v1 on loopback/RFC-1918
```

## Web UI in air-gapped deployments

`controlbridge serve` binds to `127.0.0.1` by default and runs the entire UI + API from one uvicorn process on-disk. No external assets, no CDN, no telemetry. The React bundle is served from inside the Python wheel.

```bash
# Launch in air-gapped mode
controlbridge --offline serve

# The Settings page shows an "air-gapped" badge in the header and grays
# out LLM-backed features unless you have a local endpoint configured.
```

For multi-user network deployments (a shared CMMC assessor's browser station, for example), bind to `0.0.0.0` and front with an authenticated reverse proxy:

```nginx
server {
  listen 443 ssl;
  server_name controlbridge.internal;

  # SSO / LDAP / whatever
  auth_request /auth;

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
  }
}
```

**Important:** ControlBridge has no auth in v0.4.0. Never bind to a non-loopback address without fronting with an authenticated proxy. Multi-user auth / RBAC is queued for v0.7.0+.

## Verification checklist for auditors

Proof-of-offline for an external auditor:

1. **Environment.** Disable outbound network on the host. (On Linux: `iptables -A OUTPUT -j DROP` except loopback.)
2. **Preflight.** `controlbridge --offline doctor --check-air-gap` — every subsystem should report `AIR-GAP READY`. Red entries = configuration mistakes to fix before starting.
3. **Run analysis.** `controlbridge --offline gap analyze ...` should complete without network errors.
4. **Run risk generation.** With Ollama or vLLM configured, `controlbridge --offline risk generate --gap-id GAP-XXXX` should produce a risk statement. If the LLM endpoint is misconfigured, you'll get a clear `OfflineViolationError` — **not** a mystery timeout.
5. **Web UI.** `controlbridge --offline serve` — the Settings page's air-gap posture widget should match the CLI `doctor` output.

The `OfflineViolationError` catches configuration mistakes before any data leaves the machine. If ControlBridge thinks a call might leak, it won't make the call. Fail closed, not open.

## Architecture notes

The guard module (`controlbridge_core.network_guard`) is deliberately small — a process-wide flag plus two enforcement functions (`check_url`, `check_llm_model`) plus a host classifier (`is_loopback_or_private`). Call sites (LLM client, future URL-based catalog import) invoke these explicitly; there's no monkey-patching, no import-time magic. Adding a guard to a new subsystem is a one-line addition.

The module is covered by 43 unit tests in `tests/unit/test_network_guard.py`. See the [source](../packages/controlbridge-core/src/controlbridge_core/network_guard.py) for docstrings covering every allowed-range rationale.

## Roadmap

- v0.4.0-alpha.2: GUI Settings-page air-gap toggle wired through every `/api/*` request.
- v0.5.0: First offline-capable collectors — on-premises AWS Config via the AWS SDK with custom endpoints, on-premises GitHub Enterprise, on-premises Okta Identity Cloud for Government.
- v0.6.0: Evidence chain of custody — SHA-256 digests + optional GPG signing of OSCAL Assessment Results exports, tamper-evident audit trails that survive external review.
