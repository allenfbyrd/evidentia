import { useQuery } from "@tanstack/react-query";
import { Database, Layers, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { MetricCard } from "@/components/common/console";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";

/**
 * Dashboard — historical gap reports from the gap store + top-level metrics.
 *
 * v0.4.0-alpha.1: read-only listing + metric cards. Running a new analysis
 * from the UI (POST /api/gap/analyze with an inventory upload) is deferred
 * to v0.4.0-alpha.2 so this page ships with a clean shape today.
 */
export function DashboardPage() {
  const reportsQuery = useQuery({
    queryKey: ["gap-reports"],
    queryFn: () => api.listGapReports(),
  });

  const frameworksQuery = useQuery({
    queryKey: ["frameworks-count"],
    queryFn: () => api.listFrameworks(),
  });

  const totalFrameworks = frameworksQuery.data?.total ?? 0;
  const totalReports = reportsQuery.data?.total ?? 0;
  const latest = reportsQuery.data?.reports[0];

  return (
    <div className="stack-8">
      <header className="row-between" style={{ alignItems: "flex-end" }}>
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-sub">
            Gap analysis snapshots stored locally in{" "}
            <code className="kbd">
              {reportsQuery.data?.store_dir ?? "gap store"}
            </code>
          </p>
        </div>
        <Button asChild variant="outline">
          <Link to="/frameworks">Browse frameworks</Link>
        </Button>
      </header>

      <section className="grid grid-3" aria-labelledby="top-metrics">
        <h2 id="top-metrics" className="sr-only">
          Top-line metrics
        </h2>
        <MetricCard
          icon={Layers}
          label="Bundled frameworks"
          value={String(totalFrameworks)}
          description="ready to analyze against"
          big
        />
        <MetricCard
          icon={Database}
          label="Saved reports"
          value={String(totalReports)}
          description="in the local gap store"
          big
        />
        <MetricCard
          icon={ShieldCheck}
          label="Latest coverage"
          value={
            latest?.coverage_percentage != null
              ? `${latest.coverage_percentage.toFixed(0)}%`
              : "—"
          }
          description={
            latest?.organization
              ? `across ${latest.frameworks_analyzed.length} framework${
                  latest.frameworks_analyzed.length === 1 ? "" : "s"
                }`
              : "no analysis yet"
          }
          big
        />
      </section>

      <section aria-labelledby="recent-reports" className="stack-3">
        <div className="row-between" style={{ alignItems: "flex-end" }}>
          <h2 id="recent-reports" className="h2">
            Recent reports
          </h2>
          <Link to="/gap/analyze" className="primary-link text-sm">
            Run new analysis &rarr;
          </Link>
        </div>

        {reportsQuery.isPending && (
          <ul className="reset stack-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <li key={i} className="reset">
                <div className="skel" style={{ height: "5.5rem" }} />
              </li>
            ))}
          </ul>
        )}

        {reportsQuery.isError && (
          <Alert variant="destructive">
            <AlertTitle>Could not reach the backend</AlertTitle>
            <AlertDescription>
              Is <code className="kbd">evidentia serve</code> running?
            </AlertDescription>
          </Alert>
        )}

        {reportsQuery.isSuccess && totalReports === 0 && (
          <div className="empty-state">
            No reports yet. Run{" "}
            <code className="kbd">evidentia gap analyze</code> in the terminal to
            create your first report. The UI will show it here.
          </div>
        )}

        {reportsQuery.isSuccess && totalReports > 0 && (
          <ul className="reset stack-3">
            {reportsQuery.data.reports.slice(0, 10).map((report) => (
              <li key={report.key} className="reset">
                <Card className="card-hover">
                  <CardContent style={{ padding: "var(--card-pad)" }}>
                    <div
                      className="row-between gap-4 wrap"
                      style={{ alignItems: "flex-start" }}
                    >
                      <div className="stack-2" style={{ minWidth: 0 }}>
                        <div className="row gap-2 wrap">
                          <span className="card-title base">
                            {report.organization || "(unknown org)"}
                          </span>
                          {report.coverage_percentage != null && (
                            <Badge variant="secondary">
                              {report.coverage_percentage.toFixed(0)}% coverage
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm muted" style={{ margin: 0 }}>
                          {new Date(report.mtime_iso).toLocaleString()} &middot;{" "}
                          {report.frameworks_analyzed.join(", ")}
                        </p>
                        <p className="text-xs faint" style={{ margin: 0 }}>
                          <code className="kbd">{report.key}</code> &middot;{" "}
                          {(report.size_bytes / 1024).toFixed(1)} KiB
                        </p>
                      </div>
                      <div className="row gap-2" style={{ flexShrink: 0 }}>
                        <Badge variant="outline">{report.total_gaps} gaps</Badge>
                        {report.critical_gaps > 0 && (
                          <Badge variant="critical">
                            {report.critical_gaps} critical
                          </Badge>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
