import { useQuery } from "@tanstack/react-query";

import { PathChooser } from "@/components/onboarding/PathChooser";
import { SampleLoaded } from "@/components/onboarding/SampleLoaded";
import { UploadForm } from "@/components/onboarding/UploadForm";
import { WizardForm } from "@/components/onboarding/WizardForm";
import { WizardPreview } from "@/components/onboarding/WizardPreview";
import { api } from "@/lib/api";
import { useWizardStore } from "@/lib/wizard-store";

/**
 * Home / first-run onboarding.
 *
 * v0.4.1 wires the three-path wizard:
 *   - Sample data     -> SampleLoaded (walkthrough)
 *   - Upload          -> UploadForm (drag-drop + proceed)
 *   - Wizard from scratch -> WizardForm -> WizardPreview
 *
 * If the server already has a report in the gap store, the wizard is
 * collapsed and we redirect the user to the Dashboard summary.
 */
export function HomePage() {
  const step = useWizardStore((s) => s.step);

  // Peek at the gap-reports endpoint so we can show the "returning user"
  // variant when the store isn't empty.
  const reportsQuery = useQuery({
    queryKey: ["gap-reports"],
    queryFn: () => api.listGapReports(),
  });
  const hasReports = (reportsQuery.data?.total ?? 0) > 0;

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">
          Welcome to ControlBridge
        </h1>
        <p className="text-muted-foreground">
          Open-source GRC tool for gap analysis, risk statements, and
          compliance automation. The web UI is the accessible counterpart
          to the <code className="rounded bg-muted px-1 py-0.5">controlbridge</code>{" "}
          CLI.
        </p>
      </header>

      {step === "path-chooser" && <PathChooser />}
      {step === "wizard-form" && <WizardForm />}
      {step === "wizard-preview" && <WizardPreview />}
      {step === "upload-form" && <UploadForm />}
      {step === "sample-loaded" && <SampleLoaded />}
      {step === "done" && <DonePanel />}

      {hasReports && step === "path-chooser" && (
        <aside className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">
          You have {reportsQuery.data?.total} saved{" "}
          {reportsQuery.data?.total === 1 ? "report" : "reports"}. Head to
          the <a href="/dashboard" className="underline underline-offset-2">
            Dashboard
          </a>{" "}
          to review, or run a new analysis from the
          {" "}
          <a href="/gap/analyze" className="underline underline-offset-2">
            Gap Analyze
          </a>
          {" "}page.
        </aside>
      )}
    </div>
  );
}

function DonePanel() {
  const reset = useWizardStore((s) => s.reset);
  return (
    <section className="rounded-lg border bg-card p-6">
      <h2 className="text-xl font-semibold">Nice. Next steps:</h2>
      <ul className="mt-3 list-disc space-y-1 pl-6 text-sm">
        <li>
          Save the YAMLs in your project root
          (<code className="rounded bg-muted px-1 py-0.5">controlbridge.yaml</code>,
          <code className="mx-1 rounded bg-muted px-1 py-0.5">my-controls.yaml</code>,
          <code className="rounded bg-muted px-1 py-0.5">system-context.yaml</code>)
        </li>
        <li>
          Run <code className="rounded bg-muted px-1 py-0.5">
            controlbridge gap analyze
          </code>
        </li>
        <li>
          Come back to the <a className="underline underline-offset-2" href="/dashboard">Dashboard</a>{" "}
          to review gaps, or use
          the <a className="underline underline-offset-2" href="/gap/analyze">Gap Analyze</a>{" "}
          page to re-run without leaving the browser.
        </li>
      </ul>
      <div className="mt-4">
        <button
          type="button"
          onClick={reset}
          className="text-sm text-muted-foreground underline underline-offset-2"
        >
          Start wizard over
        </button>
      </div>
    </section>
  );
}
