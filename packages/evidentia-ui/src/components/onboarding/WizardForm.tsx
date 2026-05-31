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
      className="stack-6"
      onSubmit={(e) => {
        e.preventDefault();
        if (canSubmit) mutation.mutate();
      }}
    >
      <div className="row-between">
        <h2 className="h2-lg">About your organization</h2>
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

      <div className="grid-2">
        <div className="stack-2">
          <Label htmlFor="org">Organization name</Label>
          <Input
            id="org"
            required
            value={form.organization}
            onChange={(e) => updateForm({ organization: e.target.value })}
            placeholder="Acme Corporation"
          />
        </div>
        <div className="stack-2">
          <Label htmlFor="system-name">System / product name (optional)</Label>
          <Input
            id="system-name"
            value={form.system_name}
            onChange={(e) => updateForm({ system_name: e.target.value })}
            placeholder="Acme Customer Portal"
          />
        </div>
      </div>

      <fieldset className="stack-2" style={{ border: 0, padding: 0, margin: 0 }}>
        <legend className="label">Industry</legend>
        <div className="row wrap gap-2">
          {INDUSTRIES.map((opt) => (
            <button
              key={opt.value}
              type="button"
              role="radio"
              aria-checked={form.industry === opt.value}
              className={cn("seg", form.industry === opt.value && "on")}
              onClick={() => updateForm({ industry: opt.value })}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="stack-2" style={{ border: 0, padding: 0, margin: 0 }}>
        <legend className="label">Hosting</legend>
        <div className="row wrap gap-2">
          {HOSTINGS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              role="radio"
              aria-checked={form.hosting === opt.value}
              className={cn("seg", form.hosting === opt.value && "on")}
              onClick={() => updateForm({ hosting: opt.value })}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="stack-2" style={{ border: 0, padding: 0, margin: 0 }}>
        <legend className="label">Data handled</legend>
        <div className="row wrap gap-2">
          {DATA_TYPES.map((opt) => (
            <button
              key={opt.value}
              type="button"
              aria-pressed={form.data_classification.includes(opt.value)}
              className={cn(
                "pill",
                form.data_classification.includes(opt.value) && "on",
              )}
              onClick={() =>
                updateForm({
                  data_classification: toggle(
                    form.data_classification,
                    opt.value,
                  ),
                })
              }
            >
              {opt.label}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="stack-2" style={{ border: 0, padding: 0, margin: 0 }}>
        <legend className="label">Regulatory requirements (optional)</legend>
        <div className="row wrap gap-2">
          {REGULATORY_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              aria-pressed={form.regulatory_requirements.includes(opt.value)}
              className={cn(
                "pill",
                form.regulatory_requirements.includes(opt.value) && "on",
              )}
              onClick={() =>
                updateForm({
                  regulatory_requirements: toggle(
                    form.regulatory_requirements,
                    opt.value,
                  ),
                })
              }
            >
              {opt.label}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="stack-2" style={{ border: 0, padding: 0, margin: 0 }}>
        <legend className="label">Starter control preset</legend>
        <div className="stack-2">
          {PRESETS.map((opt) => (
            <label
              key={opt.value}
              className={cn("select-row", form.preset === opt.value && "on")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                cursor: "pointer",
              }}
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

      <div className="row-end gap-3">
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

function toggle<T>(arr: T[], value: T): T[] {
  return arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value];
}
