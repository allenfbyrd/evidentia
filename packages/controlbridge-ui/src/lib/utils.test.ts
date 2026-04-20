import { describe, expect, it } from "vitest";

import { cn } from "@/lib/utils";

describe("cn (Tailwind class merger)", () => {
  it("joins simple class strings", () => {
    expect(cn("p-4", "bg-red-500")).toBe("p-4 bg-red-500");
  });

  it("later classes override earlier conflicts", () => {
    // Tailwind merge rule: px-4 -> px-2 in favor of the later value.
    expect(cn("px-4 py-2", "px-2")).toBe("py-2 px-2");
  });

  it("filters falsy inputs", () => {
    expect(cn("a", null, undefined, false, "", "b")).toBe("a b");
  });

  it("accepts conditional object syntax", () => {
    expect(cn("base", { active: true, disabled: false })).toBe("base active");
  });
});
