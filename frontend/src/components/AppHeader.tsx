type AppHeaderProps = Readonly<{
  onExport: () => void
  hasData: boolean
}>

export function AppHeader({ onExport, hasData }: AppHeaderProps) {
  return (
    <header className="fixed top-0 w-full z-50 bg-surface/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.25)]">
      <div className="h-28 w-full px-margin-lg flex flex-col justify-between py-space-xs max-w-[1600px] mx-auto">
        <div className="flex items-center justify-between gap-space-lg pt-space-xs">
          <div className="flex items-center gap-space-md flex-wrap">
            <span className="font-geist text-headline-md text-on-surface flex items-center gap-space-xs">
              LedgerPrep
              <span className="font-mono text-label-sm px-space-xs py-0.5 rounded bg-surface-container-high text-primary uppercase">
                v2.4
              </span>
            </span>
            <span className="text-outline-variant font-mono text-label-md hidden sm:inline">/</span>
            <div className="hidden sm:flex items-center gap-space-xs font-mono text-label-md text-on-surface-variant">
              <span className="text-on-surface">Tax Year 2024</span>
              <span className="text-outline-variant">/</span>
              <span>Freelance Design Schedule C</span>
            </div>
            <div className="hidden xl:flex items-center gap-space-xs px-space-sm py-1 rounded bg-surface-container-low">
              <span className="h-2 w-2 rounded-full bg-primary-container animate-pulse" />
              <span className="font-mono text-label-sm text-on-surface-variant">
                Rule Brain Engine: <span className="text-primary">Active</span> (0 LLM · deterministic)
              </span>
            </div>
          </div>
          <div className="flex items-center gap-space-md">
            <button
              type="button"
              disabled={!hasData}
              onClick={onExport}
              className="inline-flex items-center gap-space-xs font-mono text-label-md bg-surface-container-high hover:bg-surface-bright disabled:opacity-40 text-on-surface px-space-md py-1.5 rounded transition-all"
            >
              <span className="material-symbols-outlined text-[16px] text-tertiary">download</span>
              <span className="hidden md:inline">Export Tax Summary</span>
            </button>
            <div className="flex items-center gap-space-xs pl-space-sm py-1 pr-space-md rounded-full bg-surface-container-low">
              <div className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center font-mono text-label-sm">
                AR
              </div>
              <span className="font-mono text-label-md text-on-surface hidden sm:inline">
                Alex Rivera · Design Studio LLC
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center justify-between border-t border-surface-container">
          <nav className="flex items-center gap-space-xs py-1 overflow-x-auto">
            <span className="px-space-md py-1.5 rounded bg-surface-container-high text-on-surface font-semibold text-body-md whitespace-nowrap">
              Overview & Categorization
            </span>
            <span className="text-body-md text-on-surface-variant px-space-md py-1.5 whitespace-nowrap">
              Rule Dictionary
            </span>
          </nav>
          <div className="hidden md:flex items-center gap-space-md font-mono text-label-sm text-outline">
            <span className="flex items-center gap-1">
              <span className="material-symbols-outlined text-[14px] text-primary">verified_user</span>
              Schedule C ready
            </span>
          </div>
        </div>
      </div>
    </header>
  )
}
