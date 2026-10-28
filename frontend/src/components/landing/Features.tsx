import { Reveal } from "@/components/ui/Reveal";
import { SectionTitle } from "./SectionTitle";

const features = [
  { title: "Any bank layout", text: "One amount column or Debit/Credit columns, title lines on top, $1,234.56, (12.34), 12.34 CR.", icon: "M4 6h16M4 12h16M4 18h16M9 6v12" },
  { title: "Explains itself", text: "Every row shows the rule that decided it and how confident it is.", icon: "M12 18h.01M9.1 9a3 3 0 1 1 4.2 2.7c-.8.4-1.3 1.2-1.3 2.1V14" },
  { title: "Asks when unsure", text: "Mixed stores, peer-to-peer payments and unknown deposits go to review, never guessed.", icon: "M12 9v4m0 4h.01M10.3 3.9 2.4 17.5A2 2 0 0 0 4.1 20.5h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" },
  { title: "Learns your fixes", text: "Fix a merchant once and similar rows, and future statements, follow.", icon: "M4 12a8 8 0 0 1 14-5.3L20 9M20 4v5h-5M20 12a8 8 0 0 1-14 5.3L4 15m0 5v-5h5" },
  { title: "Refunds done right", text: "Money back reduces the category you spent it in. Never counted as income.", icon: "M9 14 4 9l5-5M4 9h11a5 5 0 0 1 0 10h-3" },
  { title: "Export for your accountant", text: "Download a categorized CSV with the deductible flag on every row.", icon: "M12 4v12m0 0-4-4m4 4 4-4M4 20h16" },
];

const messy = [
  ["DOORDASH DASHER DIRECT DEP", "Income", "you drove", "text-emerald-700 bg-emerald-50 ring-emerald-200"],
  ["DOORDASH*TACO SPOT", "Personal meal", "you ordered", "text-slate-700 bg-slate-50 ring-slate-200"],
  ["SHELL OIL  −$6.49", "Review", "probably snacks, not fuel", "text-amber-800 bg-amber-50 ring-amber-200"],
  ["T-MOBILE AUTOPAY  ×2 same day", "Review", "possible duplicate", "text-amber-800 bg-amber-50 ring-amber-200"],
  ["AUTOZONE REFUND  +$24.99", "Refund", "reduces Vehicle Maintenance", "text-brand-700 bg-brand-50 ring-brand-200"],
  ["MOBILE DEPOSIT  +$300.00", "Review", "not income until you say so", "text-amber-800 bg-amber-50 ring-amber-200"],
];

export function Features() {
  return (
    <section id="features" className="scroll-mt-20 py-24">
      <div className="container-page">
        <SectionTitle eyebrow="Features" title="Built for real, messy statements" />
        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => (
            <Reveal key={f.title} delay={(i % 3) * 110}>
              <div className="group h-full rounded-2xl bg-white p-6 shadow-card ring-1 ring-brand-100 transition duration-300 hover:-translate-y-1 hover:shadow-glow">
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-brand-600 ring-1 ring-brand-100 transition group-hover:bg-brand-600 group-hover:text-white">
                  <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
                    <path d={f.icon} />
                  </svg>
                </span>
                <h3 className="mt-5 font-semibold text-brand-950">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{f.text}</p>
              </div>
            </Reveal>
          ))}
        </div>

        <Reveal className="mt-16 overflow-hidden rounded-2xl shadow-card ring-1 ring-brand-100">
          <div className="flex items-center justify-between bg-gradient-to-r from-brand-50 to-white px-6 py-4">
            <h3 className="font-semibold text-brand-950">Tricky rows it handles</h3>
            <span className="text-xs text-slate-500">from the sample statements</span>
          </div>
          <ul className="divide-y divide-brand-100 bg-white">
            {messy.map(([row, label, why, tone]) => (
              <li key={row} className="grid items-center gap-2 px-6 py-3.5 transition hover:bg-brand-50/50 sm:grid-cols-[1fr_auto_1fr]">
                <span className="font-mono text-sm text-slate-600">{row}</span>
                <span className={`justify-self-start rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 sm:justify-self-center ${tone}`}>{label}</span>
                <span className="text-sm text-slate-600 sm:text-right">{why}</span>
              </li>
            ))}
          </ul>
        </Reveal>
      </div>
    </section>
  );
}
