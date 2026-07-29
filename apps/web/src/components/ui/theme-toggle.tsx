"use client";

import { useTheme } from "next-themes";
import { Sun, Moon } from "lucide-react";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      className="p-1.5 rounded hover:bg-vault-surface-hover transition-colors"
      aria-label="Toggle theme"
    >
      <Sun className="h-4 w-4 text-vault-text-muted hidden dark:block" />
      <Moon className="h-4 w-4 text-vault-text-muted block dark:hidden" />
    </button>
  );
}
