import { FileUp, PlayCircle, Sparkles, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Button, type ButtonProps } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useWizardStore, type WizardPath } from "@/lib/wizard-store";

/**
 * First-run onboarding path chooser — the 3-card grid users see on the
 * Home page when no `evidentia.yaml` exists yet.
 */
export function PathChooser() {
  const setPath = useWizardStore((s) => s.setPath);

  const cards: Array<{
    icon: LucideIcon;
    title: string;
    btn: string;
    variant: ButtonProps["variant"];
    path: WizardPath;
    desc: ReactNode;
  }> = [
    {
      icon: PlayCircle,
      title: "Try sample data",
      btn: "Load sample",
      variant: "default",
      path: "sample",
      desc: (
        <>
          Load the <em>Meridian Financial</em> fintech example (48 controls,
          3 frameworks). The fastest way to see what Evidentia does — no
          setup required.
        </>
      ),
    },
    {
      icon: FileUp,
      title: "Upload inventory",
      btn: "Upload file",
      variant: "outline",
      path: "upload",
      desc: (
        <>
          Drag-drop a CSV, YAML, or OSCAL JSON inventory you've already
          exported from another tool. Evidentia auto-detects the format.
        </>
      ),
    },
    {
      icon: Sparkles,
      title: "Start from scratch",
      btn: "Start wizard",
      variant: "outline",
      path: "wizard",
      desc: (
        <>
          Answer four questions about your org and we'll generate a tailored
          starter inventory + recommended frameworks.
        </>
      ),
    },
  ];

  return (
    <section aria-labelledby="onboarding-heading" className="stack-4">
      <header>
        <h2 id="onboarding-heading" className="h2-lg">
          Let's get you started
        </h2>
        <p className="page-sub">
          Pick the path that matches how much structured data you have today.
        </p>
      </header>
      <div className="grid-3">
        {cards.map((c) => {
          const Ic = c.icon;
          return (
            <Card key={c.title} className="card-hover">
              <CardHeader>
                <span className="icon-tile">
                  <Ic className="ic" aria-hidden />
                </span>
                <CardTitle className="lg">{c.title}</CardTitle>
                <CardDescription>{c.desc}</CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  variant={c.variant}
                  className="full"
                  onClick={() => setPath(c.path)}
                >
                  {c.btn}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
