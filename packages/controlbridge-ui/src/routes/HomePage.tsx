import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/**
 * Home / landing page.
 *
 * v0.4.0-alpha.1: static welcome + quick-nav cards. Interactive
 * onboarding wizard (3-path chooser) lands in v0.4.0-alpha.2.
 */
export function HomePage() {
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">
          Welcome to ControlBridge
        </h1>
        <p className="text-muted-foreground">
          Open-source GRC tool for gap analysis, risk statements, and
          compliance automation. The web UI is the accessible counterpart to
          the <code className="rounded bg-muted px-1 py-0.5">controlbridge</code>{" "}
          CLI.
        </p>
      </header>

      <section
        className="grid gap-4 md:grid-cols-3"
        aria-labelledby="quick-actions"
      >
        <h2 id="quick-actions" className="sr-only">
          Quick actions
        </h2>
        <Card>
          <CardHeader>
            <CardTitle>Explore frameworks</CardTitle>
            <CardDescription>
              Browse 82 bundled catalogs — NIST 800-53, SOC 2, HIPAA, CMMC,
              ISO 27001, and more.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline">
              <Link to="/frameworks">Open frameworks</Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>See your gaps</CardTitle>
            <CardDescription>
              Review the most recent gap analysis results and historical
              snapshots from the gap store.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline">
              <Link to="/dashboard">Open dashboard</Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Configure</CardTitle>
            <CardDescription>
              Edit <code>controlbridge.yaml</code>, pick an LLM provider,
              and toggle air-gapped mode.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline">
              <Link to="/settings">Open settings</Link>
            </Button>
          </CardContent>
        </Card>
      </section>

      <section
        aria-labelledby="cli-intro"
        className="rounded-lg border bg-card p-6"
      >
        <h2 id="cli-intro" className="text-xl font-medium">
          Prefer the terminal?
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Every page in this UI mirrors a CLI command. Run{" "}
          <code className="rounded bg-muted px-1 py-0.5">controlbridge init</code>{" "}
          to bootstrap a project, then{" "}
          <code className="rounded bg-muted px-1 py-0.5">
            controlbridge gap analyze
          </code>
          . The web UI and CLI share the same data models and config.
        </p>
        <pre className="mt-4 overflow-x-auto rounded bg-muted p-3 text-sm">
          <code>
            controlbridge init{"\n"}
            controlbridge gap analyze --inventory my-controls.yaml
            {"\n"}
            # or run the web UI:{"\n"}
            controlbridge serve
          </code>
        </pre>
      </section>
    </div>
  );
}
