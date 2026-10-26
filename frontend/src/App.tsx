import { AppFooter } from './components/AppFooter'
import { AppHeader } from './components/AppHeader'
import { CategoryBreakdown } from './components/CategoryBreakdown'
import { DiagnosticsPanel } from './components/DiagnosticsPanel'
import { KpiCards } from './components/KpiCards'
import { TransactionTable } from './components/TransactionTable'
import { UploadSection } from './components/UploadSection'
import { useStatementCategorizer } from './hooks/useStatementCategorizer'

function App() {
  const {
    categories,
    result,
    loading,
    rescanning,
    error,
    filter,
    categoryFilter,
    search,
    setSearch,
    updatingId,
    fileName,
    fileSize,
    stats,
    visibleRows,
    onFile,
    loadSample,
    clearStatement,
    rescan,
    onCategoryChange,
    exportSummaryCsv,
    setFilter,
    filterByCategory,
  } = useStatementCategorizer()

  const quickApprove = (id: string) => {
    void onCategoryChange(id, 'Meals & Entertainment')
  }

  return (
    <>
      <AppHeader onExport={exportSummaryCsv} hasData={!!result} />

      <main className="w-full pt-28 bg-background min-h-screen">
        <section className="w-full px-margin-lg py-space-xl max-w-[1440px] mx-auto flex flex-col gap-space-lg">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md p-space-lg rounded-xl bg-surface-container-low shadow-sm">
            <div className="flex items-start sm:items-center gap-space-md">
              <div className="p-2.5 rounded-lg bg-surface-container-high text-primary flex items-center justify-center">
                <span className="material-symbols-outlined text-[20px]">format_image_left</span>
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-space-xs font-mono text-label-sm text-outline uppercase tracking-wider">
                  <span>Tax Prep Engine</span>
                  <span className="text-outline-variant">·</span>
                  <span className="text-on-surface-variant">Freelance Designer</span>
                  <span className="text-outline-variant">·</span>
                  <span className="text-primary font-medium">Schedule C Ready</span>
                </div>
                <p className="font-geist text-body-md text-on-surface mt-0.5">
                  Deterministic engine:{' '}
                  <span className="font-mono text-financial-md text-primary">0 LLM calls</span>, Python regex mapped to
                  Schedule C categories.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-space-md font-mono text-label-sm">
              <div className="flex items-center gap-space-xs px-space-md py-1.5 rounded-full bg-surface-container text-on-surface-variant">
                <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                Local API
              </div>
              <div className="flex items-center gap-space-xs px-space-md py-1.5 rounded-full bg-surface-container text-tertiary">
                <span className="material-symbols-outlined text-[14px]">lock</span>
                Fake data only
              </div>
            </div>
          </div>

          <div className="flex flex-col md:flex-row md:items-end justify-between gap-space-lg">
            <div>
              <h1 className="font-geist text-headline-xl text-on-surface tracking-tight">Statement Categorizer</h1>
              <p className="font-geist text-body-lg text-on-surface-variant max-w-3xl mt-1">
                Ingest Chase, Amex, or Mercury CSV statements. Regex rules assign deductions; ambiguous rows go to{' '}
                <span className="text-secondary font-medium">Needs Review</span>.
              </p>
            </div>
            <div className="flex items-center gap-space-sm">
              <button
                type="button"
                disabled={!fileName || rescanning}
                onClick={() => void rescan()}
                className="inline-flex items-center gap-space-xs px-space-md py-2 rounded-lg bg-surface-container-high hover:bg-surface-bright text-on-surface font-mono text-label-md transition-all shadow-sm disabled:opacity-40"
              >
                <span className={`material-symbols-outlined text-[16px] text-tertiary ${rescanning ? 'animate-spin' : ''}`}>
                  {rescanning ? 'rotate_right' : 'refresh'}
                </span>
                Re-scan Strict Rules
              </button>
            </div>
          </div>

          <UploadSection
            loading={loading}
            fileName={fileName}
            fileSize={fileSize}
            itemCount={result?.transactions.length ?? 0}
            error={error}
            onFile={onFile}
            onSample={() => void loadSample()}
            onClear={clearStatement}
          />

          {result && stats && (
            <>
              <KpiCards
                total={stats.total}
                deductible={stats.deductible}
                transfers={stats.transfers}
                refunds={stats.refunds}
                reviewCount={result.needs_review_count}
                reviewTotal={stats.reviewTotal}
                deductibleSpend={stats.deductibleSpend}
                taxSavings={stats.taxSavings}
                onReviewClick={() => setFilter('review')}
              />

              <CategoryBreakdown
                summaries={result.summaries}
                activeCategory={categoryFilter}
                onSelect={filterByCategory}
              />

              <TransactionTable
                rows={visibleRows}
                totalCount={result.transactions.length}
                categories={categories}
                filter={filter}
                search={search}
                confirmedCount={stats.confirmed}
                reviewCount={result.needs_review_count}
                updatingId={updatingId}
                onSearch={setSearch}
                onFilter={setFilter}
                onCategoryChange={onCategoryChange}
                onQuickApprove={quickApprove}
              />

              <DiagnosticsPanel recordCount={result.transactions.length} />
            </>
          )}

          {!result && !loading && (
            <p className="font-geist text-body-md text-on-surface-variant text-center py-space-2xl">
              Upload a CSV or load the sample to see categorization results.
            </p>
          )}
        </section>
      </main>

      <AppFooter />
    </>
  )
}

export default App
