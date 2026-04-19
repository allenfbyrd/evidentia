import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api } from "@/lib/api";

/**
 * Settings page (v0.4.0-alpha.1 read-only surface).
 *
 * Read paths shipped: config, LLM status, air-gap posture.
 * Write paths (PUT /api/config with validated Pydantic payload) land
 * in v0.4.0-alpha.2 along with the interactive form.
 */
export function SettingsPage() {
  const config = useQuery({
    queryKey: ["config"],
    queryFn: () => api.getConfig(),
  });

  const llm = useQuery({
    queryKey: ["llm-status"],
    queryFn: () => api.llmStatus(),
  });

  const airGap = useQuery({
    queryKey: ["air-gap"],
    queryFn: () => api.doctorCheckAirGap(),
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-muted-foreground">
          Configuration view. Editing lands in v0.4.0-alpha.2 — for now,
          edit{" "}
          <code className="rounded bg-muted px-1 py-0.5">controlbridge.yaml</code>{" "}
          in your project directory to update these values.
        </p>
      </header>

      <section aria-labelledby="project-config">
        <h2 id="project-config" className="sr-only">
          Project configuration
        </h2>
        <Card>
          <CardHeader>
            <CardTitle>Project configuration</CardTitle>
            <CardDescription>
              Loaded from{" "}
              <code className="rounded bg-muted px-1 py-0.5">
                {config.data?.source_path ?? "controlbridge.yaml (not found; showing defaults)"}
              </code>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <ConfigRow
              label="Organization"
              value={config.data?.organization ?? "(none)"}
            />
            <ConfigRow
              label="System name"
              value={config.data?.system_name ?? "(none)"}
            />
            <ConfigRow
              label="Default frameworks"
              value={
                config.data && config.data.frameworks.length > 0
                  ? config.data.frameworks.join(", ")
                  : "(none)"
              }
            />
            <ConfigRow
              label="LLM model"
              value={config.data?.llm?.model ?? "(default: gpt-4o)"}
            />
            <ConfigRow
              label="LLM temperature"
              value={
                config.data?.llm?.temperature != null
                  ? String(config.data.llm.temperature)
                  : "(default: 0.1)"
              }
            />
          </CardContent>
        </Card>
      </section>

      <section aria-labelledby="llm-providers">
        <h2 id="llm-providers" className="sr-only">
          LLM providers
        </h2>
        <Card>
          <CardHeader>
            <CardTitle>LLM providers</CardTitle>
            <CardDescription>
              Provider keys are detected from environment variables. The
              browser never sees key values — only the presence flag below.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {llm.data ? (
              Object.entries(llm.data.providers).map(([name, state]) => (
                <div key={name} className="flex items-center justify-between">
                  <span className="capitalize">{name.replace(/_/g, " ")}</span>
                  {state.configured ? (
                    <Badge>configured via {state.source}</Badge>
                  ) : (
                    <Badge variant="outline">not configured</Badge>
                  )}
                </div>
              ))
            ) : (
              <span className="text-muted-foreground">Loading...</span>
            )}
            <p className="pt-2 text-xs text-muted-foreground">
              Active model: <code className="rounded bg-muted px-1 py-0.5">
                {llm.data?.configured_model ?? "—"}
              </code>
            </p>
          </CardContent>
        </Card>
      </section>

      <section aria-labelledby="air-gap-section">
        <h2 id="air-gap-section" className="sr-only">
          Air-gap posture
        </h2>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Air-gap posture
              {airGap.data?.air_gapped ? (
                <Badge>air-gap ready</Badge>
              ) : (
                <Badge variant="destructive">would leak</Badge>
              )}
            </CardTitle>
            <CardDescription>
              Audits configured endpoints without issuing network IO. Pass{" "}
              <code className="rounded bg-muted px-1 py-0.5">--offline</code>{" "}
              at CLI / server startup to enforce.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {airGap.data?.checks.map((check) => (
              <div
                key={check.subsystem}
                className="flex items-start justify-between gap-4"
              >
                <div>
                  <div className="font-mono text-xs uppercase tracking-wide text-muted-foreground">
                    {check.subsystem}
                  </div>
                  <div>{check.detail}</div>
                </div>
                {check.status === "ok" && <Badge>ok</Badge>}
                {check.status === "would_leak" && (
                  <Badge variant="destructive">would leak</Badge>
                )}
                {check.status === "skipped" && (
                  <Badge variant="outline">skipped</Badge>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function ConfigRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="font-medium text-muted-foreground">{label}</span>
      <span className="text-right font-mono">{value}</span>
    </div>
  );
}
