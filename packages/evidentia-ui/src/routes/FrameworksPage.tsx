import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Frameworks browser — lists all 82 bundled catalogs, filterable by tier
 * + category + free-text search.
 */
export function FrameworksPage() {
  const [tierFilter, setTierFilter] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const query = useQuery({
    queryKey: ["frameworks", tierFilter, categoryFilter],
    queryFn: () =>
      api.listFrameworks({
        tier: tierFilter ?? undefined,
        category: categoryFilter ?? undefined,
      }),
  });

  const filtered = useMemo(() => {
    if (!query.data) return [];
    const needle = search.trim().toLowerCase();
    if (!needle) return query.data.frameworks;
    return query.data.frameworks.filter(
      (fw) =>
        fw.id.toLowerCase().includes(needle) ||
        fw.name.toLowerCase().includes(needle),
    );
  }, [query.data, search]);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Frameworks</h1>
        <p className="mt-1 text-muted-foreground">
          {query.data
            ? `${filtered.length} of ${query.data.total} catalogs`
            : "Loading catalogs..."}
        </p>
      </header>

      <section className="flex flex-wrap gap-3" aria-label="Filters">
        <input
          type="search"
          className="flex-1 min-w-64 rounded-md border bg-background px-3 py-2 text-sm"
          placeholder="Search by ID or name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search frameworks"
        />
        <TierFilter current={tierFilter} onChange={setTierFilter} />
        <CategoryFilter current={categoryFilter} onChange={setCategoryFilter} />
      </section>

      {query.isError && (
        <Card className="border-destructive">
          <CardContent className="p-6 text-sm text-destructive">
            Could not fetch frameworks. Is the backend running?
          </CardContent>
        </Card>
      )}

      {query.isSuccess && filtered.length === 0 && (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            No frameworks match your filters.
          </CardContent>
        </Card>
      )}

      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((fw) => (
          <li key={fw.id}>
            <Link
              to={`/frameworks/${encodeURIComponent(fw.id)}`}
              className="group block h-full"
            >
              <Card className="h-full transition-colors group-hover:border-primary">
                <CardHeader className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">Tier {fw.tier}</Badge>
                    <Badge variant="secondary">{fw.category}</Badge>
                    {fw.placeholder === "true" && (
                      <Badge variant="destructive">placeholder</Badge>
                    )}
                  </div>
                  <CardTitle className="text-base">{fw.name}</CardTitle>
                </CardHeader>
                <CardContent className="pt-0 text-xs text-muted-foreground">
                  <code className="rounded bg-muted px-1 py-0.5">{fw.id}</code>{" "}
                  &middot; {fw.version}
                </CardContent>
              </Card>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

function TierFilter({
  current,
  onChange,
}: {
  current: string | null;
  onChange: (value: string | null) => void;
}) {
  const options: { value: string | null; label: string }[] = [
    { value: null, label: "All tiers" },
    { value: "A", label: "Tier A (public)" },
    { value: "B", label: "Tier B (free-restricted)" },
    { value: "C", label: "Tier C (licensed)" },
    { value: "D", label: "Tier D (regulation)" },
  ];
  return (
    <div className="flex gap-1" role="radiogroup" aria-label="Filter by tier">
      {options.map((opt) => (
        <button
          key={opt.value ?? "all"}
          type="button"
          role="radio"
          aria-checked={current === opt.value}
          onClick={() => onChange(opt.value)}
          className={cn(
            "rounded-md px-2 py-1 text-xs transition-colors",
            current === opt.value
              ? "bg-primary text-primary-foreground"
              : "bg-secondary text-secondary-foreground hover:bg-accent",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

function CategoryFilter({
  current,
  onChange,
}: {
  current: string | null;
  onChange: (value: string | null) => void;
}) {
  const options: { value: string | null; label: string }[] = [
    { value: null, label: "All types" },
    { value: "control", label: "Control" },
    { value: "technique", label: "Technique" },
    { value: "vulnerability", label: "Vulnerability" },
    { value: "obligation", label: "Obligation" },
  ];
  return (
    <div
      className="flex gap-1"
      role="radiogroup"
      aria-label="Filter by category"
    >
      {options.map((opt) => (
        <button
          key={opt.value ?? "all"}
          type="button"
          role="radio"
          aria-checked={current === opt.value}
          onClick={() => onChange(opt.value)}
          className={cn(
            "rounded-md px-2 py-1 text-xs transition-colors",
            current === opt.value
              ? "bg-primary text-primary-foreground"
              : "bg-secondary text-secondary-foreground hover:bg-accent",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
