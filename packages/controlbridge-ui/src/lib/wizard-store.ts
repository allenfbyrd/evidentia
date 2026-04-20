/**
 * Zustand store for the onboarding-wizard state machine.
 *
 * The wizard has three entry paths on the Home page:
 *   - "sample"   -> load the Meridian v2 demo inventory
 *   - "upload"   -> drag-drop an existing inventory file
 *   - "wizard"   -> answer a few questions; generate starter YAMLs
 *                   via POST /api/init/wizard
 *
 * Each path has its own state shape. Only one can be active at a time.
 */

import { create } from "zustand";

import type { InitWizardResponse } from "@/types/api";

export type WizardPath = "sample" | "upload" | "wizard" | null;

export type WizardStep =
  | "path-chooser"
  | "wizard-form"
  | "wizard-preview"
  | "upload-form"
  | "sample-loaded"
  | "done";

export interface WizardFormState {
  organization: string;
  system_name: string;
  industry: string;
  hosting: string;
  data_classification: string[];
  regulatory_requirements: string[];
  preset:
    | "soc2-starter"
    | "nist-moderate-starter"
    | "hipaa-starter"
    | "cmmc-starter"
    | "empty";
}

const EMPTY_FORM: WizardFormState = {
  organization: "",
  system_name: "",
  industry: "saas",
  hosting: "aws",
  data_classification: ["PII"],
  regulatory_requirements: [],
  preset: "nist-moderate-starter",
};

interface WizardStore {
  path: WizardPath;
  step: WizardStep;
  form: WizardFormState;
  preview: InitWizardResponse | null;
  uploadFile: File | null;
  setPath: (path: WizardPath) => void;
  setStep: (step: WizardStep) => void;
  updateForm: (patch: Partial<WizardFormState>) => void;
  setPreview: (preview: InitWizardResponse | null) => void;
  setUploadFile: (file: File | null) => void;
  reset: () => void;
}

export const useWizardStore = create<WizardStore>((set) => ({
  path: null,
  step: "path-chooser",
  form: EMPTY_FORM,
  preview: null,
  uploadFile: null,
  setPath: (path) => {
    if (path === null) {
      set({ path: null, step: "path-chooser" });
    } else if (path === "sample") {
      set({ path, step: "sample-loaded" });
    } else if (path === "upload") {
      set({ path, step: "upload-form" });
    } else {
      set({ path, step: "wizard-form" });
    }
  },
  setStep: (step) => set({ step }),
  updateForm: (patch) =>
    set((s) => ({ form: { ...s.form, ...patch } })),
  setPreview: (preview) => set({ preview }),
  setUploadFile: (uploadFile) => set({ uploadFile }),
  reset: () =>
    set({
      path: null,
      step: "path-chooser",
      form: EMPTY_FORM,
      preview: null,
      uploadFile: null,
    }),
}));

export const INDUSTRIES = [
  { value: "saas", label: "SaaS / software" },
  { value: "fintech", label: "Fintech / payments" },
  { value: "healthtech", label: "Health-tech / healthcare" },
  { value: "ecommerce", label: "E-commerce / retail" },
  { value: "govcon", label: "Government contractor / DoD" },
  { value: "other", label: "Other" },
] as const;

export const HOSTINGS = [
  { value: "aws", label: "AWS" },
  { value: "azure", label: "Azure" },
  { value: "gcp", label: "GCP" },
  { value: "hybrid", label: "Hybrid cloud / multi-cloud" },
  { value: "on-prem", label: "On-premises" },
] as const;

export const DATA_TYPES = [
  { value: "PII", label: "PII (personally identifiable)" },
  { value: "PCI-CDE", label: "PCI-CDE (cardholder data)" },
  { value: "PHI", label: "PHI (protected health info)" },
  { value: "CUI", label: "CUI (controlled unclassified)" },
  { value: "Financial", label: "Financial records" },
  { value: "Intellectual Property", label: "IP / trade secrets" },
] as const;

export const REGULATORY_OPTIONS = [
  { value: "SOC 2", label: "SOC 2" },
  { value: "HIPAA", label: "HIPAA" },
  { value: "PCI DSS", label: "PCI DSS" },
  { value: "GDPR", label: "GDPR" },
  { value: "CCPA", label: "CCPA" },
  { value: "FedRAMP", label: "FedRAMP" },
  { value: "CMMC", label: "CMMC" },
  { value: "ISO 27001", label: "ISO 27001" },
] as const;

export const PRESETS = [
  {
    value: "nist-moderate-starter",
    label: "NIST 800-53 Moderate starter (6 controls)",
  },
  {
    value: "soc2-starter",
    label: "SOC 2 starter (5 controls using CC6.x / CC7.x IDs)",
  },
  {
    value: "hipaa-starter",
    label: "HIPAA starter (6 controls using 164.x IDs)",
  },
  {
    value: "cmmc-starter",
    label: "CMMC Level 2 / NIST 800-171 starter (5 controls)",
  },
  { value: "empty", label: "Empty (add controls manually)" },
] as const;
