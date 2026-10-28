import { Reveal } from "@/components/ui/Reveal";

const layers = [
  { name: "Your earlier fixes", text: "If you filed a merchant before, your choice wins." },
  { name: "Money movement", text: "Card payments and transfers are not spending." },
  { name: "Money in", text: "Payouts and tips are income, refunds are money back, unknown deposits wait for you." },
  { name: "Fees", text: "Bank fees and card interest." },
  { name: "Known merchants", text: "Fuel, tolls, repairs, phone, insurance… with sanity checks like a $6 gas-station charge being snacks." },
  { name: "Not sure? Ask.", text: "Anything under 75% confidence goes to Needs Review with its best guess." },
];

export function BrainLayers() {
  return (
    <section className="relative overflow-hidden bg-brand-950 py-24 text-white">
      <div className="bg-grid pointer-events-none absolute inset-0 opacity-60 [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_75%)]" />
      <div className="pointer-events-none absolute right-0 top-0 h-96 w-96 animate-drift rounded-full bg-brand-600/30 blur-3xl" />
      <div className="container-page relative grid items-center gap-14 lg:grid-cols-2">
        <Reveal>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-accent-300">Inside the brain</p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
            Six layers. <span className="text-gradient">The first one that is sure decides.</span>
          </h2>
          <p className="mt-5 text-lg leading-relaxed text-brand-100">
            Every row passes through the same readable rules, in order. Each decision comes with a confidence score and a plain
            reason, so you always see why a row landed where it did. No AI model is involved.
          </p>
        </Reveal>
        <ol className="relative space-y-3 before:absolute before:bottom-4 before:left-[27px] before:top-4 before:w-px before:bg-gradient-to-b before:from-brand-400 before:to-accent-400">
          {layers.map((l, i) => (
            <Reveal key={l.name} delay={i * 90}>
              <li className="relative flex gap-4 rounded-xl bg-white/[0.04] p-4 ring-1 ring-white/10 transition hover:bg-white/[0.08] hover:ring-brand-400/40">
                <span className="relative z-10 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-brand-500 to-accent-500 text-sm font-bold">
                  {i + 1}
                </span>
                <div>
                  <p className="font-semibold">{l.name}</p>
                  <p className="mt-0.5 text-sm text-brand-100">{l.text}</p>
                </div>
              </li>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}
