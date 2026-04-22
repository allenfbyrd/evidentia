import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, CircleCheck, CirclePlus, Minus } from "lucide-react";
import { useMemo, useState } from "react";

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
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { severityBadge } from "@/lib/severity";
import type { GapDiff, GapDiffEntry } from "@/types/api";

/**
 * Gap Diff page — pick two saved reports, see what changed.
 *
 * Base / head are chosen from the gap-store reports list. After pressing
 * Compare we POST /api/gap/diff and render a summary + per-entry table.
 */
export function GapDiffPage() {
  const [baseKey, setBaseKey] = useState<string | null>(null);
  const [headKey, setHeadKey] = useState<string | null>(null);

  const reportsQuery = useQuery({
    queryKey: ["gap-reports"],
    queryFn: () => api.listGapReports(),
  });

  const mutation = useMutation({
    mutationFn: () => {
      if (!baseKey || !headKey) throw new Error("Pick base + head");
      return api.gapDiff(baseKey, headKey);
    },
  });

  const reports = reportsQuery.data?.reports ?? [];
  const canCompare = Boolean(baseKey && headKey && baseKey !== headKey);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Gap Diff</h1>
        <p className="mt-1 text-muted-foreground">
          Compare two saved reports. Good for PR-level compliance-as-code
          and for tracking how an org's posture moves over time.
        </p>
      </header>

      {reports.length < 2 && (
        <Alert>
          <AlertTitle>Need at least 2 saved reports</AlertTitle>
          <AlertDescription>
            Run <code>evidentia gap analyze</code> twice (or from the
            Gap Analyze page) to populate the gap store, then come back.
          </AlertDescription>
        </Alert>
      )}

      {reports.length >= 2 && (
        <section className="grid gap-3 md:grid-cols-2">
          <ReportPicker
            label="Base (before)"
            reports={reports}
            selected={baseKey}
            onSelect={setBaseKey}
          />
          <ReportPicker
            label="Head (after)"
            reports={reports}
            selected={headKey}
            onSelect={setHeadKey}
          />
        </section>
      )}

      <div className="flex items-center justify-end gap-3 border-t pt-4">
        {baseKey === headKey && baseKey !== null && (
          <span className="text-xs text-muted-foreground">
            Pick two different reports to compare.
          </span>
        )}
        <Button
          onClick={() => mutation.mutate()}
          disabled={!canCompare || mutation.isPending}
        >
          {mutation.isPending ? "Computing..." : "Compare"}
        </Button>
      </div>

      {mutation.isError && (
        <Alert variant="destructive">
          <AlertTitle>Diff failed</AlertTitle>
          <AlertDescription>
            {mutation.error instanceof Error
              ? mutation.error.message
              : "Unknown error."}
          </AlertDescription>
        </Alert>
      )}

      {mutation.data && <DiffView diff={mutation.data} />}
    </div>
  );
}

function ReportPicker({
  label,
  reports,
  selected,
  onSelect,
}: {
  label: string;
  reports: Array<{
    key: string;
    mtime_iso: string;
    organization: string;
    frameworks_analyzed: string[];
    total_gaps: number;
    critical_gaps: number;
  }>;
  selected: string | null;
  onSelect: (key: string) => void;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">{label}</CardTitle>
      </CardHeader>
      <CardContent className="max-h-72 space-y-1 overflow-auto">
        {reports.map((r) => (
          <button
            type="button"
            key={r.key}
            onClick={() => onSelect(r.key)}
            className={cn(
              "w-full rounded-md border px-3 py-2 text-left text-sm transition-colors",
              selected === r.key
                ? "border-primary bg-primary/5"
                : "hover:bg-accent/50",
            )}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium">
                {r.organization || "(unknown org)"}
              </span>
              <Badge variant="outline">{r.total_gaps} gaps</Badge>
            </div>
            <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
              <span>{new Date(r.mtime_iso).toLocaleString()}</span>
              <code className="rounded bg-muted px-1 py-0.5">{r.key}</code>
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              {r.frameworks_analyzed.join(", ")}
            </div>
          </button>
        ))}
      </CardContent>
    </Card>
  );
}

