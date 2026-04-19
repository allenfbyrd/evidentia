/** TypeScript mirrors of CatalogControl + ControlCatalog from
 *  controlbridge_core.models.catalog. */

export interface CatalogControl {
  id: string;
  title: string;
  description: string;
  family: string | null;
  class?: string | null;
  control_class?: string | null;
  priority?: string | null;
  baseline_impact: string[];
  enhancements: CatalogControl[];
  related_controls: string[];
  assessment_objectives: string[];
  objective?: string | null;
  guidance?: string | null;
  examples: string[];
  parameters: Record<string, string>;
  ordering?: number | null;
  tier?: string | null;
  license_required: boolean;
  license_url?: string | null;
  placeholder: boolean;
}

export interface ControlCatalog {
  framework_id: string;
  framework_name: string;
  version: string;
  source: string;
  controls: CatalogControl[];
  families: string[];
  family_hierarchy?: Record<string, string[]> | null;
  category: "control" | "technique" | "vulnerability" | "obligation";
  tier?: string | null;
  license_required: boolean;
  license_terms?: string | null;
  license_url?: string | null;
  placeholder: boolean;
}
