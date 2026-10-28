import { ButtonLink } from "@/components/ui/Button";
import { Reveal } from "@/components/ui/Reveal";

export function CallToAction() {
  return (
    <section className="pb-24">
      <div className="container-page">
        <Reveal>
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-brand-700 via-brand-500 to-accent-500 bg-[length:200%_200%] px-8 py-16 text-center text-white animate-gradient-x">
            <div className="bg-grid pointer-events-none absolute inset-0 opacity-40" />
            <h2 className="relative text-3xl font-bold tracking-tight sm:text-4xl">Ready for tax time?</h2>
            <p className="relative mx-auto mt-4 max-w-xl text-lg text-white/85">
              Try it with a sample statement, or upload your own CSV export. It takes seconds.
            </p>
            <div className="relative mt-9 flex flex-wrap justify-center gap-3">
              <ButtonLink href="/categorize" variant="secondary" className="px-6 py-3">
                Sort a statement now <span aria-hidden>→</span>
              </ButtonLink>
              <ButtonLink href="#prepare" variant="ghost" className="px-6 py-3 text-white ring-1 ring-white/40 hover:bg-white/10">
                CSV guide
              </ButtonLink>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
