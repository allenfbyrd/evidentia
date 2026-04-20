import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

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
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

type StreamEvent =
  | { phase: "start"; total: number }
  | {
      phase: "progress";
      gap_id: string;
      control_id: string;
      framework: string;
      index: number;
      total: number;
      status: "generating" | "done";
      risk?: unknown;
    }
  | {
      phase: "error";
      gap_id?: string;
      control_id?: string;
      framework?: string;
      detail: string;
    }
  | { phase: "done"; generated: number; failed: number };

interface GapRow {
  key: string;
  status: "pending" | "generating" | "done" | "error";
  detail?: string;
  control_id?: string;
  framework?: string;
}

/**
 * Risk Generate — SSE-streamed per-gap progress.
 *
 * POSTs to /api/risk/generate using fetch + ReadableStream reader so we
 * can read the SSE body in the browser. (The standard EventSource API
 * doesn't support POST; sse-starlette serves a POST-friendly stream.)
 */
export function RiskGeneratePage() {
  const [reportKey, setReportKey] = useState<string | null>(null);
  const [contextPath, setContextPath] = useState("");
  const [topN, setTopN] = useState(10);
  const [rows, setRows] = useState<Record<string, GapRow>>({});
  const [progress, setProgress] = useState<{
    current: number;
    total: number;
  } | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [finalSummary, setFinalSummary] = useState<{
    generated: number;
    failed: number;
  } | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reportsQuery = useQuery({
    queryKey: ["gap-reports"],
    queryFn: () => api.listGapReports(),
  });
  const reports = reportsQuery.data?.reports ?? [];

  const reset = useCallback(() => {
    setRows({});
    setProgress(null);
    setFinalSummary(null);
    setStreamError(null);
  }, []);

  const onStreamEvent = useCallback((evt: StreamEvent) => {
    if (evt.phase === "start") {
      setProgress({ current: 0, total: evt.total });
    } else if (evt.phase === "progress") {
      const gapKey = evt.gap_id;
      setRows((prev) => ({
        ...prev,
        [gapKey]: {
          key: gapKey,
          status: evt.status,
          control_id: evt.control_id,
          framework: evt.framework,
        },
      }));
      if (evt.status === "done") {
        setProgress((p) =>
          p ? { ...p, current: Math.min(p.total, p.current + 1) } : p,
        );
      }
    } else if (evt.phase === "error") {
      if (evt.gap_id) {
        setRows((prev) => ({
          ...prev,
          [evt.gap_id!]: {
            key: evt.gap_id!,
            status: "error",
            detail: evt.detail,
            control_id: evt.control_id,
            framework: evt.framework,
          },
        }));
      } else {
        setStreamError(evt.detail);
      }
    } else if (evt.phase === "done") {
      setFinalSummary({
        generated: evt.generated,
        failed: evt.failed,
      });
      setIsStreaming(false);
    }
  }, []);

  const start = async () => {
    if (!reportKey) return;
    reset();
    setIsStreaming(true);
    abortRef.current = new AbortController();

    try {
      const res = await fetch("/api/risk/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        signal: abortRef.current.signal,
        body: JSON.stringify({
          report_key: reportKey,
          top_n: topN,
          context_path: contextPath.trim() || null,
        }),
      });

      if (!res.ok || !res.body) {
        const detail = (await res.text().catch(() => "")) || `HTTP ${res.status}`;
        setStreamError(`Request failed: ${detail.slice(0, 300)}`);
        setIsStreaming(false);
        return;
      }

      await readSse(res.body, onStreamEvent);
    } catch (e) {
      if ((e as { name?: string }).name !== "AbortError") {
        setStreamError(e instanceof Error ? e.message : String(e));
      }
      setIsStreaming(false);
    }
  };

  const cancel = () => {
    abortRef.current?.abort();
    setIsStreaming(false);
  };

  useEffect(() => () => abortRef.current?.abort(), []);

  const rowList = Object.values(rows);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">
          Risk Generate
        </h1>
        <p className="mt-1 text-muted-foreground">
          AI-generated NIST SP 800-30 risk statements for your top-priority
          gaps. Progress streams live from the server.
        </p>
      </header>

      {reports.length === 0 && (
        <Alert>
          <AlertTitle>No reports in the gap store yet</AlertTitle>
          <AlertDescription>
            Run a gap analysis first (from the{" "}
            <a href="/gap/analyze" className="underline">
              Gap Analyze
            </a>{" "}
            page) so there's a report to generate risks for.
          </AlertDescription>
        </Alert>
      )}

      {reports.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Configuration</CardTitle>
            <CardDescription>
              Pick the source report + system context. The generator
              fans out concurrently and streams per-gap progress back.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Source report</Label>
              <div className="mt-1 max-h-44 space-y-1 overflow-auto rounded-md border p-2">
                {reports.map((r) => (
                  <button
                    key={r.key}
                    type="button"
                    onClick={() => setReportKey(r.key)}
                    className={cn(
                      "block w-full rounded-md border px-3 py-1.5 text-left text-xs transition-colors",
                      reportKey === r.key
                        ? "border-primary bg-primary/5"
                        : "hover:bg-accent/50",
                    )}
                  >
                    <span className="font-medium">
                      {r.organization || "(unknown)"}
                    </span>{" "}
                    —{" "}
                    <span className="text-muted-foreground">
                      {r.total_gaps} gaps, {r.frameworks_analyzed.join(", ")}
                    </span>
                    <br />
                    <code className="rounded bg-muted px-1">{r.key}</code>{" "}
                    <span className="text-muted-foreground">
                      {new Date(r.mtime_iso).toLocaleString()}
                    </span>
                  </button>
                ))}
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <Label htmlFor="context-path">
                  system-context.yaml path (required)
                </Label>
                <Input
                  id="context-path"
                  placeholder="/abs/path/to/system-context.yaml"
                  value={contextPath}
                  onChange={(e) => setContextPath(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="top-n">Top N gaps</Label>
                <Input
                  id="top-n"
                  type="number"
                  min={1}
                  max={50}
                  value={topN}
                  onChange={(e) =>
                    setTopN(
                      Math.max(1, Math.min(50, Number(e.target.value) || 10)),
                    )
                  }
                  className="mt-1"
                />
                <p className="mt-1 text-xs text-muted-foreground">
                  Picks the highest-priority gaps by priority_score.
                </p>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2">
              {isStreaming ? (
                <Button variant="outline" onClick={cancel}>
                  Cancel
                </Button>
              ) : (
                <Button
                  onClick={start}
                  disabled={!reportKey || !contextPath.trim()}
                >
                  Generate
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {progress && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Progress</CardTitle>
            <CardDescription>
              {progress.current} of {progress.total} complete
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Progress
              value={
                progress.total === 0
                  ? 0
                  : (progress.current / progress.total) * 100
              }
            />
          </CardContent>
        </Card>
      )}

      {streamError && (
        <Alert variant="destructive">
          <AlertTitle>Stream error</AlertTitle>
          <AlertDescription>{streamError}</AlertDescription>
        </Alert>
      )}

      {finalSummary && (
        <Alert variant={finalSummary.failed > 0 ? "destructive" : "success"}>
          <AlertTitle>Done</AlertTitle>
          <AlertDescription>
            Generated {finalSummary.generated} risk statement
            {finalSummary.generated === 1 ? "" : "s"}
            {finalSummary.failed > 0 &&
              `; ${finalSummary.failed} failed (see individual rows below).`}
          </AlertDescription>
        </Alert>
      )}

      {rowList.length > 0 && (
        <ul className="divide-y rounded-lg border">
          {rowList.map((row) => (
            <li key={row.key} className="flex items-center gap-3 px-4 py-2">
              <StatusDot status={row.status} />
              <div className="flex-1 text-sm">
                {row.control_id && (
                  <span className="font-mono text-xs">
                    {row.framework}:{row.control_id}
                  </span>
                )}
                {row.detail && (
                  <span className="ml-2 text-xs text-destructive">
                    {row.detail}
                  </span>
                )}
              </div>
              <Badge variant="outline" className="capitalize">
                {row.status}
              </Badge>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function StatusDot({
  status,
}: {
  status: "pending" | "generating" | "done" | "error";
}) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-block h-2.5 w-2.5 rounded-full",
        status === "done" && "bg-primary",
        status === "generating" && "animate-pulse bg-primary/60",
        status === "error" && "bg-destructive",
        status === "pending" && "bg-muted-foreground/40",
      )}
    />
  );
}

/**
 * Minimal SSE reader for a POST-initiated text/event-stream response.
 * Parses `data: {...}` lines and dispatches parsed JSON to `onEvent`.
 */
async function readSse(
  body: ReadableStream<Uint8Array>,
  onEvent: (evt: StreamEvent) => void,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const lines = part.split("\n");
      const dataLines = lines
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trimStart());
      if (dataLines.length === 0) continue;
      const payload = dataLines.join("\n");
      try {
        const parsed = JSON.parse(payload) as StreamEvent;
        onEvent(parsed);
      } catch {
        // Ignore malformed frames — the server occasionally emits
        // keep-alive comments and other non-JSON lines.
      }
    }
  }
}
