/**
 * Browser-download helpers for binary/text artifacts returned by the API.
 *
 * Kept framework-free and side-effect-light so the pure pieces
 * (filename parsing, anchor construction) are unit-testable under jsdom
 * without performing a real navigation.
 */

/**
 * Parse the download filename out of a `Content-Disposition` header.
 *
 * Handles the common `attachment; filename="foo.json"` form (what the
 * Evidentia API emits) as well as bare `filename=foo.json` and RFC 5987
 * `filename*=UTF-8''foo.json`. Returns `fallback` when no filename can
 * be recovered.
 */
export function parseContentDispositionFilename(
  header: string | null,
  fallback: string,
): string {
  if (!header) return fallback;

  // RFC 5987 extended form takes precedence when present.
  const star = /filename\*\s*=\s*(?:UTF-8'[^']*')?["']?([^"';]+)["']?/i.exec(
    header,
  );
  if (star?.[1]) {
    try {
      return decodeURIComponent(star[1]);
    } catch {
      return star[1];
    }
  }

  const plain = /filename\s*=\s*"([^"]+)"|filename\s*=\s*([^";]+)/i.exec(header);
  const value = plain?.[1] ?? plain?.[2];
  if (value) return value.trim();

  return fallback;
}

/**
 * Trigger a browser "save file" for an in-memory blob.
 *
 * Builds an object URL, clicks a transient anchor, then revokes the URL.
 * No-ops gracefully when `document` is unavailable (SSR / test guards).
 */
export function triggerBlobDownload(blob: Blob, filename: string): void {
  if (typeof document === "undefined") return;
  const url = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.rel = "noopener";
    anchor.style.display = "none";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}
