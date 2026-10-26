import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import { CATEGORY_COLORS } from './categories'
import RuleDialog from './components/RuleDialog'
import RulesPanel from './components/RulesPanel'
import Statements, { ImportReport } from './components/Statements'
import TotalsPanel from './components/TotalsPanel'
import TransactionList from './components/TransactionList'
import UploadPanel from './components/UploadPanel'

function Stripe() {
  return (
    <div className="flex h-1.5 w-full" aria-hidden="true">
      {Object.values(CATEGORY_COLORS).map((color) => (
        <div key={color} className="flex-1" style={{ backgroundColor: color }} />
      ))}
    </div>
  )
}

export default function App() {
  const [meta, setMeta] = useState(null)
  const [statements, setStatements] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [rows, setRows] = useState([])
  const [summary, setSummary] = useState(null)
  const [rules, setRules] = useState(null)
  const [filter, setFilter] = useState('needs_review')
  const [keepVisible, setKeepVisible] = useState(new Set())
  const [offer, setOffer] = useState(null)
  const [ruleDraft, setRuleDraft] = useState(null)
  const [notice, setNotice] = useState('')
  const [loadError, setLoadError] = useState('')

  const refresh = useCallback(async (statementId) => {
    try {
      const [list, txns, totals, ruleSet] = await Promise.all([
        api.statements(),
        api.transactions(statementId),
        api.summary(statementId),
        api.rules(),
      ])
      setStatements(list)
      setRows(txns)
      setSummary(totals)
      setRules(ruleSet)
      setLoadError('')
    } catch (error) {
      setLoadError(error.message)
    }
  }, [])

  useEffect(() => {
    api.meta().then(setMeta).catch((error) => setLoadError(error.message))
  }, [])

  useEffect(() => {
    // Fetch-on-change: the API is the source of truth, so reload whenever the selected statement changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh(selectedId)
  }, [selectedId, refresh])

  useEffect(() => {
    if (!notice) return undefined
    const timer = setTimeout(() => setNotice(''), 4500)
    return () => clearTimeout(timer)
  }, [notice])

  function changeFilter(value) {
    setFilter(value)
    setKeepVisible(new Set())
    setOffer(null)
  }

  async function handleUploaded(statement) {
    setOffer(null)
    setKeepVisible(new Set())
    setFilter(statement.report.needs_review ? 'needs_review' : 'all')
    if (selectedId === statement.id) await refresh(statement.id)
    else setSelectedId(statement.id)
  }

  // Runs an action and shows its error as a notice instead of failing silently.
  const guarded = (action) => async (...args) => {
    try {
      await action(...args)
    } catch (error) {
      setNotice(error.message)
    }
  }

  const correct = guarded(async (row, category) => {
    const updated = await api.correct(row.id, category)
    setKeepVisible((ids) => new Set(ids).add(row.id))
    setOffer(updated.rule_offer ? { ...updated.rule_offer, txnId: row.id } : null)
    await refresh(selectedId)
  })

  const undo = guarded(async (row) => {
    await api.correct(row.id, null)
    setOffer(null)
    await refresh(selectedId)
  })

  async function ruleCreated(result) {
    setRuleDraft(null)
    setOffer(null)
    const sorted = result.rows_decided
    setNotice(`Rule saved. ${sorted} ${sorted === 1 ? 'row was' : 'rows were'} sorted by it.`)
    await refresh(selectedId)
  }

  const deleteStatement = guarded(async (statement) => {
    if (!window.confirm(`Delete ${statement.filename} and all of its rows? This can't be undone.`)) return
    await api.deleteStatement(statement.id)
    if (selectedId === statement.id) setSelectedId(null)
    else await refresh(selectedId)
  })

  const deleteAll = guarded(async () => {
    if (!window.confirm('Delete every imported statement and transaction? Your rules are kept.')) return
    await api.deleteAll()
    setSelectedId(null)
    await refresh(null)
  })

  const toggleRule = guarded(async (rule) => {
    await api.toggleRule(rule.id, !rule.enabled)
    await refresh(selectedId)
  })

  const deleteRule = guarded(async (rule) => {
    if (!window.confirm(`Delete the rule for ${rule.pattern}? Rows it already sorted keep their category.`)) return
    await api.deleteRule(rule.id)
    await refresh(selectedId)
  })

  const selected = statements.find((s) => s.id === selectedId)

  return (
    <div className="min-h-screen">
      <Stripe />
      <header className="mx-auto flex max-w-7xl flex-wrap items-end justify-between gap-4 px-4 pt-8 pb-6 sm:px-6">
        <div className="max-w-2xl">
          <h1 className="font-display text-4xl font-extrabold tracking-tight sm:text-5xl">Statement Categorizer</h1>
          <p className="mt-2 text-ink-soft sm:text-lg">
            Sorts a freelance developer&apos;s bank statement for tax time. The rules decide what they can, and
            anything they aren&apos;t sure about waits for you.
          </p>
        </div>
        <a
          href={api.exportUrl(selectedId)}
          download
          className={`inline-flex items-center gap-2 rounded-lg bg-ink px-4 py-2.5 text-sm font-medium text-white hover:bg-[#0c1529] ${
            rows.length ? '' : 'pointer-events-none opacity-40'
          }`}
          aria-disabled={!rows.length}
        >
          Export CSV{selected ? ` for ${selected.filename}` : ''}
        </a>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 pb-16 sm:px-6">
        {loadError && (
          <p role="alert" className="rounded-xl bg-rani-soft px-4 py-3 text-[#9c1450]">
            {loadError}
          </p>
        )}

        <div className="grid gap-6 lg:grid-cols-[24rem_minmax(0,1fr)]">
          <UploadPanel meta={meta} onUploaded={handleUploaded} />
          <TotalsPanel summary={summary} onShowReview={() => changeFilter('needs_review')} />
        </div>

        <Statements
          statements={statements}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onDelete={deleteStatement}
          onDeleteAll={deleteAll}
        />
        <ImportReport statement={selected} />

        <TransactionList
          rows={rows}
          categories={meta?.categories ?? []}
          filter={filter}
          onFilter={changeFilter}
          keepVisible={keepVisible}
          offer={offer}
          onCorrect={correct}
          onUndo={undo}
          onMakeRule={(draft) => setRuleDraft(draft)}
          onDismissOffer={() => setOffer(null)}
        />

        <RulesPanel
          rules={rules}
          onNew={() => setRuleDraft({ pattern: '', match_type: 'contains', category: '' })}
          onToggle={toggleRule}
          onDelete={deleteRule}
        />
      </main>

      <footer className="border-t border-line bg-white">
        <p className="mx-auto max-w-7xl px-4 py-6 text-sm text-ink-soft sm:px-6">
          Categories are bookkeeping labels, not tax advice. PKR and USD are never added together and nothing is
          converted. Everything stays on this machine in a local SQLite file.
        </p>
      </footer>

      {ruleDraft && (
        <RuleDialog
          draft={ruleDraft}
          categories={meta?.categories ?? []}
          onClose={() => setRuleDraft(null)}
          onCreated={ruleCreated}
        />
      )}

      {notice && (
        <div role="status" className="fixed right-4 bottom-4 z-30 rounded-xl bg-ink px-4 py-3 text-sm text-white shadow-lg">
          {notice}
        </div>
      )}
    </div>
  )
}
