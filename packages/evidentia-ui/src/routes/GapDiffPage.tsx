import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, CheckCircle2, CirclePlus, Minus } from "lucide-react";
import { useMemo, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
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
    <div className="stack-6">
      <header>
        <h1 className="page-title">Gap Diff</h1>
        <p className="page-sub">
          Compare two saved reports. Good for PR-level compliance-as-code
          and for tracking how an org's posture moves over time.
        </p>
      </header>

      {reports.length < 2 && (
        <Alert>
          <AlertTitle>Need at least 2 saved reports</AlertTitle>
          <AlertDescription>
            Run <code className="kbd">evidentia gap analyze</code> twice (or
            from the Gap Analyze page) to populate the gap store, then come
            back.
          </AlertDescription>
        </Alert>
      )}

      {reports.length >= 2 && (
        <section className="grid grid-2">
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

      <div className="row-end gap-3 border-t pt-4">
        {baseKey === headKey && baseKey !== null && (
          <span className="text-xs muted">
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
        <CardTitle className="base">{label}</CardTitle>
      </CardHeader>
      <CardContent className="scroll-72 stack-2">
        {reports.map((r) => (
          <button
            type="button"
            key={r.key}
            onClick={() => onSelect(r.key)}
            className={cn("select-row", selected === r.key && "on")}
          >
            <div className="row-between">
              <span style={{ fontWeight: 500 }} className="text-sm">
                {r.organization || "(unknown org)"}
              </span>
              <Badge variant="outline">{r.total_gaps} gaps</Badge>
            </div>
            <div
              className="row-between text-xs muted"
              style={{ marginTop: "0.25rem" }}
            >
              <span>{new Date(r.mtime_iso).toLocaleString()}</span>
              <code className="kbd">{r.key}</code>
            </div>
            <div className="text-xs muted" style={{ marginTop: "0.25rem" }}>
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

  const cards: Array<{
    icon: React.ReactNode;
    label: string;
    value: number;
    tone: "dest" | "prim" | "neutral";
  }> = [
    {
      icon: <CirclePlus className="ic" aria-hidden style={{ width: "0.95rem", height: "0.95rem" }} />,
      label: "Opened",
      value: summary.opened,
      tone: summary.opened > 0 ? "dest" : "neutral",
    },
    {
      icon: <CheckCircle2 className="ic" aria-hidden style={{ width: "0.95rem", height: "0.95rem" }} />,
      label: "Closed",
      value: summary.closed,
      tone: "prim",
    },
    {
      icon: <ArrowUp className="ic" aria-hidden style={{ width: "0.95rem", height: "0.95rem" }} />,
      label: "Severity up",
      value: summary.severity_increased,
      tone: summary.severity_increased > 0 ? "dest" : "neutral",
    },
    {
      icon: <ArrowDown className="ic" aria-hidden style={{ width: "0.95rem", height: "0.95rem" }} />,
      label: "Severity down",
      value: summary.severity_decreased,
      tone: "prim",
    },
    {
      icon: <Minus className="ic" aria-hidden style={{ width: "0.95rem", height: "0.95rem" }} />,
      label: "Unchanged",
      value: summary.unchanged,
      tone: "neutral",
    },
  ];

  const tabs: Array<[typeof filterStatus, string]> = [
    ["all", `All (${diff.entries.length})`],
    ["opened", `Opened (${summary.opened})`],
    ["closed", `Closed (${summary.closed})`],
    [
      "severity_changed",
      `Severity changed (${summary.severity_increased + summary.severity_decreased})`,
    ],
  ];

  return (
    <section className="stack-4" aria-labelledby="diff-summary">
      <h2 id="diff-summary" className="h2-lg">
        Diff summary
      </h2>
      <div className="grid grid-5">
        {cards.map((c) => {
          const isDestActive = c.value > 0 && c.tone === "dest";
          return (
            <Card
              key={c.label}
              className={cn(
                c.value > 0 && c.tone === "dest" && "border-dest",
                c.value > 0 && c.tone === "prim" && "border-prim",
              )}
            >
              <CardContent style={{ padding: "var(--card-pad)" }}>
                <div
                  className="row gap-2 metric-label"
                  style={{
                    color: isDestActive ? "hsl(var(--destructive))" : undefined,
                  }}
                >
                  {c.icon}
                  {c.label}
                </div>
                <p
                  className="metric-value sm"
                  style={{
                    color: isDestActive ? "hsl(var(--destructive))" : undefined,
                  }}
                >
                  {c.value}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {isRegression && (
        <Alert variant="destructive">
          <AlertTitle>Regression detected</AlertTitle>
          <AlertDescription>
            {summary.opened} new gap{summary.opened === 1 ? "" : "s"} opened
            and {summary.severity_increased} severit
            {summary.severity_increased === 1 ? "y" : "ies"} increased. In CI,
            this would fail the <code className="kbd">--fail-on-regression</code>{" "}
            check.
          </AlertDescription>
        </Alert>
      )}

      <div className="row wrap gap-2" role="tablist" aria-label="Filter by status">
        {tabs.map(([value, label]) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={filterStatus === value}
            onClick={() => setFilterStatus(value)}
            className={cn("seg", filterStatus === value && "on")}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="table-wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th>Status</th>
              <th>Framework</th>
              <th>Control</th>
              <th>Title</th>
              <th>Base</th>
              <th>Head</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((e, i) => (
              <DiffRow entry={e} key={`${e.framework}:${e.control_id}:${i}`} />
            ))}
            {filtered.length === 0 && (
              <tr>
                <td
                  colSpan={6}
                  style={{ textAlign: "center", padding: "1rem" }}
                  className="text-sm muted"
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
  const rowSeverity = entry.head_severity || entry.base_severity || undefined;
  return (
    <tr
      data-severity={rowSeverity}
      style={
        {
          "--rowsev": `hsl(var(--sev-${rowSeverity ?? "informational"}))`,
        } as React.CSSProperties
      }
    >
      <td>
        <Badge variant={statusBadgeVariant[entry.status]}>
          {statusLabel[entry.status]}
        </Badge>
      </td>
      <td>
        <code className="kbd">{entry.framework}</code>
      </td>
      <td className="mono text-xs">{entry.control_id}</td>
      <td>
        <span className="line-1 text-sm">{entry.control_title ?? "—"}</span>
      </td>
      <td>
        {entry.base_severity ? (
          <Badge variant={severityBadge(entry.base_severity)}>
            {entry.base_severity}
          </Badge>
        ) : (
          <span className="text-xs muted">—</span>
        )}
      </td>
      <td>
        {entry.head_severity ? (
          <Badge variant={severityBadge(entry.head_severity)}>
            {entry.head_severity}
          </Badge>
        ) : (
          <span className="text-xs muted">—</span>
        )}
      </td>
    </tr>
  );
}
