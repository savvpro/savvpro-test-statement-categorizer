import React from 'react'

interface Props {
  current: string
  onchange: (val: string) => void
}

export default function Filters({ current, onchange }: Props) {
  const tabs = [
    { id: "all", label: "All" },
    { id: "review", label: "Needs Review" },
    { id: "confident", label: "Confident" }
  ]

  return (
    <div className="flex" style={{ marginBottom: 20 }}>
      {tabs.map(t => (
        <button
          key={t.id}
          className={`filterbtn ${current === t.id ? "active" : ""}`}
          onClick={() => onchange(t.id)}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}