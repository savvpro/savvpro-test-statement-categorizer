import { useEffect, useState } from "react";
import { CategoryTotals } from "./components/CategoryTotals.jsx";
import { ReviewProgress } from "./components/ReviewProgress.jsx";
import { SavedRules } from "./components/SavedRules.jsx";
import { TaxEstimatePanel } from "./components/TaxEstimatePanel.jsx";
import { TransactionFilters } from "./components/TransactionFilters.jsx";
import { TransactionTable } from "./components/TransactionTable.jsx";
import { UploadPanel } from "./components/UploadPanel.jsx";
import { useStatement, useTaxEstimate } from "./hooks/useStatement.js";
import { api } from "./lib/api.js";
import { exportCsv } from "./lib/exportCsv.js";

const NO_FILTERS = { query: "", reviewOnly: false, category: "" };

export default function App() {
  const statement = useStatement();
  const estimate = useTaxEstimate(statement.rows);
  const [categories, setCategories] = useState([]);
  const [filters, setFilters] = useState(NO_FILTERS);
  const { rows, issues, status, pending } = statement;

  useEffect(() => { api.categories().then(setCategories).catch(() => {}); }, []);
  useEffect(() => setFilters(NO_FILTERS), [statement.fileName]);

  return (
    <main>
      <header>
        <h1>Statement Categorizer</h1>
        <p>Sort a freelancer's business statement into HMRC Self Assessment categories, fix anything uncertain, and see what to set aside for tax.</p>
      </header>

      <UploadPanel onUpload={statement.upload} loading={status.loading} fileName={statement.fileName} />
      {status.error && <div className="alert error" role="alert">{status.error}</div>}
      {status.notice && <div className="alert ok" role="status">{status.notice}</div>}

      {rows.length > 0 && (
        <>
          <ReviewProgress total={rows.length} pending={pending} />

          {issues.length > 0 && (
            <details className="alert error">
              <summary>{issues.length} row(s) could not be read and were skipped</summary>
              <ul>{issues.map((i) => <li key={i.row}>Row {i.row}: {i.message}</li>)}</ul>
            </details>
          )}

          <div className="layout">
            <CategoryTotals totals={statement.totals} activeCategory={filters.category}
              onSelect={(category) => setFilters({ ...filters, category })} />
            <TaxEstimatePanel estimate={estimate} />
          </div>

          <TransactionFilters filters={filters} onChange={setFilters} canExport={pending === 0}
            onExport={() => exportCsv(rows, statement.fileName.replace(/\.csv$/i, "") + "-categorized.csv")} />
          <TransactionTable rows={rows} categories={categories} filters={filters}
            onSetCategory={statement.setCategory} onApplyToMerchant={statement.applyToMerchant}
            onRemember={statement.rememberMerchant} />
        </>
      )}

      <SavedRules refreshKey={status.notice} />
    </main>
  );
}
