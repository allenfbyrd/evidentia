import type { BadgeProps } from "@/components/ui/badge";
import type { GapSeverity } from "@/types/api";

/** Map Evidentia severity enum values -> shadcn Badge variants. */
export function severityBadge(severity: GapSeverity): BadgeProps["variant"] {
  switch (severity) {
    case "critical":
      return "critical";
    case "high":
      return "high";
    case "medium":
      return "medium";
    case "low":
      return "low";
    case "informational":
      return "informational";
  }
}

/** Integer rank used for sorting (critical=4 ... informational=0). */
export const SEVERITY_RANK: Record<GapSeverity, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
  informational: 0,
};
