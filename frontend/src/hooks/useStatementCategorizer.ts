import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { fetchCategories, updateTransactionCategory, uploadStatement } from '../api'
import type { CategorizeResponse, CategorizedTransaction } from '../types'
import { effectiveCategory, isConfirmed, isDeductible, isReview } from '../utils/transactions'

export type TableFilter = 'all' | 'review' | 'confirmed' | 'deductible'

export function useStatementCategorizer() {
  const [categories, setCategories] = useState<string[]>([])
  const [result, setResult] = useState<CategorizeResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [rescanning, setRescanning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<TableFilter>('all')
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [updatingId, setUpdatingId] = useState<string | null>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const [fileSize, setFileSize] = useState<number | null>(null)
  const lastFileRef = useRef<File | null>(null)

  useEffect(() => {
    fetchCategories().then(setCategories).catch(() => {})
  }, [])

  const processFile = useCallback(async (file: File) => {
    setError(null)
    setLoading(true)
    lastFileRef.current = file
    setFileName(file.name)
    setFileSize(file.size)
    try {
      const data = await uploadStatement(file)
      setResult(data)
      setFilter(data.needs_review_count > 0 ? 'review' : 'all')
      setCategoryFilter(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }, [])

  const onFile = useCallback(
    (file: File | undefined) => {
      if (!file) return
      void processFile(file)
    },
    [processFile],
  )

  const loadSample = useCallback(async () => {
    setError(null)
    setLoading(true)
    try {
      const res = await fetch('/samples/freelance_designer_statement.csv')
      const blob = await res.blob()
      const file = new File([blob], 'freelance_designer_chase_q4.csv', { type: 'text/csv' })
      await processFile(file)
    } catch {
      setError('Could not load sample CSV')
    } finally {
      setLoading(false)
    }
  }, [processFile])

  const clearStatement = useCallback(() => {
    setResult(null)
    setFileName(null)
    setFileSize(null)
    lastFileRef.current = null
    setFilter('all')
    setCategoryFilter(null)
    setSearch('')
  }, [])

  const rescan = useCallback(async () => {
    if (!lastFileRef.current) return
    setRescanning(true)
    try {
      await processFile(lastFileRef.current)
    } finally {
      setRescanning(false)
    }
  }, [processFile])

  const onCategoryChange = async (txId: string, category: string) => {
    setUpdatingId(txId)
    setError(null)
    try {
      const data = await updateTransactionCategory(txId, category)
      setResult(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Update failed')
    } finally {
      setUpdatingId(null)
    }
  }

  const stats = useMemo(() => {
    if (!result) return null
    const txs = result.transactions
    let deductible = 0
    let transfers = 0
    let refunds = 0
    for (const tx of txs) {
      const cat = effectiveCategory(tx)
      if (cat === 'Transfer / Not Spending') transfers++
      else if (cat === 'Refund') refunds++
      else if (isDeductible(tx)) deductible++
    }
    const reviewTotal = txs
      .filter(isReview)
      .reduce((sum, t) => sum + t.amount, 0)
    const deductibleSpend = txs.filter(isDeductible).reduce((sum, t) => sum + t.amount, 0)
    return {
      total: txs.length,
      deductible,
      transfers,
      refunds,
      reviewTotal,
      deductibleSpend,
      taxSavings: Math.abs(deductibleSpend) * 0.3,
      confirmed: txs.filter(isConfirmed).length,
    }
  }, [result])

  const visibleRows = useMemo(() => {
    if (!result) return [] as CategorizedTransaction[]
    const q = search.trim().toLowerCase()
    return result.transactions.filter((tx) => {
      if (categoryFilter && effectiveCategory(tx) !== categoryFilter) return false
      if (filter === 'review' && !isReview(tx)) return false
      if (filter === 'confirmed' && !isConfirmed(tx)) return false
      if (filter === 'deductible' && !isDeductible(tx)) return false
      if (q) {
        const hay = `${tx.date} ${tx.description} ${tx.reason} ${effectiveCategory(tx)}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
  }, [result, filter, categoryFilter, search])

  const exportSummaryCsv = useCallback(() => {
    if (!result) return
    const header = 'date,description,amount,category,confidence,reason\n'
    const rows = result.transactions.map((tx) => {
      const esc = (s: string) => `"${s.replace(/"/g, '""')}"`
      return [
        esc(tx.date),
        esc(tx.description),
        tx.amount,
        esc(effectiveCategory(tx)),
        tx.confidence,
        esc(tx.reason),
      ].join(',')
    })
    const blob = new Blob([header + rows.join('\n')], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'schedule-c-summary.csv'
    a.click()
    URL.revokeObjectURL(url)
  }, [result])

  const setFilterAndClearCategory = (f: TableFilter) => {
    setCategoryFilter(null)
    setFilter(f)
  }

  const filterByCategory = (category: string) => {
    setCategoryFilter(category)
    setFilter('all')
  }

  return {
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
    setFilter: setFilterAndClearCategory,
    filterByCategory,
  }
}
