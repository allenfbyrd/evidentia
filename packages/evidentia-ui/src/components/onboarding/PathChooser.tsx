import { FileUp, PlayCircle, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useWizardStore } from "@/lib/wizard-store";

/**
 * First-run onboarding path chooser — the 3-card grid users see on the
 * Home page when no `evidentia.yaml` exists yet.
 */
export function PathChooser() {
  const setPath = useWizardStore((s) => s.setPath);

  return (
    <section aria-labelledby="onboarding-heading" className="space-y-4">
      <header>
        <h2 id="onboarding-heading" className="text-2xl font-semibold">
          Let's get you started
        </h2>
        <p className="mt-1 text-muted-foreground">
          Pick the path that matches how much structured data you have today.
        </p>
      </header>
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <PlayCircle className="h-6 w-6 text-primary" aria-hidden />
            <CardTitle className="text-lg">Try sample data</CardTitle>
            <CardDescription>
              Load the <em>Meridian Financial</em> fintech example (48 controls,
              3 frameworks). The fastest way to see what Evidentia does —
              no setup required.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full" onClick={() => setPath("sample")}>
              Load sample
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <FileUp className="h-6 w-6 text-primary" aria-hidden />
            <CardTitle className="text-lg">Upload inventory</CardTitle>
            <CardDescription>
              Drag-drop a CSV, YAML, or OSCAL JSON inventory you've already
              exported from another tool. Evidentia auto-detects the
              format.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              className="w-full"
              variant="outline"
              onClick={() => setPath("upload")}
            >
              Upload file
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Sparkles className="h-6 w-6 text-primary" aria-hidden />
            <CardTitle className="text-lg">Start from scratch</CardTitle>
            <CardDescription>
              Answer four questions about your org and we'll generate a
              tailored starter inventory + recommended frameworks.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              className="w-full"
              variant="outline"
              onClick={() => setPath("wizard")}
            >
              Start wizard
            </Button>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
