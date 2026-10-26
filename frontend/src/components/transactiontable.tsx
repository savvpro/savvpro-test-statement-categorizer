import React, { useState } from 'react'
import { Transaction } from '../types'
import Categoryselect from './categoryselect'

interface Props {
  transactions: Transaction[]
  onupdated: () => void
}

export default function Transactiontable({ transactions, onupdated }: Props) {
  const [expandedid, setexpandedid] = useState<number | null>(null)

  return (
    <div className="card" style={{ overflowX: "auto" }}>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Description</th>
            <th>Amount</th>
            <th>Category</th>
            <th>Confidence</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map(t => (
            <tr key={t.id} className={t.category === "Needs Review" ? "needsreviewrow" : ""}>
              <td style={{ whiteSpace: "nowrap" }}>{t.date}</td>
              <td>
                <div>{t.descriptionraw}</div>
                <div>
                  {t.isrefund && <span className="badge badgerefund">Refund</span>}
                  {t.isduplicate && <span className="badge badgeduplicate">Duplicate</span>}
                  {t.isrecurring && <span className="badge badgerecurring">Recurring</span>}
                </div>
              </td>
              <td className={t.amount < 0 ? "red" : "green"} style={{ whiteSpace: "nowrap" }}>
                {Number(t.amount).toLocaleString()}
              </td>
              <td>
                <Categoryselect
                  txnid={t.id}
                  currentcategory={t.category}
                  suggestedcategory={t.suggestedcategory}
                  onupdated={onupdated}
                />
              </td>
              <td>
                {Math.round(t.confidence * 100)}%
                <div className="confbar">
                  <div className="conffill" style={{ width: `${t.confidence * 100}%` }}></div>
                </div>
              </td>
              <td>
                <div style={{ fontSize: 13, cursor: "pointer", textDecoration: "underline" }} onClick={() => setexpandedid(expandedid === t.id ? null : t.id)}>
                  {t.reason}
                </div>
                {expandedid === t.id && (
                  <div className="evidencebox">
                    {t.conflicts.length > 0 && (
                      <div className="red" style={{ marginBottom: 5 }}>
                        <strong>Conflicts:</strong> {t.conflicts.join(", ")}
                      </div>
                    )}
                    <strong>Signals:</strong>
                    {t.signals.length === 0 ? " None" : (
                      <ul style={{ margin: "5px 0", paddingLeft: 20 }}>
                        {t.signals.map((s, idx) => (
                          <li key={idx}>{s.family} - {s.name} ({s.points > 0 ? "+" : ""}{s.points}): {s.text}</li>
                        ))}
                      </ul>
                    )}
                    <div><strong>Route:</strong> {t.route}</div>
                    <div><strong>Two reasons met:</strong> {t.tworeasonsmet ? "Yes" : "No"}</div>
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}