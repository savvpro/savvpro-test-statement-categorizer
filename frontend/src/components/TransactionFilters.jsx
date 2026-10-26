export function TransactionFilters({ filters, onChange, onExport, canExport }) {
  const set = (patch) => onChange({ ...filters, ...patch });
  return (
    <div className="toolbar">
      <input type="search" placeholder="Search description or merchant" value={filters.query}
        onChange={(e) => set({ query: e.target.value })} aria-label="Search transactions" />
      <label><input type="checkbox" checked={filters.reviewOnly} onChange={(e) => set({ reviewOnly: e.target.checked })} /> Needs review only</label>
      {filters.category && <button className="chip" onClick={() => set({ category: "" })}>{filters.category} ✕</button>}
      <span className="spacer" />
      <button onClick={onExport} disabled={!canExport} title={canExport ? "" : "Resolve all reviews first"}>Export CSV</button>
    </div>
  );
}
