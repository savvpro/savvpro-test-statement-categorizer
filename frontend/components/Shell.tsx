"use client";

import { useEffect, useState } from "react";
import {
  BookOpenCheck,
  ChevronRight,
  FileSpreadsheet,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  ReceiptText,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cx } from "./ui";

export type View = "dashboard" | "statements" | "review" | "rules";

export const VIEW_LABEL: Record<View, string> = {
  dashboard: "Dashboard",
  statements: "Statements",
  review: "Needs Review",
  rules: "Learned Rules",
};

const NAV: Array<{ view: View; icon: LucideIcon }> = [
  { view: "dashboard", icon: LayoutDashboard },
  { view: "statements", icon: FileSpreadsheet },
  { view: "review", icon: ListChecks },
  { view: "rules", icon: BookOpenCheck },
];

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <span
        className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-white"
        aria-hidden="true"
      >
        <ReceiptText size={18} strokeWidth={1.75} />
      </span>
      <div className="leading-tight">
        <p className="text-[15px] font-semibold text-ink">LedgerLite</p>
        <p className="text-xs text-faint">Tax Categorizer</p>
      </div>
    </div>
  );
}

function NavList({
  view,
  reviewCount,
  onNavigate,
}: {
  view: View;
  reviewCount: number | null;
  onNavigate: (v: View) => void;
}) {
  return (
    <ul className="space-y-1">
      {NAV.map(({ view: v, icon: Icon }) => {
        const active = v === view;
        return (
          <li key={v}>
            <button
              type="button"
              onClick={() => onNavigate(v)}
              aria-current={active ? "page" : undefined}
              className={cx(
                "flex h-10 w-full items-center gap-3 rounded-lg px-3 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-accent",
                active ? "bg-accent-soft font-medium text-accent" : "text-muted hover:bg-page hover:text-ink",
              )}
            >
              <Icon size={18} strokeWidth={1.75} aria-hidden="true" />
              <span className="flex-1 text-left">{VIEW_LABEL[v]}</span>
              {v === "review" && reviewCount !== null && reviewCount > 0 ? (
                <span
                  className="rounded-full bg-amber-soft px-2 py-0.5 text-xs font-medium tabular-nums text-amber"
                  aria-label={`${reviewCount} to review`}
                >
                  {reviewCount}
                </span>
              ) : null}
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function SignOut() {
  return (
    <button
      type="button"
      className="flex h-10 w-full items-center gap-3 rounded-lg px-3 text-sm text-muted transition-colors hover:bg-page hover:text-ink focus-visible:outline-2 focus-visible:outline-accent"
    >
      <LogOut size={18} strokeWidth={1.75} aria-hidden="true" />
      Sign out
    </button>
  );
}

export function Shell({
  view,
  reviewCount,
  onNavigate,
  children,
}: {
  view: View;
  reviewCount: number | null;
  onNavigate: (v: View) => void;
  children: React.ReactNode;
}) {
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMenuOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  const go = (v: View) => {
    setMenuOpen(false);
    onNavigate(v);
  };

  return (
    <div className="min-h-screen lg:flex">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-line bg-card px-4 py-5 lg:flex">
        <div className="px-2">
          <Brand />
        </div>
        <nav aria-label="Main" className="mt-8 flex-1">
          <NavList view={view} reviewCount={reviewCount} onNavigate={go} />
        </nav>
        <div className="border-t border-line pt-3">
          <SignOut />
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 border-b border-line bg-card">
          <div className="flex h-16 items-center gap-3 px-4 sm:px-6 lg:px-8">
            <button
              type="button"
              className="-ml-1 inline-flex h-10 w-10 items-center justify-center rounded-lg text-muted hover:bg-page lg:hidden"
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen}
              aria-controls="mobile-nav"
              onClick={() => setMenuOpen((o) => !o)}
            >
              {menuOpen ? <X size={20} strokeWidth={1.75} /> : <Menu size={20} strokeWidth={1.75} />}
            </button>
            <div className="lg:hidden">
              <Brand />
            </div>

            <nav aria-label="Breadcrumb" className="hidden min-w-0 lg:block">
              <ol className="flex items-center gap-1.5 text-sm">
                <li>
                  <button type="button" onClick={() => go("dashboard")} className="text-faint hover:text-ink">
                    Home
                  </button>
                </li>
                <li aria-hidden="true" className="text-faint">
                  <ChevronRight size={14} />
                </li>
                <li aria-current="page" className="truncate font-medium text-ink">
                  {VIEW_LABEL[view]}
                </li>
              </ol>
            </nav>

            <div className="ml-auto flex items-center gap-3">
              <div className="hidden text-right leading-tight sm:block">
                <p className="text-sm font-medium text-ink">Sara Khan</p>
                <p className="text-xs text-faint">Freelancer</p>
              </div>
              <span
                className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent"
                aria-label="Sara Khan"
              >
                SK
              </span>
            </div>
          </div>

          {menuOpen ? (
            <div id="mobile-nav" className="border-t border-line bg-card px-4 pb-4 pt-3 lg:hidden">
              <nav aria-label="Main">
                <NavList view={view} reviewCount={reviewCount} onNavigate={go} />
              </nav>
              <div className="mt-3 border-t border-line pt-3">
                <SignOut />
              </div>
            </div>
          ) : null}
        </header>

        <main className="mx-auto w-full max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
