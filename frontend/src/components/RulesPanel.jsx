import { useState } from 'react'
import { CategoryChip, Panel } from './ui'

const MATCH_WORDS = { contains: 'contains', starts_with: 'starts with', exact: 'is exactly' }
const USE_WORDS = {
  always: 'always business',
  usually: 'business on a business account',
  sometimes: 'always asks you',
  never: 'personal',
}

function BuiltIn({ rules }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-5 border-t border-line pt-4">
      <button onClick={() => setOpen(!open)} aria-expanded={open} className="text-sm font-medium underline underline-offset-2">
        {open ? 'Hide' : 'Show'} the {rules.length} built-in rules
      </button>
      {open && (
        <div className="mt-3 max-h-96 overflow-auto rounded-xl border border-line">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 bg-paper text-ink-soft">
              <tr>
                <th className="px-3 py-2 font-medium">Checked in</th>
                <th className="px-3 py-2 font-medium">Description contains</th>
                <th className="px-3 py-2 font-medium">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rules.map((rule) => (
                <tr key={rule.id}>
                  <td className="px-3 py-1.5 text-ink-soft">{rule.stage.replace('_', ' ')}</td>
                  <td className="px-3 py-1.5 font-medium">{rule.pattern}</td>
                  <td className="px-3 py-1.5">
                    {rule.category ? (
                      <>
                        {rule.category}
                        {rule.stage === 'merchants' && (
                          <span className="text-ink-soft">, {USE_WORDS[rule.business_use]}</span>
                        )}
                      </>
                    ) : (
                      <span className="text-[#7a5200]">Review{rule.suggest ? `, suggests ${rule.suggest}` : ''}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default function RulesPanel({ rules, onToggle, onDelete, onNew }) {
  const mine = rules?.user ?? []
  return (
    <Panel
      title="Your rules"
      aside={
        <button onClick={onNew} className="text-sm font-medium text-lapis underline underline-offset-2">
          New rule
        </button>
      }
    >
      {mine.length === 0 ? (
        <p className="text-ink-soft">
          No rules yet. When you fix a row, the app offers to turn the fix into a rule. Nothing is learned unless you
          say so.
        </p>
      ) : (
        <ul className="divide-y divide-line">
          {mine.map((rule) => (
            <li key={rule.id} className={`flex flex-wrap items-center gap-3 py-2.5 ${rule.enabled ? '' : 'opacity-55'}`}>
              <span className="min-w-0 flex-1 text-sm">
                Description {MATCH_WORDS[rule.match_type]} <strong>{rule.pattern}</strong>
              </span>
              <CategoryChip name={rule.category} muted={!rule.enabled} />
              <label className="inline-flex items-center gap-1.5 text-sm text-ink-soft">
                <input type="checkbox" checked={rule.enabled} onChange={() => onToggle(rule)} className="accent-lapis" />
                On
              </label>
              <button
                onClick={() => onDelete(rule)}
                className="text-sm text-ink-soft underline underline-offset-2 hover:text-brick"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
      <BuiltIn rules={rules?.built_in ?? []} />
    </Panel>
  )
}
