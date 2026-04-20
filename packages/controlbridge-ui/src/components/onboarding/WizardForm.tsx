import { useMutation } from "@tanstack/react-query";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  DATA_TYPES,
  HOSTINGS,
  INDUSTRIES,
  PRESETS,
  REGULATORY_OPTIONS,
  useWizardStore,
} from "@/lib/wizard-store";

/**
 * The four-question wizard form. Submit -> POST /api/init/wizard ->
 * render the generated YAMLs + recommended frameworks in WizardPreview.
 */
export function WizardForm() {
  const { form, updateForm, setPreview, setStep, reset } = useWizardStore();

  const mutation = useMutation({
    mutationFn: () =>
      api.initWizard({
        organization: form.organization.trim(),
        system_name: form.system_name.trim() || null,
        industry: form.industry,
        hosting: form.hosting,
        data_classification: form.data_classification,
        regulatory_requirements: form.regulatory_requirements,
        preset: form.preset,
      }),
    onSuccess: (data) => {
      setPreview(data);
      setStep("wizard-preview");
    },
  });

  const canSubmit = form.organization.trim().length > 0 && !mutation.isPending;

  return (
    <form
      className="space-y-6"
      onSubmit={(e) => {
        e.preventDefault();
        if (canSubmit) mutation.mutate();
      }}
    >
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">About your organization</h2>
        <Button type="button" variant="ghost" size="sm" onClick={reset}>
          Cancel
        </Button>
      </div>

      {mutation.isError && (
        <Alert variant="destructive">
          <AlertTitle>Wizard failed</AlertTitle>
          <AlertDescription>
            {mutation.error instanceof Error
              ? mutation.error.message
              : "Unknown error. Check the server logs."}
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <Label htmlFor="org">Organization name</Label>
          <Input
            id="org"
            required
            value={form.organization}
            onChange={(e) => updateForm({ organization: e.target.value })}
            placeholder="Acme Corporation"
            className="mt-1"
          />
        </div>
        <div>
          <Label htmlFor="system-name">System / product name (optional)</Label>
          <Input
            id="system-name"
            value={form.system_name}
            onChange={(e) => updateForm({ system_name: e.target.value })}
            placeholder="Acme Customer Portal"
            className="mt-1"
          />
        </div>
      </div>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Industry</legend>
        <div className="flex flex-wrap gap-2">
          {INDUSTRIES.map((opt) => (
            <Radio
              key={opt.value}
              name="industry"
              value={opt.value}
              label={opt.label}
              checked={form.industry === opt.value}
              onSelect={() => updateForm({ industry: opt.value })}
            />
          ))}
        </div>
      </fieldset>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Hosting</legend>
        <div className="flex flex-wrap gap-2">
          {HOSTINGS.map((opt) => (
            <Radio
              key={opt.value}
              name="hosting"
              value={opt.value}
              label={opt.label}
              checked={form.hosting === opt.value}
              onSelect={() => updateForm({ hosting: opt.value })}
            />
          ))}
        </div>
      </fieldset>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Data handled</legend>
        <div className="flex flex-wrap gap-2">
          {DATA_TYPES.map((opt) => (
            <MultiPill
              key={opt.value}
              label={opt.label}
              checked={form.data_classification.includes(opt.value)}
              onToggle={() =>
                updateForm({
                  data_classification: toggle(
                    form.data_classification,
                    opt.value,
                  ),
                })
              }
            />
          ))}
        </div>
      </fieldset>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">
          Regulatory requirements (optional)
        </legend>
        <div className="flex flex-wrap gap-2">
          {REGULATORY_OPTIONS.map((opt) => (
            <MultiPill
              key={opt.value}
              label={opt.label}
              checked={form.regulatory_requirements.includes(opt.value)}
              onToggle={() =>
                updateForm({
                  regulatory_requirements: toggle(
                    form.regulatory_requirements,
                    opt.value,
                  ),
                })
              }
            />
          ))}
        </div>
      </fieldset>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">
          Starter control preset
        </legend>
        <div className="space-y-1">
          {PRESETS.map((opt) => (
            <label
              key={opt.value}
              className={cn(
                "flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors",
                form.preset === opt.value
                  ? "border-primary bg-primary/5"
                  : "hover:bg-accent/50",
              )}
            >
              <input
                type="radio"
                name="preset"
                value={opt.value}
                checked={form.preset === opt.value}
                onChange={() =>
                  updateForm({
                    preset: opt.value as typeof form.preset,
                  })
                }
              />
              {opt.label}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="flex items-center justify-end gap-3">
        <Button type="button" variant="outline" onClick={reset}>
          Start over
        </Button>
        <Button type="submit" disabled={!canSubmit}>
          {mutation.isPending ? "Generating..." : "Preview starter files"}
        </Button>
      </div>
    </form>
  );
}

function Radio(props: {
  name: string;
  value: string;
  label: string;
  checked: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={props.checked}
      onClick={props.onSelect}
      className={cn(
        "rounded-md border px-3 py-1.5 text-sm transition-colors",
        props.checked
          ? "border-primary bg-primary text-primary-foreground"
          : "hover:bg-accent",
      )}
    >
      {props.label}
    </button>
  );
}

function MultiPill(props: {
  label: string;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={props.checked}
      onClick={props.onToggle}
      className={cn(
        "rounded-full border px-3 py-1 text-xs transition-colors",
        props.checked
          ? "border-primary bg-primary text-primary-foreground"
          : "hover:bg-accent",
      )}
    >
      {props.label}
    </button>
  );
}

function toggle<T>(arr: T[], value: T): T[] {
  return arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value];
}
