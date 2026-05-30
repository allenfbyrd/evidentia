/**
 * Typed API client for the Evidentia REST backend.
 *
 * Thin fetch wrapper returning typed data or throwing `ApiError`. All hooks
 * in @/hooks/*.ts wrap these calls with TanStack Query for caching,
 * retries, and mutation state.
 *
 * Runtime base URL: always same-origin (production ships frontend + API
 * from one uvicorn instance). Dev mode: Vite's proxy forwards /api to :8000.
 */

import { parseContentDispositionFilename } from "@/lib/download";
import type {
  AirGapCheckResponse,
  GapAnalysisReport,
  GapDiff,
  HealthResponse,
  InitWizardRequest,
  InitWizardResponse,
  LlmStatusResponse,
  VersionResponse,
} from "@/types/api";
import type { ControlCatalog, CatalogControl } from "@/types/catalog";
import type { EvidentiaConfig } from "@/types/config";

export class ApiError extends Error {
  public readonly status: number;
  public readonly payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      /* empty body is fine */
    }
    throw new ApiError(
      `API ${init?.method ?? "GET"} ${path} failed (${response.status})`,
      response.status,
      payload,
    );
  }

  if (response.status === 204) {
    return undefined as unknown as T;
  }

  return (await response.json()) as T;
}

export interface FrameworkListEntry {
  id: string;
  name: string;
  version: string;
  tier: string;
  category: string;
  placeholder: string;
  license_required: string;
}

export interface FrameworkListResponse {
  total: number;
  frameworks: FrameworkListEntry[];
}

export interface GapReportMeta {
  key: string;
  mtime_iso: string;
  size_bytes: number;
  organization: string;
  frameworks_analyzed: string[];
  total_gaps: number;
  critical_gaps: number;
  coverage_percentage: number | null;
}

export interface GapReportListResponse {
  total: number;
  reports: GapReportMeta[];
  store_dir: string;
}

/**
 * Gap-report export formats supported by `POST /api/gap/export`.
 *
 * Mirrors `evidentia_core.gap_analyzer.reporter.OutputFormat` (the same
 * set the CLI's `evidentia gap analyze --format` honors). Kept in sync
 * with `GAP_EXPORT_FORMATS` in the API's `schemas.py`.
 */
export const GAP_EXPORT_FORMATS = [
  { id: "json", label: "JSON", hint: "Full report (native Evidentia schema)" },
  { id: "oscal-ar", label: "OSCAL AR", hint: "OSCAL Assessment Results" },
  { id: "sarif", label: "SARIF", hint: "SARIF 2.1.0 (code-scanning)" },
  { id: "ocsf", label: "OCSF Compliance", hint: "OCSF Compliance Finding (2003)" },
  {
    id: "ocsf-detection",
    label: "OCSF Detection",
    hint: "OCSF Detection Finding (2004, SIEM)",
  },
  { id: "cyclonedx-vex", label: "CycloneDX VEX", hint: "CycloneDX 1.6 VEX" },
  { id: "csv", label: "CSV", hint: "One row per gap" },
  { id: "markdown", label: "Markdown", hint: "Human-readable report" },
] as const;

export type GapExportFormat = (typeof GAP_EXPORT_FORMATS)[number]["id"];

export interface GapExportResult {
  blob: Blob;
  filename: string;
}

/**
 * Request a gap-report export and return the artifact blob + the
 * server-suggested filename (parsed from `Content-Disposition`).
 *
 * Does NOT go through the JSON `request()` helper because the response
 * body is an arbitrary artifact (JSON / CSV / SARIF / …), not a typed
 * JSON envelope. On a non-2xx response the JSON `{detail}` error body is
 * read and thrown as an `ApiError`.
 */
export async function exportGapReport(
  report: GapAnalysisReport,
  format: GapExportFormat,
): Promise<GapExportResult> {
  const response = await fetch("/api/gap/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ format, report }),
  });

  if (!response.ok) {
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      /* empty body is fine */
    }
    const detail =
      payload &&
      typeof payload === "object" &&
      "detail" in payload &&
      typeof (payload as { detail: unknown }).detail === "string"
        ? (payload as { detail: string }).detail
        : `Export failed (${response.status})`;
    throw new ApiError(detail, response.status, payload);
  }

  const blob = await response.blob();
  const filename = parseContentDispositionFilename(
    response.headers.get("content-disposition"),
    `gap-report.${format === "json" ? "json" : "txt"}`,
  );
  return { blob, filename };
}

export const api = {
  // ── Probe / identity ──────────────────────────────────────────────────
  health: () => request<HealthResponse>("/api/health"),
  version: () => request<VersionResponse>("/api/version"),
  llmStatus: () => request<LlmStatusResponse>("/api/llm-status"),

  // ── Doctor / air-gap ──────────────────────────────────────────────────
  doctor: () =>
    request<{ subsystems: Array<{ name: string; status: string; detail: string }> }>(
      "/api/doctor",
    ),
  doctorCheckAirGap: () =>
    request<AirGapCheckResponse>("/api/doctor/check-air-gap", { method: "POST" }),

  // ── Config ────────────────────────────────────────────────────────────
  getConfig: () => request<EvidentiaConfig>("/api/config"),
  putConfig: (cfg: EvidentiaConfig) =>
    request<EvidentiaConfig>("/api/config", {
      method: "PUT",
      body: JSON.stringify(cfg),
    }),

  // ── Frameworks ────────────────────────────────────────────────────────
  listFrameworks: (params?: { tier?: string; category?: string }) => {
    const search = new URLSearchParams();
    if (params?.tier) search.set("tier", params.tier);
    if (params?.category) search.set("category", params.category);
    const qs = search.toString();
    return request<FrameworkListResponse>(
      `/api/frameworks${qs ? `?${qs}` : ""}`,
    );
  },
  getFramework: (id: string) =>
    request<ControlCatalog>(`/api/frameworks/${encodeURIComponent(id)}`),
  getControl: (frameworkId: string, controlId: string) =>
    request<CatalogControl>(
      `/api/frameworks/${encodeURIComponent(frameworkId)}/controls/${encodeURIComponent(
        controlId,
      )}`,
    ),

  // ── Gaps ──────────────────────────────────────────────────────────────
  listGapReports: () => request<GapReportListResponse>("/api/gap/reports"),
  getGapReport: (key: string) =>
    request<GapAnalysisReport>(`/api/gap/reports/${key}`),
  gapDiff: (baseKey: string, headKey: string) =>
    request<GapDiff>("/api/gap/diff", {
      method: "POST",
      body: JSON.stringify({ base_key: baseKey, head_key: headKey }),
    }),

  // ── Init wizard ───────────────────────────────────────────────────────
  initWizard: (payload: InitWizardRequest) =>
    request<InitWizardResponse>("/api/init/wizard", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
