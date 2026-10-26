import { useMemo, useState } from 'react';
import { Search, SlidersHorizontal, ArrowDownLeft, ArrowUpRight, CircleAlert, ChevronDown, Check, PencilLine } from 'lucide-react';
import { CATEGORIES } from '../lib/api.js';

function money(value) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Math.abs(Number(value) || 0));
}
function displayDate(value) {
  if (!value) return '—';
  const date = new Date(`${value}`.length === 10 ? `${value}T12:00:00` : value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
function badgeClass(category) {
  const c = category.toLowerCase();
  if (c.includes('income') || c.includes('salary')) return 'cat-green';
  if (c.includes('review')) return 'cat-amber';
  if (c.includes('grocer') || c.includes('health')) return 'cat-teal';
  if (c.includes('transfer') || c.includes('refund')) return 'cat-violet';
  if (c.includes('housing') || c.includes('utilit')) return 'cat-blue';
  return 'cat-slate';
}

export default function TransactionTable({ transactions, onCategoryChange, savingId }) {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('All transactions');
  const [editing, setEditing] = useState(null);
  const [draft, setDraft] = useState('');
  const filtered = useMemo(() => transactions.filter(t => {
    const matchesQuery = `${t.description} ${t.category} ${t.date} ${t.amount}`.toLowerCase().includes(query.toLowerCase());
    const matchesFilter = filter === 'All transactions' || (filter === 'Needs review' ? t.needs_review || t.category.toLowerCase() === 'needs review' : t.amount < 0);
    return matchesQuery && matchesFilter;
  }), [transactions, query, filter]);

  async function save(row) {
    const ok = await onCategoryChange(row, draft);
    if (ok) setEditing(null);
  }

  return <section className="transactions-card">
    <div className="transactions-heading"><div><span className="eyebrow">YOUR ACTIVITY</span><h2>Transactions <span className="count-pill">{transactions.length}</span></h2><p>Review and fine-tune your transaction categories.</p></div><div className="table-actions"><label className="search-box"><Search size={16}/><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search transactions" aria-label="Search transactions"/></label><label className="filter-select"><SlidersHorizontal size={15}/><select value={filter} onChange={e => setFilter(e.target.value)} aria-label="Filter transactions"><option>All transactions</option><option>Needs review</option><option>Expenses</option></select><ChevronDown size={14}/></label></div></div>
    {transactions.length === 0 ? <div className="empty-state"><div className="empty-icon"><ArrowDownLeft size={22}/></div><h3>Your transactions will appear here</h3><p>Upload a CSV statement above to see categorized transactions and review suggestions.</p></div> : filtered.length === 0 ? <div className="empty-state compact"><Search size={22}/><h3>No matching transactions</h3><p>Try a different search or filter.</p></div> : <div className="table-scroll"><table><thead><tr><th>TRANSACTION</th><th>DATE</th><th>AMOUNT</th><th>CATEGORY</th><th>STATUS</th><th><span className="sr-only">Edit</span></th></tr></thead><tbody>
      {filtered.map(row => <tr key={row.id}>
        <td><div className="transaction-name"><span className={`merchant-icon ${row.amount < 0 ? 'expense-icon' : 'income-icon'}`}>{row.amount < 0 ? <ArrowUpRight size={16}/> : <ArrowDownLeft size={16}/>}</span><div><strong>{row.description}</strong><span>{row.reference || row.merchant_category || 'Statement transaction'}</span></div></div></td>
        <td className="date-cell">{displayDate(row.date)}</td><td><span className={`amount ${row.amount < 0 ? 'negative' : 'positive'}`}>{row.amount < 0 ? '−' : '+'}{money(row.amount)}</span></td>
        <td>{editing === row.id ? <div className="edit-category"><select value={draft} onChange={e => setDraft(e.target.value)} aria-label={`New category for ${row.description}`}>{CATEGORIES.map(c => <option key={c}>{c}</option>)}</select><button className="save-category" disabled={savingId === row.id} onClick={() => save(row)} aria-label="Save category"><Check size={15}/></button></div> : <button className={`category-badge ${badgeClass(row.category)}`} onClick={() => {setEditing(row.id);setDraft(row.category);}} title="Click to edit category">{row.category}<PencilLine size={12}/></button>}</td>
        <td>{row.needs_review || row.category.toLowerCase() === 'needs review' ? <span className="status-review"><CircleAlert size={13}/> Needs review</span> : <span className="status-done"><Check size={13}/> Categorized</span>}</td>
        <td><button className="row-edit" aria-label={`Edit ${row.description}`} onClick={() => {setEditing(row.id);setDraft(row.category);}}><PencilLine size={15}/></button></td>
      </tr>)}
    </tbody></table></div>}
    {transactions.length > 0 && <div className="table-bottom"><span>Showing <strong>{filtered.length}</strong> of <strong>{transactions.length}</strong> transactions</span><span className="table-note"><CircleAlert size={13}/> Check uncertain transactions before exporting</span></div>}
  </section>;
}