function DiffView({ diff }: { diff: GapDiff }) {
  const [filterStatus, setFilterStatus] = useState<
    "all" | "opened" | "closed" | "severity_changed"
  >("all");

  const summary = diff.summary;
  const filtered = useMemo(() => {
    if (filterStatus === "all") return diff.entries;
    if (filterStatus === "severity_changed") {
      return diff.entries.filter(
        (e) =>
          e.status === "severity_increased" ||
          e.status === "severity_decreased",
      );
    }
    return diff.entries.filter((e) => e.status === filterStatus);
  }, [diff.entries, filterStatus]);

  const isRegression = summary.opened > 0 || summary.severity_increased > 0;

  return (
    <section className="space-y-4" aria-labelledby="diff-summary">
      <h2 id="diff-summary" className="text-xl font-semibold">
        Diff summary
      </h2>
      <div className="grid gap-3 sm:grid-cols-5">
        <SummaryCard
          icon={<CirclePlus className="h-4 w-4" />}
          label="Opened"
          value={summary.opened}
          tone={summary.opened > 0 ? "destructive" : "neutral"}
        />
        <SummaryCard
          icon={<CircleCheck className="h-4 w-4" />}
          label="Closed"
          value={summary.closed}
          tone="success"
        />
        <SummaryCard
          icon={<ArrowUp className="h-4 w-4" />}
          label="Severity up"
          value={summary.severity_increased}
          tone={summary.severity_increased > 0 ? "destructive" : "neutral"}
        />
        <SummaryCard
          icon={<ArrowDown className="h-4 w-4" />}
          label="Severity down"
          value={summary.severity_decreased}
          tone="success"
        />
        <SummaryCard
          icon={<Minus className="h-4 w-4" />}
          label="Unchanged"
          value={summary.unchanged}
          tone="neutral"
        />
      </div>

      {isRegression && (
        <Alert variant="destructive">
          <AlertTitle>Regression detected</AlertTitle>
          <AlertDescription>
            {summary.opened} new gap{summary.opened === 1 ? "" : "s"} opened
            and {summary.severity_increased} severit
            {summary.severity_increased === 1 ? "y" : "ies"} increased. In CI,
            this would fail the <code>--fail-on-regression</code> check.
          </AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filter by status">
        {[
          ["all", `All (${diff.entries.length})`],
          ["opened", `Opened (${summary.opened})`],
          ["closed", `Closed (${summary.closed})`],
          [
            "severity_changed",
            `Severity changed (${summary.severity_increased + summary.severity_decreased})`,
          ],
        ].map(([value, label]) => (
          <button
            key={value as string}
            type="button"
            role="tab"
            aria-selected={filterStatus === value}
            onClick={() => setFilterStatus(value as typeof filterStatus)}
            className={cn(
              "rounded-md border px-3 py-1 text-xs transition-colors",
              filterStatus === value
                ? "border-primary bg-primary text-primary-foreground"
                : "hover:bg-accent",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-3 py-2 text-left text-xs uppercase">Status</th>
              <th className="px-3 py-2 text-left text-xs uppercase">Framework</th>
              <th className="px-3 py-2 text-left text-xs uppercase">Control</th>
              <th className="px-3 py-2 text-left text-xs uppercase">Title</th>
              <th className="px-3 py-2 text-left text-xs uppercase">Base</th>
              <th className="px-3 py-2 text-left text-xs uppercase">Head</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filtered.map((e, i) => (
              <DiffRow entry={e} key={`${e.framework}:${e.control_id}:${i}`} />
            ))}
            {filtered.length === 0 && (
              <tr>
                <td
                  colSpan={6}
                  className="p-4 text-center text-sm text-muted-foreground"
                >
                  No entries match the current filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function SummaryCard({
  icon,
  label,
  value,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  tone: "success" | "destructive" | "neutral";
}) {
  return (
    <Card
      className={cn(
        tone === "destructive" && value > 0 && "border-destructive/60",
        tone === "success" && value > 0 && "border-primary/60",
      )}
    >
      <CardHeader className="pb-2">
        <CardDescription className="flex items-center gap-1 text-xs uppercase tracking-wide">
          {icon} {label}
        </CardDescription>
        <CardTitle className="text-3xl">{value}</CardTitle>
      </CardHeader>
    </Card>
  );
}

function DiffRow({ entry }: { entry: GapDiffEntry }) {
  const statusLabel: Record<GapDiffEntry["status"], string> = {
    opened: "opened",
    closed: "closed",
    severity_increased: "sev ↑",
    severity_decreased: "sev ↓",
    unchanged: "unchanged",
  };
  const statusBadgeVariant: Record<
    GapDiffEntry["status"],
    "critical" | "default" | "outline" | "secondary"
  > = {
    opened: "critical",
    closed: "default",
    severity_increased: "critical",
    severity_decreased: "default",
    unchanged: "outline",
  };
  return (
    <tr className="hover:bg-accent/30">
      <td className="px-3 py-2">
        <Badge variant={statusBadgeVariant[entry.status]}>
          {statusLabel[entry.status]}
        </Badge>
      </td>
      <td className="px-3 py-2">
        <code className="rounded bg-muted px-1 py-0.5 text-xs">
          {entry.framework}
        </code>
      </td>
      <td className="px-3 py-2 font-mono text-xs">{entry.control_id}</td>
      <td className="px-3 py-2">
        <span className="line-clamp-1 text-sm">
          {entry.control_title ?? "—"}
        </span>
      </td>
      <td className="px-3 py-2">
        {entry.base_severity ? (
          <Badge variant={severityBadge(entry.base_severity)}>
            {entry.base_severity}
          </Badge>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </td>
      <td className="px-3 py-2">
        {entry.head_severity ? (
          <Badge variant={severityBadge(entry.head_severity)}>
            {entry.head_severity}
          </Badge>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </td>
    </tr>
  );
}
