import { useMutation, useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { GapTable } from "@/components/gap/GapTable";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useWizardStore } from "@/lib/wizard-store";
import type { GapAnalysisReport } from "@/types/api";

/**
 * Gap Analyze interactive page.
 *
 * Two inventory sources:
 *   1. A file uploaded from the browser (primary path; the wizard's
 *      upload path also lands here).
 *   2. A server-side path — typing a path the backend can read. Useful
 *      for CI / headless / power-user flows.
 *
 * Results render as a :class:`GapTable` below the form.
 */
export function GapAnalyzePage() {
  const uploadFile = useWizardStore((s) => s.uploadFile);
  const setUploadFile = useWizardStore((s) => s.setUploadFile);
  const [serverPath, setServerPath] = useState("");
  const [frameworks, setFrameworks] = useState<Set<string>>(new Set());
  const [organization, setOrganization] = useState("");
  const [systemName, setSystemName] = useState("");
  const [inventoryText, setInventoryText] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement | null>(null);

  const fwQuery = useQuery({
    queryKey: ["frameworks-picker"],
    queryFn: () => api.listFrameworks(),
  });

  const mutation = useMutation({
    mutationFn: async (): Promise<GapAnalysisReport> => {
      const payload: {
        frameworks: string[];
        organization?: string;
        system_name?: string;
        inventory_content?: string;
        inventory_format?: string;
        inventory_path?: string;
      } = {
        frameworks: Array.from(frameworks),
        organization: organization.trim() || undefined,
        system_name: systemName.trim() || undefined,
      };
      if (inventoryText) {
        payload.inventory_content = inventoryText;
        payload.inventory_format = inferFormat(uploadFile?.name);
      } else if (serverPath.trim()) {
        payload.inventory_path = serverPath.trim();
      }
      const res = await fetch("/api/gap/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        let detail: unknown = null;
        try {
          detail = await res.json();
        } catch {
          /* empty */
        }
        throw new ApiError(
          `POST /api/gap/analyze failed (${res.status})`,
          res.status,
          detail,
        );
      }
      return (await res.json()) as GapAnalysisReport;
    },
  });

  const handleFile = async (f: File | null) => {
    if (!f) return;
    setUploadFile(f);
    setInventoryText(await f.text());
  };

  const canSubmit =
    frameworks.size > 0 &&
    (inventoryText !== null || serverPath.trim().length > 0) &&
    !mutation.isPending;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Gap Analyze</h1>
        <p className="mt-1 text-muted-foreground">
          Pick frameworks, provide an inventory, and run{" "}
          <code className="rounded bg-muted px-1 py-0.5">
            evidentia gap analyze
          </code>{" "}
          from the browser. Results save to the gap store automatically.
        </p>
      </header>

      <form
        className="space-y-5"
        onSubmit={(e) => {
          e.preventDefault();
          if (canSubmit) mutation.mutate();
        }}
      >
        <section className="space-y-3">
          <h2 className="text-lg font-medium">1. Inventory</h2>
          <div className="grid gap-3 md:grid-cols-2">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Upload file</CardTitle>
                <CardDescription>YAML / JSON / CSV.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <input
                  ref={fileInput}
                  type="file"
                  accept=".yaml,.yml,.json,.csv"
                  className="sr-only"
                  id="analyze-upload"
                  onChange={(e) => {
                    handleFile(e.target.files?.[0] ?? null);
                  }}
                />
                <Label
                  htmlFor="analyze-upload"
                  className="inline-block cursor-pointer"
                >
                  <Button asChild variant="outline" size="sm">
                    <span>{uploadFile ? "Change file" : "Choose file"}</span>
                  </Button>
                </Label>
                {uploadFile && (
                  <p className="text-xs text-muted-foreground">
                    Selected: <code>{uploadFile.name}</code> ({uploadFile.size}{" "}
                    bytes)
                  </p>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Or server path</CardTitle>
                <CardDescription>
                  Absolute path readable by the server process.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Input
                  placeholder="/path/to/my-controls.yaml"
                  value={serverPath}
                  onChange={(e) => setServerPath(e.target.value)}
                />
              </CardContent>
            </Card>
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-medium">2. Frameworks</h2>
          <p className="text-sm text-muted-foreground">
            Pick one or more. Filter by tier in the{" "}
            <a href="/frameworks" className="underline">
              Frameworks browser
            </a>{" "}
            if you need help picking.
          </p>
          <div className="max-h-60 overflow-auto rounded-lg border p-3">
            {fwQuery.isPending && <p className="text-sm">Loading...</p>}
            {fwQuery.isError && (
              <p className="text-sm text-destructive">
                Could not load frameworks.
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              {fwQuery.data?.frameworks.map((fw) => {
                const checked = frameworks.has(fw.id);
                return (
                  <button
                    key={fw.id}
                    type="button"
                    role="switch"
                    aria-checked={checked}
                    onClick={() => {
                      const next = new Set(frameworks);
                      if (checked) {
                        next.delete(fw.id);
                      } else {
                        next.add(fw.id);
                      }
                      setFrameworks(next);
                    }}
                    className={cn(
                      "rounded-full border px-3 py-1 text-xs transition-colors",
                      checked
                        ? "border-primary bg-primary text-primary-foreground"
                        : "hover:bg-accent",
                    )}
                  >
                    {fw.id}{" "}
                    <span className="opacity-60">(T{fw.tier})</span>
                  </button>
                );
              })}
            </div>
          </div>
          {frameworks.size > 0 && (
            <p className="text-xs text-muted-foreground">
              Selected: {Array.from(frameworks).join(", ")}
            </p>
          )}
        </section>

        <section className="grid gap-3 md:grid-cols-2">
          <div>
            <Label htmlFor="org-override">Organization override (optional)</Label>
            <Input
              id="org-override"
              value={organization}
              onChange={(e) => setOrganization(e.target.value)}
              placeholder="Uses inventory's organization if blank"
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="system-override">System name override (optional)</Label>
            <Input
              id="system-override"
              value={systemName}
              onChange={(e) => setSystemName(e.target.value)}
              className="mt-1"
            />
          </div>
        </section>

        <div className="flex items-center justify-between border-t pt-4">
          <p className="text-xs text-muted-foreground">
            The report will be saved to the local gap store and appear on
            the Dashboard.
          </p>
          <Button type="submit" disabled={!canSubmit}>
            {mutation.isPending ? "Running..." : "Run analysis"}
          </Button>
        </div>
      </form>

      {mutation.isError && (
        <Alert variant="destructive">
          <AlertTitle>Analysis failed</AlertTitle>
          <AlertDescription>
            {mutation.error instanceof ApiError && mutation.error.payload
              ? JSON.stringify(mutation.error.payload)
              : String(mutation.error)}
          </AlertDescription>
        </Alert>
      )}

      {mutation.data && <GapResults report={mutation.data} />}
    </div>
  );
}

function GapResults({ report }: { report: GapAnalysisReport }) {
  return (
    <section className="space-y-4" aria-labelledby="results-heading">
      <header className="flex items-center justify-between">
        <h2 id="results-heading" className="text-xl font-semibold">
          Results
        </h2>
        <div className="flex gap-2">
          <Badge variant="outline">{report.total_gaps} total gaps</Badge>
          {report.critical_gaps > 0 && (
            <Badge variant="critical">{report.critical_gaps} critical</Badge>
          )}
          {report.high_gaps > 0 && (
            <Badge variant="high">{report.high_gaps} high</Badge>
          )}
        </div>
      </header>
      <div className="grid gap-3 sm:grid-cols-3">
        <MetricCard
          label="Coverage"
          value={`${report.coverage_percentage.toFixed(0)}%`}
          detail={`${report.total_controls_in_inventory} / ${report.total_controls_required} controls`}
        />
        <MetricCard
          label="Frameworks analyzed"
          value={String(report.frameworks_analyzed.length)}
          detail={report.frameworks_analyzed.join(", ")}
        />
        <MetricCard
          label="Efficiency wins"
          value={String(report.efficiency_opportunities.length)}
          detail="controls satisfying 3+ frameworks"
        />
      </div>
      <GapTable gaps={report.gaps} />
    </section>
  );
}

function MetricCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription className="text-xs uppercase tracking-wide">
          {label}
        </CardDescription>
        <CardTitle className="text-2xl">{value}</CardTitle>
      </CardHeader>
      <CardContent className="text-xs text-muted-foreground">
        {detail}
      </CardContent>
    </Card>
  );
}

function inferFormat(filename: string | undefined): string {
  if (!filename) return "yaml";
  const lower = filename.toLowerCase();
  if (lower.endsWith(".csv")) return "csv";
  if (lower.endsWith(".json")) return "json";
  return "yaml";
}
