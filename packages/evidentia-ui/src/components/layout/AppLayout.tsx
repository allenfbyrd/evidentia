import { Fragment } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, Outlet, useLocation } from "react-router-dom";

import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

type NavMeta = { label: string; description: string; crumb: string };

/** Route metadata — colocated with the layout so adding a route is one edit. */
const NAV_META: Record<string, NavMeta> = {
  "/": { label: "Home", description: "Welcome + onboarding", crumb: "Welcome to Evidentia" },
  "/dashboard": { label: "Dashboard", description: "Saved gap reports", crumb: "Saved gap reports" },
  "/frameworks": { label: "Frameworks", description: "92 bundled catalogs", crumb: "Catalog browser" },
  "/gap/analyze": { label: "Gap Analyze", description: "Run a gap analysis", crumb: "Run a gap analysis" },
  "/gap/diff": { label: "Gap Diff", description: "Compare two reports", crumb: "Compare two reports" },
  "/risk/generate": { label: "Risk Generate", description: "AI risk statements", crumb: "AI risk statements" },
  "/settings": { label: "Settings", description: "Config + LLM + air-gap", crumb: "Configuration" },
};

/** Grouped navigation rail. */
const NAV_GROUPS: { label: string | null; items: string[] }[] = [
  { label: null, items: ["/"] },
  { label: "Analyze", items: ["/gap/analyze", "/gap/diff", "/risk/generate"] },
  { label: "Library", items: ["/dashboard", "/frameworks"] },
  { label: "Configure", items: ["/settings"] },
];

function isActive(to: string, path: string): boolean {
  return to === "/" ? path === "/" : path.startsWith(to);
}

function crumbFor(path: string): { label: string; crumb: string } {
  if (path.startsWith("/frameworks/")) {
    return { label: "Frameworks", crumb: "Catalog detail" };
  }
  const key = NAV_GROUPS.flatMap((g) => g.items).find((k) => isActive(k, path)) ?? "/";
  const m = NAV_META[key];
  return m ? { label: m.label, crumb: m.crumb } : { label: "Evidentia", crumb: "" };
}

