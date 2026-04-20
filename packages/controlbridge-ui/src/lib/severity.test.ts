import { describe, expect, it } from "vitest";

import { SEVERITY_RANK, severityBadge } from "@/lib/severity";
import type { GapSeverity } from "@/types/api";

describe("severity helpers", () => {
  it("maps each enum value to a badge variant", () => {
    expect(severityBadge("critical")).toBe("critical");
    expect(severityBadge("high")).toBe("high");
    expect(severityBadge("medium")).toBe("medium");
    expect(severityBadge("low")).toBe("low");
    expect(severityBadge("informational")).toBe("informational");
  });

  it("ranks critical highest, informational lowest", () => {
    const unsorted: GapSeverity[] = [
      "critical",
      "informational",
      "medium",
      "low",
      "high",
    ];
    const ordered = [...unsorted].sort(
      (a, b) => SEVERITY_RANK[a] - SEVERITY_RANK[b],
    );
    expect(ordered).toEqual([
      "informational",
      "low",
      "medium",
      "high",
      "critical",
    ]);
  });
});
