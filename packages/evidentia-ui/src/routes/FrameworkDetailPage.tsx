import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";

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

export function FrameworkDetailPage() {
  const { id } = useParams<{ id: string }>();
  const query = useQuery({
    queryKey: ["framework", id],
    queryFn: () => api.getFramework(id ?? ""),
    enabled: Boolean(id),
  });

  if (!id) {
    return <p className="text-destructive">No framework ID in URL.</p>;
  }

  if (query.isError) {
    return (
      <div className="space-y-4">
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle>Framework not found</CardTitle>
            <CardDescription>
              Could not load framework <code>{id}</code>.
            </CardDescription>
          </CardHeader>
        </Card>
        <Button asChild variant="outline">
          <Link to="/frameworks">Back to frameworks</Link>
        </Button>
      </div>
    );
  }

  if (!query.data) {
    return <p>Loading framework...</p>;
  }

  const catalog = query.data;

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <div className="flex items-center gap-2">
          <Badge variant="outline">Tier {catalog.tier ?? "?"}</Badge>
          <Badge variant="secondary">{catalog.category}</Badge>
          {catalog.placeholder && <Badge variant="destructive">placeholder</Badge>}
          {catalog.license_required && <Badge>license required</Badge>}
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">
          {catalog.framework_name}
        </h1>
        <p className="text-muted-foreground">
          <code className="rounded bg-muted px-1 py-0.5">
            {catalog.framework_id}
          </code>{" "}
          &middot; version {catalog.version} &middot;{" "}
          {catalog.controls.length} top-level controls ({catalog.families.length}{" "}
          families)
        </p>
      </header>

      {catalog.license_terms && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">License</CardTitle>
            <CardDescription>{catalog.license_terms}</CardDescription>
          </CardHeader>
        </Card>
      )}

      <section aria-labelledby="controls-list" className="space-y-3">
        <h2 id="controls-list" className="text-xl font-medium">
          Controls
        </h2>
        <ul className="space-y-2">
          {catalog.controls.map((ctrl) => (
            <li key={ctrl.id}>
              <Card>
                <CardHeader className="space-y-1 pb-3">
                  <div className="flex items-start justify-between gap-4">
                    <CardTitle className="text-base font-mono">
                      {ctrl.id}
                    </CardTitle>
                    {ctrl.family && (
                      <Badge variant="outline">{ctrl.family}</Badge>
                    )}
                  </div>
                  <CardDescription className="font-sans">
                    {ctrl.title}
                  </CardDescription>
                </CardHeader>
                {ctrl.description && !ctrl.placeholder && (
                  <CardContent className="pt-0 text-sm text-muted-foreground">
                    {ctrl.description.length > 300
                      ? `${ctrl.description.slice(0, 300)}...`
                      : ctrl.description}
                  </CardContent>
                )}
                {ctrl.placeholder && (
                  <CardContent className="pt-0 text-sm text-muted-foreground">
                    <span className="italic">
                      Placeholder control. Supply your licensed copy via{" "}
                      <code className="rounded bg-muted px-1 py-0.5">
                        evidentia catalog import
                      </code>
                      .
                    </span>
                  </CardContent>
                )}
              </Card>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
