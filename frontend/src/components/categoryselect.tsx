import React, { useState, useEffect } from 'react'
import { fetchapi } from '../api'

interface Props {
  txnid: number
  currentcategory: string
  suggestedcategory: string | null
  onupdated: () => void
}

export default function Categoryselect({ txnid, currentcategory, suggestedcategory, onupdated }: Props) {
  const [categories, setcategories] = useState<string[]>([])
  const [selected, setselected] = useState(currentcategory === "Needs Review" ? (suggestedcategory || "") : currentcategory)
  const [createrule, setcreaterule] = useState(true)
  const [loading, setloading] = useState(false)

  useEffect(() => {
    fetchapi("/api/categories").then(setcategories)
  }, [])

  const handlesave = async () => {
    if (!selected || selected === "Needs Review") return
    setloading(true)
    try {
      await fetchapi(`/api/transactions/${txnid}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category: selected, createrule })
      })
      onupdated()
    } finally {
      setloading(false)
    }
  }

  if (currentcategory !== "Needs Review") {
    return <span>{currentcategory}</span>
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      <select value={selected} onChange={(e) => setselected(e.target.value)}>
        <option value="">{suggestedcategory ? "Select category..." : "Needs Review"}</option>
        {categories.filter(c => c !== "Needs Review").map(c => (
          <option key={c} value={c}>{c}</option>
        ))}
      </select>
      <label style={{ fontSize: 11 }}>
        <input type="checkbox" checked={createrule} onChange={(e) => setcreaterule(e.target.checked)} />
        Remember for similar
      </label>
      <button onClick={handlesave} disabled={loading || !selected} style={{ fontSize: 11 }}>
        {loading ? "Saving..." : "Save"}
      </button>
    </div>
  )
}