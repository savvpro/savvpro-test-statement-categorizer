export function Logo({ light = false }: { light?: boolean }) {
  return (
    <span className={`flex items-center gap-2 text-lg font-bold tracking-tight ${light ? "text-white" : "text-brand-950"}`}>
      <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-glow">
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M4 7h16M4 12h10M4 17h7" />
          <path d="m15 16 2 2 4-4" />
        </svg>
      </span>
      <span>
        Ledger<span className={light ? "text-accent-300" : "text-brand-600"}>Lane</span>
      </span>
    </span>
  );
}
