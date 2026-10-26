import React from 'react'
import { Summary } from '../types'

interface Props {
  summary: Summary | null
}

export default function Summarypanel({ summary }: Props) {
  if (!summary) return null

  return (
    <div className="card">
      <h2>Summary</h2>
      <div className="grid4">
        <div className="statbox">
          <div>Total Income</div>
          <div className="statval green">PKR {summary.totalincome.toLocaleString()}</div>
        </div>
        <div className="statbox">
          <div>Total Spending</div>
          <div className="statval red">PKR {summary.totalspending.toLocaleString()}</div>
        </div>
        <div className="statbox">
          <div>Net</div>
          <div className="statval">PKR {(summary.totalincome + summary.totalspending).toLocaleString()}</div>
        </div>
        <div className="statbox">
          <div>Needs Review</div>
          <div className="statval red">{summary.needsreviewcount}</div>
        </div>
      </div>
      <h3>Totals by Category (Net of Refunds)</h3>
      <table>
        <tbody>
          {Object.entries(summary.totalspercategory).map(([cat, amt]) => (
            <tr key={cat}>
              <td>{cat}</td>
              <td>PKR {Number(amt).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}