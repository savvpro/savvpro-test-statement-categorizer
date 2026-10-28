import Link from "next/link";
import { Logo } from "./Logo";

const highlights = [
  { label: "Upload", value: "Any bank or card CSV", icon: "M12 16V4m0 0-4 4m4-4 4 4M4 20h16" },
  { label: "Decisions", value: "Rule-based, no AI model", icon: "M9 12l2 2 4-4M12 21a9 9 0 1 1 0-18 9 9 0 0 1 0 18z" },
  { label: "Data", value: "Fake samples, nothing shared", icon: "M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6z" },
];

const columns = [
  {
    title: "Product",
    links: [
      { href: "/categorize", label: "Sort a statement" },
      { href: "/#how-it-works", label: "How it works" },
      { href: "/#prepare", label: "CSV guide" },
      { href: "/#features", label: "Features" },
    ],
  },
  {
    title: "Samples",
    links: [
      { href: "/samples/checking_bank_style.csv", label: "Checking account", download: true },
      { href: "/samples/credit_card_style.csv", label: "Credit card", download: true },
      { href: "/samples/debit_credit_columns.csv", label: "Debit / Credit", download: true },
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="relative overflow-hidden bg-brand-950 text-white">
      <div className="bg-grid pointer-events-none absolute inset-0 opacity-40 [mask-image:linear-gradient(to_bottom,black,transparent)]" />
      <div className="pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full bg-brand-600/30 blur-3xl" />

      <div className="container-page relative">
        {/* call to action */}
        <div className="flex flex-col gap-8 border-b border-white/10 py-14 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent-300">Tax time, sorted</p>
            <h2 className="mt-3 text-4xl font-light leading-tight tracking-tight sm:text-5xl">
              Let&apos;s sort your <span className="text-gradient font-semibold">statement.</span>
            </h2>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/categorize"
              className="group inline-flex items-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-semibold text-brand-900 transition hover:bg-brand-50"
            >
              Upload a CSV <span className="transition-transform duration-300 group-hover:translate-x-1">→</span>
            </Link>
            <Link
              href="/#prepare"
              className="inline-flex items-center rounded-lg px-5 py-3 text-sm font-semibold text-white ring-1 ring-white/30 transition hover:bg-white/10 hover:ring-white/60"
            >
              Read the CSV guide
            </Link>
          </div>
        </div>

        {/* highlight cards */}
        <div className="grid gap-4 py-10 sm:grid-cols-3">
          {highlights.map((h) => (
            <div
              key={h.label}
              className="group flex items-center gap-4 rounded-xl bg-white/[0.04] p-5 ring-1 ring-white/10 transition duration-300 hover:-translate-y-1 hover:bg-white/[0.08] hover:ring-brand-400/40"
            >
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 shadow-glow transition-transform duration-300 group-hover:scale-110">
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
                  <path d={h.icon} />
                </svg>
              </span>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-brand-200">{h.label}</p>
                <p className="mt-0.5 font-semibold">{h.value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* brand + links */}
        <div className="grid gap-10 py-8 md:grid-cols-[1.4fr_1fr_1fr]">
          <div>
            <Logo light />
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-brand-200">
              Tax-ready bank and card statements for rideshare and delivery drivers. Every decision is explained, and anything
              unsure waits for you.
            </p>
          </div>
          {columns.map((col) => (
            <div key={col.title}>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-300">{col.title}</p>
              <ul className="mt-4 space-y-2.5">
                {col.links.map((l) => (
                  <li key={l.href}>
                    <a
                      href={l.href}
                      download={"download" in l ? true : undefined}
                      className="group inline-flex items-center gap-1.5 text-sm text-brand-100 transition-colors hover:text-white"
                    >
                      <span className="h-px w-0 bg-accent-400 transition-all duration-300 group-hover:w-3" />
                      {l.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* oversized outline wordmark */}
        <p
          aria-hidden
          className="pointer-events-none select-none text-center text-[19vw] font-bold leading-[0.8] tracking-tighter text-transparent [-webkit-text-stroke:1px_rgba(141,179,255,0.22)] lg:text-[200px]"
        >
          LedgerLane
        </p>
      </div>

      <div className="relative border-t border-white/10 bg-black/20">
        <div className="container-page flex flex-col gap-3 py-5 text-xs text-brand-200 sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} LedgerLane · Statement Categorizer assessment by Hammad Shabbir · Demo data only</p>
          <a
            href="#"
            aria-label="Back to top"
            className="grid h-9 w-9 place-items-center self-start rounded-full ring-1 ring-white/25 transition hover:-translate-y-0.5 hover:bg-white hover:text-brand-900 sm:self-auto"
          >
            ↑
          </a>
        </div>
      </div>
    </footer>
  );
}
