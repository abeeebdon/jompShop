import { Sun, Moon } from "@phosphor-icons/react";
import { useTheme } from "../lib/theme-context";

export default function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";
  return (
    <button
      onClick={toggle}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className="jomp-theme-toggle"
      data-testid="theme-toggle"
    >
      {isDark ? <Sun size={16} weight="fill" /> : <Moon size={16} weight="fill" />}
    </button>
  );
}
