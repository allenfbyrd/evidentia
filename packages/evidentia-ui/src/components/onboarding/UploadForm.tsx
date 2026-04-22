import { Upload } from "lucide-react";
import { useRef, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { useWizardStore } from "@/lib/wizard-store";

/**
 * "Upload inventory" path. v0.4.1 guides the user to the Gap Analyze
 * page — which handles the actual upload + analysis in one step. This
 * screen is a signpost + format-support documentation.
 */
export function UploadForm() {
  const reset = useWizardStore((s) => s.reset);
  const setUploadFile = useWizardStore((s) => s.setUploadFile);
  const fileInput = useRef<HTMLInputElement | null>(null);
  const [droppedName, setDroppedName] = useState<string | null>(null);

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const f = files[0];
    setUploadFile(f);
    setDroppedName(f.name);
  };

  return (
    <section aria-labelledby="upload-heading" className="space-y-4">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h2 id="upload-heading" className="text-2xl font-semibold">
            Upload an inventory
          </h2>
          <p className="mt-1 text-muted-foreground">
            We auto-detect the format based on the file extension.
          </p>
        </div>
        <Button variant="ghost" onClick={reset}>
          Cancel
        </Button>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Supported formats</CardTitle>
          <CardDescription>
            YAML / JSON / CSV. OSCAL component definitions and CISO Assistant
            exports are parsed automatically. CSV expects columns
            <code className="mx-1 rounded bg-muted px-1">id</code>,
            <code className="mx-1 rounded bg-muted px-1">title</code>, and
            <code className="mx-1 rounded bg-muted px-1">status</code>.
          </CardDescription>
        </CardHeader>
      </Card>

      <div
        className={cn(
          "rounded-lg border-2 border-dashed p-8 text-center",
          droppedName ? "border-primary bg-primary/5" : "border-muted-foreground/30",
        )}
        onDragOver={(e) => {
          e.preventDefault();
        }}
        onDrop={(e) => {
          e.preventDefault();
          handleFiles(e.dataTransfer.files);
        }}
      >
        <Upload className="mx-auto h-10 w-10 text-muted-foreground" aria-hidden />
        <p className="mt-3 text-sm font-medium">
          {droppedName ?? "Drag your inventory file here"}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          or click to browse
        </p>
        <input
          ref={fileInput}
          type="file"
          accept=".yaml,.yml,.json,.csv"
          className="sr-only"
          id="inventory-upload"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <Label
          htmlFor="inventory-upload"
          className="mt-4 inline-block cursor-pointer"
        >
          <Button asChild size="sm" variant="outline">
            <span>Choose file</span>
          </Button>
        </Label>
      </div>

      {droppedName && (
        <Alert variant="success">
          <AlertTitle>File ready for analysis</AlertTitle>
          <AlertDescription>
            Head to <strong>Gap Analyze</strong> to pick frameworks and run
            the analysis.
          </AlertDescription>
        </Alert>
      )}

      <div className="flex justify-end">
        <Button
          asChild
          disabled={!droppedName}
          variant={droppedName ? "default" : "secondary"}
        >
          <a href="/gap/analyze">Continue to Gap Analyze</a>
        </Button>
      </div>
    </section>
  );
}
