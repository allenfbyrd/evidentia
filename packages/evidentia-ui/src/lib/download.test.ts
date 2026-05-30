import { describe, expect, it, vi, afterEach } from "vitest";

import {
  parseContentDispositionFilename,
  triggerBlobDownload,
} from "@/lib/download";

describe("parseContentDispositionFilename", () => {
  it("extracts a quoted filename", () => {
    expect(
      parseContentDispositionFilename(
        'attachment; filename="Meridian-Financial.sarif"',
        "fallback.txt",
      ),
    ).toBe("Meridian-Financial.sarif");
  });

  it("extracts a bare (unquoted) filename", () => {
    expect(
      parseContentDispositionFilename(
        "attachment; filename=report.json",
        "fallback.txt",
      ),
    ).toBe("report.json");
  });

  it("prefers the RFC 5987 extended form when present", () => {
    expect(
      parseContentDispositionFilename(
        "attachment; filename=\"fallback.bin\"; filename*=UTF-8''r%C3%A9port.csv",
        "fallback.txt",
      ),
    ).toBe("réport.csv");
  });

  it("returns the fallback when the header is null", () => {
    expect(parseContentDispositionFilename(null, "fallback.txt")).toBe(
      "fallback.txt",
    );
  });

  it("returns the fallback when no filename is present", () => {
    expect(
      parseContentDispositionFilename("attachment", "fallback.txt"),
    ).toBe("fallback.txt");
  });
});

describe("triggerBlobDownload", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("creates an anchor with the download attribute and clicks it", () => {
    const createObjectURL = vi
      .fn()
      .mockReturnValue("blob:mock-url");
    const revokeObjectURL = vi.fn();
    // jsdom does not implement these by default.
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL,
      revokeObjectURL,
    });

    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});

    const blob = new Blob(["{}"], { type: "application/json" });
    triggerBlobDownload(blob, "out.json");

    expect(createObjectURL).toHaveBeenCalledWith(blob);
    expect(clickSpy).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
    // The anchor is removed from the DOM after the click.
    expect(document.querySelector("a[download]")).toBeNull();

    vi.unstubAllGlobals();
  });
});
