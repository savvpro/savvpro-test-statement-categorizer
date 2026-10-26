import React, { useState, useEffect, useCallback } from 'react'
import { fetchapi } from './api'
import { Summary, Transaction } from './types'
import Uploadbox from './components/uploadbox'
import Summarypanel from './components/summarypanel'
import Filters from './components/filters'
import Transactiontable from './components/transactiontable'

export default function App() {
  const [uploadid, setuploadid] = useState<number | null>(null)
  const [summary, setsummary] = useState<Summary | null>(null)
  const [transactions, settransactions] = useState<Transaction[]>([])
  const [status, setstatus] = useState("all")

  const loaddata = useCallback(async () => {
    if (!uploadid) return
    const sum = await fetchapi(`/api/uploads/${uploadid}/summary`)
    setsummary(sum)
    const txns = await fetchapi(`/api/uploads/${uploadid}/transactions?status=${status}`)
    settransactions(txns)
  }, [uploadid, status])

  useEffect(() => {
    loaddata()
  }, [loaddata])

  return (
    <div className="container">
      <h1>Statement Categorizer</h1>
      <Uploadbox onuploadsuccess={setuploadid} />
      
      {uploadid && (
        <>
          <Summarypanel summary={summary} />
          <Filters current={status} onchange={setstatus} />
          <Transactiontable transactions={transactions} onupdated={loaddata} />
        </>
      )}
    </div>
  )
}