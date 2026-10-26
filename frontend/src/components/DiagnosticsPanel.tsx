type DiagnosticsPanelProps = Readonly<{
  recordCount: number
}>

export function DiagnosticsPanel({ recordCount }: DiagnosticsPanelProps) {
  return (
    <div className="rounded-xl bg-surface-container-lowest p-space-xl shadow-md">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-gutter-lg items-center">
        <div className="lg:col-span-2 flex flex-col gap-space-xs">
          <div className="flex items-center gap-space-xs font-mono text-label-sm text-primary uppercase tracking-wider">
            <span className="material-symbols-outlined text-[16px]">memory</span>
            Python Regex Matcher Diagnostics
          </div>
          <h3 className="font-geist text-headline-md text-on-surface">Deterministic Privacy Guarantee</h3>
          <p className="font-geist text-body-md text-on-surface-variant max-w-2xl">
            {recordCount} records evaluated on your FastAPI backend. Category rules run as auditable Python regex—no
            merchant data is sent to an LLM for classification.
          </p>
        </div>
        <div className="flex flex-col gap-space-sm">
          <div className="p-space-md rounded-lg bg-surface-container-low flex items-center justify-between">
            <span className="font-mono text-label-sm text-outline">LLM API Invocations</span>
            <span className="font-mono text-financial-md text-primary">0 Calls</span>
          </div>
          <div className="p-space-md rounded-lg bg-surface-container-low flex items-center justify-between">
            <span className="font-mono text-label-sm text-outline">Audit Trail Integrity</span>
            <span className="font-mono text-financial-md text-primary">100% Deterministic</span>
          </div>
        </div>
      </div>
    </div>
  )
}
