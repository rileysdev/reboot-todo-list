import { useCallback, useEffect, useState } from "react";

type Theme = "light" | "dark";
const STORAGE_KEY = "todo.theme";

function prefersDark(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  );
}

// Explicit theme choice stamped on <html data-theme>. When unset, the
// CSS falls back to the OS preference.
export function useTheme(): { theme: Theme; toggle: () => void } {
  const [explicit, setExplicit] = useState<Theme | null>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "light" || stored === "dark" ? stored : null;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (explicit) {
      root.setAttribute("data-theme", explicit);
      localStorage.setItem(STORAGE_KEY, explicit);
    } else {
      root.removeAttribute("data-theme");
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [explicit]);

  const toggle = useCallback(() => {
    setExplicit((current) => {
      const effective = current ?? (prefersDark() ? "dark" : "light");
      return effective === "dark" ? "light" : "dark";
    });
  }, []);

  const theme: Theme = explicit ?? (prefersDark() ? "dark" : "light");
  return { theme, toggle };
}
