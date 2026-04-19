import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

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
    <div className="space-y-8">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-muted-foreground">
            Gap analysis snapshots stored locally in{" "}
            <code className="rounded bg-muted px-1 py-0.5">
              {reportsQuery.data?.store_dir ?? "gap store"}
            </code>
          </p>
        </div>
        <Button asChild variant="outline">
          <Link to="/frameworks">Browse frameworks</Link>
        </Button>
      </header>

      <section
        className="grid gap-4 sm:grid-cols-3"
        aria-labelledby="top-metrics"
      >
        <h2 id="top-metrics" className="sr-only">
          Top-line metrics
        </h2>
        <MetricCard
          label="Bundled frameworks"
          value={String(totalFrameworks)}
          description="ready to analyze against"
        />
        <MetricCard
          label="Saved reports"
          value={String(totalReports)}
          description="in the local gap store"
        />
        <MetricCard
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
        />
      </section>

      <section aria-labelledby="recent-reports" className="space-y-3">
        <div className="flex items-end justify-between">
          <h2 id="recent-reports" className="text-xl font-medium">
            Recent reports
          </h2>
        </div>
        {reportsQuery.isPending && (
          <Card>
            <CardContent className="p-6 text-sm text-muted-foreground">
              Loading...
            </CardContent>
          </Card>
        )}
        {reportsQuery.isError && (
          <Card className="border-destructive">
            <CardContent className="p-6 text-sm text-destructive">
              Could not reach the backend. Is{" "}
              <code className="rounded bg-muted px-1 py-0.5">
                controlbridge serve
              </code>{" "}
              running?
            </CardContent>
          </Card>
        )}
        {reportsQuery.isSuccess && totalReports === 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">No reports yet</CardTitle>
              <CardDescription>
                Run{" "}
                <code className="rounded bg-muted px-1 py-0.5">
                  controlbridge gap analyze
                </code>{" "}
                in the terminal to create your first report. The UI will show
                it here.
              </CardDescription>
            </CardHeader>
          </Card>
        )}
        {reportsQuery.isSuccess && totalReports > 0 && (
          <ul className="space-y-3">
            {reportsQuery.data.reports.slice(0, 10).map((report) => (
              <li key={report.key}>
                <Card>
                  <CardHeader>
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <CardTitle className="text-base">
                          {report.organization || "(unknown org)"}
                        </CardTitle>
                        <CardDescription className="mt-1">
                          {new Date(report.mtime_iso).toLocaleString()} &middot;{" "}
                          {report.frameworks_analyzed.join(", ")}
                        </CardDescription>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">
                          {report.total_gaps} total gaps
                        </Badge>
                        {report.critical_gaps > 0 && (
                          <Badge variant="critical">
                            {report.critical_gaps} critical
                          </Badge>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0 text-xs text-muted-foreground">
                    <code className="rounded bg-muted px-1 py-0.5">
                      {report.key}
                    </code>{" "}
                    &middot; {(report.size_bytes / 1024).toFixed(1)} KiB
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

function MetricCard({
  label,
  value,
  description,
}: {
  label: string;
  value: string;
  description: string;
}) {
  return (
    <Card>
      <CardHeader className="space-y-1 pb-2">
        <CardDescription className="text-xs uppercase tracking-wide">
          {label}
        </CardDescription>
        <CardTitle className="text-3xl">{value}</CardTitle>
      </CardHeader>
      <CardContent className="pt-0 text-sm text-muted-foreground">
        {description}
      </CardContent>
    </Card>
  );
}
