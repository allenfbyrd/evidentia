import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "evidentia-theme";

/** Read the initial theme from the <html> class (set by the no-FOUC inline
 *  script in index.html), falling back to localStorage / prefers-color-scheme. */
function getInitialTheme(): Theme {
  if (typeof document !== "undefined" && document.documentElement.classList.contains("dark")) {
    return "dark";
  }
  if (typeof window !== "undefined") {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored === "dark" || stored === "light") return stored;
    } catch {
      /* localStorage unavailable (private mode / SSR) — ignore. */
    }
    if (window.matchMedia?.("(prefers-color-scheme: dark)").matches) return "dark";
  }
  return "light";
}

/**
 * Light/dark theme controller. Toggling sets the `.dark` class on <html>
 * (which swaps every design token) and persists the choice to localStorage.
 */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      /* ignore persistence failures */
    }
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }, []);

  return { theme, toggle, setTheme };
}
