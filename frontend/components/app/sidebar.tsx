"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Upload, FileText, List, AlertCircle,
  Wand2, Tag, BarChart3, Settings, HelpCircle, BookOpen,
  ChevronLeft, ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/format";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import type { DashboardData } from "@/lib/types";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/statements", label: "Statements", icon: FileText },
  { href: "/transactions", label: "Transactions", icon: List },
  { href: "/review", label: "Review Queue", icon: AlertCircle, badge: true },
  { href: "/rules", label: "Rules", icon: Wand2 },
  { href: "/categories", label: "Categories", icon: Tag },
  { href: "/reports", label: "Reports", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/how-it-works", label: "How It Works", icon: HelpCircle },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const { data } = useQuery({
    queryKey: qk.dashboard(),
    queryFn: () => api.get("/dashboard") as Promise<DashboardData>,
    staleTime: 60_000,
  });
  const reviewCount = data?.needs_review_count ?? 0;

  return (
    <aside
      style={{
        width: collapsed ? 64 : 240,
        background: "var(--surface)",
        borderRight: "1px solid var(--border)",
        transition: "width 0.2s ease",
      }}
      className="flex flex-col h-full shrink-0"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-[var(--border)]">
        <div className="shrink-0">
          <BookOpen size={22} style={{ color: "var(--accent)" }} />
        </div>
        {!collapsed && (
          <span
            className="text-lg font-semibold truncate"
            style={{ fontFamily: "var(--font-fraunces), Georgia, serif", color: "var(--fg)" }}
          >
            Ledgerline
          </span>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 overflow-y-auto">
        {navItems.map(({ href, label, icon: Icon, badge }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              title={collapsed ? label : undefined}
              className={cn(
                "flex items-center gap-3 px-4 py-2.5 mx-2 rounded-[var(--radius-md)] text-sm transition-colors relative",
                active
                  ? "bg-[var(--accent-light)] text-[var(--accent)] font-medium"
                  : "text-[var(--fg-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
              )}
            >
              <span className="shrink-0 relative">
                <Icon size={18} />
                {badge && reviewCount > 0 && collapsed && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-[var(--highlight)] text-[#92601A] text-[9px] font-bold flex items-center justify-center">
                    {reviewCount > 9 ? "9+" : reviewCount}
                  </span>
                )}
              </span>
              {!collapsed && (
                <>
                  <span className="truncate">{label}</span>
                  {badge && reviewCount > 0 && (
                    <span className="ml-auto rounded-full bg-[var(--highlight)] text-[#92601A] text-xs font-bold px-1.5 py-0.5 min-w-[20px] text-center">
                      {reviewCount}
                    </span>
                  )}
                </>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={onToggle}
        className="flex items-center justify-center h-12 border-t border-[var(--border)] text-[var(--fg-muted)] hover:text-[var(--fg)] hover:bg-[var(--surface-2)] transition-colors"
        title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>
    </aside>
  );
}
