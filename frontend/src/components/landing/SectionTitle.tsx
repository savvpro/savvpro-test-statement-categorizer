import { Reveal } from "@/components/ui/Reveal";

export function SectionTitle({ eyebrow, title, text, dark = false }: { eyebrow: string; title: string; text?: string; dark?: boolean }) {
  return (
    <Reveal className="mx-auto max-w-2xl text-center">
      <p className={`text-sm font-semibold uppercase tracking-[0.18em] ${dark ? "text-accent-300" : "text-brand-600"}`}>{eyebrow}</p>
      <h2 className={`mt-3 text-3xl font-bold tracking-tight sm:text-4xl ${dark ? "text-white" : "text-brand-950"}`}>{title}</h2>
      {text && <p className={`mt-4 text-lg ${dark ? "text-brand-100" : "text-slate-600"}`}>{text}</p>}
    </Reveal>
  );
}
