import { Reveal } from "@/components/ui/Reveal";
import { SectionTitle } from "./SectionTitle";

const steps = [
  { title: "Upload", text: "Drop a CSV from your bank or card.", icon: "M12 16V4m0 0-4 4m4-4 4 4M4 20h16" },
  { title: "Read & clean", text: "Find columns, fix signs, skip junk rows, clean merchant names.", icon: "M4 6h16M4 12h10M4 18h6" },
  { title: "Rule brain", text: "Six readable rule layers decide each row with a confidence score.", icon: "M9 3h6v4H9zM5 10h14v11H5zM9 14h6" },
  { title: "You review", text: "Unsure rows wait for you with a reason and a best guess.", icon: "M9 12l2 2 4-4M12 21a9 9 0 1 1 0-18 9 9 0 0 1 0 18z" },
  { title: "Totals & export", text: "Income, deductible and personal totals, ready for your accountant.", icon: "M4 19V5m5 14V9m5 10v-6m5 6V7" },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-20 py-24">
      <div className="container-page">
        <SectionTitle eyebrow="How it works" title="From messy CSV to tax-ready totals" />
        <ol className="relative mt-16 grid gap-10 md:grid-cols-5 md:gap-6">
          {/* the pipeline: a line with data packets flowing along it */}
          <div aria-hidden className="absolute left-[10%] right-[10%] top-8 hidden h-0.5 bg-gradient-to-r from-brand-200 via-brand-400 to-brand-200 md:block">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="absolute top-1/2 h-2 w-2 -translate-y-1/2 animate-flow rounded-full bg-accent-400 shadow-[0_0_12px_4px_rgba(34,211,238,0.6)]"
                style={{ animationDelay: `${i * -1.07}s` }}
              />
            ))}
          </div>
          {steps.map((s, i) => (
            <Reveal key={s.title} delay={i * 110}>
              <li className="group relative flex flex-col items-center text-center">
                <span className="relative z-10 grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-glow ring-4 ring-white transition duration-300 group-hover:-translate-y-1 group-hover:rotate-3">
                  <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d={s.icon} />
                  </svg>
                </span>
                <span className="mt-5 text-xs font-semibold uppercase tracking-[0.18em] text-brand-500">Step {i + 1}</span>
                <h3 className="mt-1 font-semibold text-brand-950">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{s.text}</p>
              </li>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}