export function AppLayout() {
  const { pathname } = useLocation();

  const { data: health, isError: healthError } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.health(),
    refetchInterval: 15_000,
  });

  const { data: airGap } = useQuery({
    queryKey: ["air-gap"],
    queryFn: () => api.doctorCheckAirGap(),
    staleTime: 60_000,
  });

  const connected = health?.status === "ok" && !healthError;
  const offline = Boolean(airGap?.air_gapped);
  const { label: crumbLabel, crumb } = crumbFor(pathname);

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      {/* ── Deep-navy brand nav rail ── */}
      <aside
        className="sticky top-0 flex h-screen w-64 shrink-0 flex-col border-r border-chrome-border bg-chrome text-chrome-foreground"
        aria-label="Primary navigation"
      >
        <Link to="/" className="flex items-center gap-3 px-5 pb-4 pt-5">
          <img
            src="/logo-transparent-background/evidentia-mark-cream.svg"
            alt=""
            className="h-9 w-auto shrink-0"
          />
          <span className="flex flex-col leading-tight">
            <span className="text-lg font-semibold tracking-tight text-cream">Evidentia</span>
            <span className="mt-0.5 text-[0.66rem] uppercase tracking-[0.06em] text-chrome-muted">
              Compliance console
            </span>
          </span>
        </Link>

        <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-3 pb-4">
          {NAV_GROUPS.map((group, i) => (
            <Fragment key={group.label ?? `g${i}`}>
              {group.label && (
                <div className="px-2.5 pb-1 pt-4 text-[0.65rem] font-semibold uppercase tracking-[0.09em] text-chrome-muted">
                  {group.label}
                </div>
              )}
              {group.items.map((to) => {
                const active = isActive(to, pathname);
                const m = NAV_META[to];
                if (!m) return null;
                return (
                  <Link
                    key={to}
                    to={to}
                    className={cn(
                      "relative flex flex-col rounded-md px-2.5 py-2 transition-colors",
                      active
                        ? "bg-chrome-active text-cream-soft"
                        : "text-[hsl(var(--chrome-fg)/0.82)] hover:bg-chrome-hover hover:text-chrome-foreground",
                    )}
                    aria-current={active ? "page" : undefined}
                  >
                    {active && (
                      <span
                        className="absolute -left-3 bottom-1.5 top-1.5 w-[3px] rounded-r bg-primary"
                        aria-hidden
                      />
                    )}
                    <span className="text-[0.86rem] font-medium">{m.label}</span>
                    <span
                      className={cn(
                        "truncate text-[0.68rem]",
                        active ? "text-[hsl(var(--chrome-fg)/0.6)]" : "text-chrome-muted",
                      )}
                    >
                      {m.description}
                    </span>
                  </Link>
                );
              })}
            </Fragment>
          ))}
        </nav>

        <div
          className="mx-3 mb-3.5 flex flex-col gap-2 rounded-md border border-chrome-border bg-[hsl(var(--chrome-bg-2)/0.6)] px-3 py-2.5"
          aria-label="Backend status"
        >
          <div className="flex items-center justify-between gap-2 text-[0.72rem]">
            <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-chrome-muted">
              <span
                className={cn("h-[7px] w-[7px] rounded-full", connected ? "bg-success" : "bg-destructive")}
                aria-hidden
              />
              Backend
            </span>
            <span className="font-mono text-[0.7rem] text-chrome-foreground">
              {health?.version ? `v${health.version}` : "…"}
            </span>
          </div>
          <div className="flex items-center justify-between gap-2 text-[0.72rem]">
            <span className="text-chrome-muted">Air-gap</span>
            {offline ? (
              <span className="rounded-full border border-[hsl(var(--primary)/0.5)] bg-[hsl(var(--primary)/0.16)] px-1.5 py-0.5 text-[0.64rem] font-semibold tracking-wide text-cream-soft">
                ready
              </span>
            ) : (
              <span className="font-mono text-[0.7rem] text-chrome-foreground">off</span>
            )}
          </div>
        </div>
      </aside>

      {/* ── Workspace ── */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-[58px] items-center justify-between gap-4 border-b border-border bg-[hsl(var(--background)/0.85)] px-8 backdrop-blur">
          <div className="flex items-center gap-2 text-[0.92rem]">
            <span className="font-semibold tracking-tight">{crumbLabel}</span>
            <span className="text-[0.8rem] text-muted-foreground">· {crumb}</span>
          </div>
          <nav className="flex items-center gap-3.5" aria-label="Connection status">
            {offline && (
              <span
                className="inline-flex items-center gap-1.5 rounded-full border border-border-strong px-2.5 py-1 text-[0.72rem] text-muted-foreground"
                title="All subsystems are air-gap ready."
              >
                air-gapped
              </span>
            )}
            <span
              className={cn(
                "inline-flex items-center gap-1.5 text-[0.8rem]",
                connected ? "text-muted-foreground" : "text-destructive",
              )}
              aria-live="polite"
            >
              <span
                className={cn("h-2 w-2 rounded-full", connected ? "bg-success" : "bg-destructive")}
                aria-hidden
              />
              {connected ? "connected" : "disconnected"}
            </span>
          </nav>
        </header>

        <main className="mx-auto w-full max-w-[1180px] flex-1 px-8 pb-12 pt-9">
          <Outlet />
        </main>

        <footer className="border-t border-border py-4 text-center text-[0.74rem] text-muted-foreground">
          Evidentia is open source under Apache-2.0. ·{" "}
          <a
            href="https://github.com/polycentric-labs/evidentia"
            className="underline-offset-[3px] hover:text-primary hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            Source on GitHub
          </a>
        </footer>
      </div>
    </div>
  );
}
