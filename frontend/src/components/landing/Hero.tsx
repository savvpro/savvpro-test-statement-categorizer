import { ButtonLink } from "@/components/ui/Button";

const preview = [
  { desc: "UBER *PAYOUT DRIVER WEEKLY", amount: "+$1,284.50", cat: "Platform Income", tone: "bg-emerald-400/15 text-emerald-300 ring-emerald-400/30" },
  { desc: "SHELL OIL 57444 DALLAS TX", amount: "−$48.20", cat: "Fuel", tone: "bg-brand-400/15 text-brand-200 ring-brand-400/30" },
  { desc: "DOORDASH*TACO SPOT", amount: "−$23.18", cat: "Meals (Personal)", tone: "bg-white/10 text-slate-200 ring-white/20" },
  { desc: "SHELL OIL 57444 DALLAS TX", amount: "−$6.49", cat: "Needs Review", tone: "bg-amber-400/15 text-amber-300 ring-amber-400/30" },
  { desc: "TRANSFER TO SAVINGS", amount: "−$500.00", cat: "Transfer", tone: "bg-violet-400/15 text-violet-200 ring-violet-400/30" },
];

const stats = [
  { value: "6", label: "rule layers" },
  { value: "3", label: "bank layouts" },
  { value: "0", label: "AI guesses" },
];

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-brand-950 text-white">
      <div className="bg-grid pointer-events-none absolute inset-0 [mask-image:radial-gradient(ellipse_at_top,black_40%,transparent_75%)]" />
      <div className="pointer-events-none absolute -left-32 top-10 h-96 w-96 animate-drift rounded-full bg-brand-600/40 blur-3xl" />
      <div className="pointer-events-none absolute -right-24 bottom-0 h-80 w-80 animate-drift rounded-full bg-accent-500/25 blur-3xl [animation-delay:-7s]" />

      <div className="container-page relative grid items-center gap-14 py-20 lg:grid-cols-[1.05fr_1fr] lg:py-28">
        <div className="animate-fade-up">
          <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-brand-100 ring-1 ring-white/15">
            <span className="h-1.5 w-1.5 animate-pulse2 rounded-full bg-accent-400" />
            For rideshare &amp; delivery drivers
          </span>
          <h1 className="mt-6 text-4xl font-bold leading-[1.08] tracking-tight sm:text-6xl">
            Your statements, <span className="text-gradient">sorted for tax time.</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-brand-100">
            Upload a bank or card CSV. Every transaction is sorted into tax categories, each decision is explained, and anything
            the app is not sure about waits for you. A wrong guess is worse than asking.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <ButtonLink href="/categorize" className="px-6 py-3 shadow-glow">
              Sort a statement
              <span aria-hidden>→</span>
            </ButtonLink>
            <ButtonLink href="#prepare" variant="ghost" className="px-6 py-3 text-white ring-1 ring-white/20 hover:bg-white/10">
              How to prepare your CSV
            </ButtonLink>
          </div>
          <dl className="mt-12 flex gap-10">
            {stats.map((s) => (
              <div key={s.label}>
                <dt className="text-3xl font-bold text-white">{s.value}</dt>
                <dd className="mt-1 text-sm text-brand-200">{s.label}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="relative animate-float">
          <div className="absolute -inset-4 rounded-3xl bg-gradient-to-br from-brand-500/40 to-accent-500/30 blur-2xl" />
          <div className="relative rounded-2xl bg-white/[0.06] p-5 ring-1 ring-white/15 backdrop-blur-xl">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-red-400/80" />
                <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
                <p className="ml-2 font-mono text-xs text-brand-200">checking_september.csv</p>
              </div>
              <span className="rounded-full bg-amber-400/15 px-2.5 py-0.5 text-xs font-medium text-amber-300 ring-1 ring-amber-400/30">
                1 to review
              </span>
            </div>
            <ul className="space-y-2">
              {preview.map((row, i) => (
                <li
                  key={row.desc + row.amount}
                  className="flex animate-fade-up items-center justify-between gap-3 rounded-xl bg-white/[0.04] px-4 py-3 ring-1 ring-white/10"
                  style={{ animationDelay: `${300 + i * 140}ms` }}
                >
                  <div className="min-w-0">
                    <p className="truncate font-mono text-[11px] text-brand-200">{row.desc}</p>
                    <p className="text-sm font-semibold">{row.amount}</p>
                  </div>
                  <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ${row.tone}`}>{row.cat}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
