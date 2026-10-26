"use client";

import { useTheme } from "next-themes";
import { Sun, Moon, Monitor } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/format";

const themes = ["light", "dark", "system"] as const;
type Theme = (typeof themes)[number];

const icons: Record<Theme, React.ReactNode> = {
  light: <Sun size={16} />,
  dark: <Moon size={16} />,
  system: <Monitor size={16} />,
};

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) return <div className="w-9 h-9" />;

  const current = (theme as Theme) ?? "system";
  const next = themes[(themes.indexOf(current) + 1) % themes.length];

  return (
    <button
      onClick={() => setTheme(next)}
      title={`Switch to ${next} theme`}
      className={cn(
        "w-9 h-9 flex items-center justify-center rounded-[var(--radius-md)] text-[var(--fg-muted)] hover:text-[var(--fg)] hover:bg-[var(--surface-2)] transition-colors",
        className
      )}
    >
      {icons[current]}
    </button>
  );
}
