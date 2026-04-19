/**
 * Typed API client for the ControlBridge REST backend.
 *
 * Thin fetch wrapper returning typed data or throwing `ApiError`. All hooks
 * in @/hooks/*.ts wrap these calls with TanStack Query for caching,
 * retries, and mutation state.
 *
 * Runtime base URL: always same-origin (production ships frontend + API
 * from one uvicorn instance). Dev mode: Vite's proxy forwards /api to :8000.
 */

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
import type { ControlBridgeConfig } from "@/types/config";

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
  getConfig: () => request<ControlBridgeConfig>("/api/config"),
  putConfig: (cfg: ControlBridgeConfig) =>
    request<ControlBridgeConfig>("/api/config", {
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
