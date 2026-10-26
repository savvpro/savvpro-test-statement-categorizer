import type { Tab } from "@/lib/format";

const TABS: { id: Tab; label: string }[] = [
  { id: "all", label: "All" },
  { id: "review", label: "Needs Review" },
  { id: "edited", label: "Edited" },
];

type Props = {
  tab: Tab;
  category: string;
  query: string;
  categories: string[];
  shown: number;
  total: number;
  onTab: (t: Tab) => void;
  onCategory: (c: string) => void;
  onQuery: (q: string) => void;
};

export function FilterBar({ tab, category, query, categories, shown, total, onTab, onCategory, onQuery }: Props) {
  // Arrow keys move between tabs (roving tabindex), as in the ARIA tabs pattern.
  function onKey(e: React.KeyboardEvent, i: number) {
    const step = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    e.preventDefault();
    const next = TABS[(i + step + TABS.length) % TABS.length];
    onTab(next.id);
    document.getElementById(`tab-${next.id}`)?.focus();
  }

  return (
    <div className="filters">
      <div className="tabs" role="tablist" aria-label="Row filter">
        {TABS.map((t, i) => (
          <button
            key={t.id}
            id={`tab-${t.id}`}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            tabIndex={tab === t.id ? 0 : -1}
            onClick={() => onTab(t.id)}
            onKeyDown={(e) => onKey(e, i)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="field">
        <label htmlFor="category-filter">Category</label>
        <select id="category-filter" value={category} onChange={(e) => onCategory(e.target.value)}>
          <option value="">All categories</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>
      <div className="field grow">
        <label htmlFor="search">Search</label>
        <input id="search" type="search" placeholder="Search descriptions" value={query} onChange={(e) => onQuery(e.target.value)} />
      </div>
      <p className="count" aria-live="polite">Showing {shown} of {total} rows</p>
    </div>
  );
}
