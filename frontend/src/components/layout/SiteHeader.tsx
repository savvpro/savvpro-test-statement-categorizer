"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Logo } from "./Logo";

const links = [
  { href: "/#how-it-works", label: "How it works" },
  { href: "/#prepare", label: "CSV guide" },
  { href: "/#features", label: "Features" },
];

export function SiteHeader() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-40 transition-all duration-300 ${
        scrolled ? "bg-white/80 shadow-[0_8px_30px_-12px_rgba(11,27,77,0.25)] backdrop-blur-xl" : "bg-white"
      }`}
    >
      <div className="h-1 bg-gradient-to-r from-brand-700 via-brand-500 to-accent-400" />
      <div className="container-page flex h-16 items-center justify-between">
        <Link href="/" aria-label="LedgerLane home" className="transition-transform duration-300 hover:scale-[1.03]">
          <Logo />
        </Link>

        <nav className="hidden items-center gap-1 rounded-xl bg-brand-50/70 p-1 ring-1 ring-brand-100 md:flex">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="group relative rounded-lg px-4 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-white hover:text-brand-700 hover:shadow-sm"
            >
              {l.label}
              <span className="absolute inset-x-4 bottom-1 h-0.5 origin-left scale-x-0 rounded-full bg-gradient-to-r from-brand-500 to-accent-400 transition-transform duration-300 group-hover:scale-x-100" />
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <Link
            href="/categorize"
            className="group hidden items-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white shadow-glow transition hover:bg-brand-700 sm:inline-flex"
          >
            Sort a statement
            <span className="grid h-5 w-5 place-items-center rounded-full bg-white/20 transition-transform duration-300 group-hover:translate-x-0.5">
              →
            </span>
          </Link>
          <button
            type="button"
            aria-label="Menu"
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
            className="grid h-10 w-10 place-items-center rounded-lg text-brand-900 ring-1 ring-brand-100 md:hidden"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              {open ? <path d="M6 6l12 12M18 6 6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
          </button>
        </div>
      </div>

      {open && (
        <nav className="container-page flex flex-col gap-1 pb-4 md:hidden">
          {[...links, { href: "/categorize", label: "Sort a statement" }].map((l) => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className="rounded-lg px-3 py-2.5 text-sm font-medium text-slate-700 hover:bg-brand-50 hover:text-brand-700"
            >
              {l.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
