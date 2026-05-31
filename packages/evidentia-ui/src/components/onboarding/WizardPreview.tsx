import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useWizardStore } from "@/lib/wizard-store";

/**
 * Renders the three generated YAML files + recommended framework list
 * returned by /api/init/wizard. Each file has a Copy button so users
 * can paste into their editor of choice.
 *
 * v0.4.1 does NOT automatically write the files to the server — that's
 * an explicit safety rail so the wizard can't silently clobber existing
 * files. A future "Commit to disk" button is queued for v0.4.2.
 */
export function WizardPreview() {
  const { preview, reset, setStep } = useWizardStore();

  if (!preview) {
    return null;
  }

  return (
    <section aria-labelledby="preview-heading" className="stack-6">
      <header className="row-between gap-4">
        <div>
          <h2 id="preview-heading" className="h2-lg">
            Your starter files
          </h2>
          <p className="page-sub">
            Three YAML files tailored to your answers. Copy them into your
            project directory or let the wizard write them on disk.
          </p>
        </div>
        <Button variant="ghost" onClick={() => setStep("wizard-form")}>
          Edit answers
        </Button>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="lg">Recommended frameworks</CardTitle>
          <CardDescription>
            Based on your industry, hosting, data types, and regulatory scope.
            These are suggestions — add or remove any you don't need.
          </CardDescription>
        </CardHeader>
        <CardContent className="row wrap gap-2">
          {preview.recommended_frameworks.map((fw) => (
            <Badge key={fw} variant="secondary">
              {fw}
            </Badge>
          ))}
        </CardContent>
      </Card>

      <Tabs defaultValue="evidentia" className="w-full">
        <TabsList>
          <TabsTrigger value="evidentia">evidentia.yaml</TabsTrigger>
          <TabsTrigger value="controls">my-controls.yaml</TabsTrigger>
          <TabsTrigger value="context">system-context.yaml</TabsTrigger>
        </TabsList>
        <TabsContent value="evidentia">
          <YamlCard filename="evidentia.yaml" content={preview.evidentia_yaml} />
        </TabsContent>
        <TabsContent value="controls">
          <YamlCard
            filename="my-controls.yaml"
            content={preview.my_controls_yaml}
          />
        </TabsContent>
        <TabsContent value="context">
          <YamlCard
            filename="system-context.yaml"
            content={preview.system_context_yaml}
          />
        </TabsContent>
      </Tabs>

      <footer className="row-end gap-3 pt-4">
        <Button variant="outline" onClick={reset}>
          Start over
        </Button>
        <Button onClick={() => setStep("done")}>Done</Button>
      </footer>
    </section>
  );
}

function YamlCard({ filename, content }: { filename: string; content: string }) {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };
  return (
    <Card>
      <CardHeader className="row-between pb-3">
        <CardTitle className="base mono">{filename}</CardTitle>
        <Button
          size="sm"
          variant="outline"
          onClick={onCopy}
          aria-label={`Copy ${filename}`}
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5" /> Copied
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" /> Copy
            </>
          )}
        </Button>
      </CardHeader>
      <CardContent>
        <pre className="block scroll-72">
          <code>{content}</code>
        </pre>
      </CardContent>
    </Card>
  );
}
