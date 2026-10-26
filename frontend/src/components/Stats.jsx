import { ArrowDownLeft, ArrowUpRight, ChartNoAxesCombined, CircleAlert, Wallet } from 'lucide-react';

function currency(value) { return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(value); }
export default function Stats({ transactions }) {
  const income = transactions.filter(t => t.amount > 0 && !/refund|transfer/i.test(t.category)).reduce((s,t) => s + t.amount, 0);
  const expenses = transactions.filter(t => t.amount < 0).reduce((s,t) => s + Math.abs(t.amount), 0);
  const review = transactions.filter(t => t.needs_review || t.category.toLowerCase() === 'needs review').length;
  const stats = [
    { label: 'Total transactions', value: transactions.length.toLocaleString(), note: 'Across imported statements', icon: Wallet, color: 'stat-indigo' },
    { label: 'Money in', value: currency(income), note: 'Excludes transfer/refund labels', icon: ArrowDownLeft, color: 'stat-green' },
    { label: 'Money out', value: currency(expenses), note: 'Outgoing transactions', icon: ArrowUpRight, color: 'stat-blue' },
    { label: 'Needs review', value: review.toLocaleString(), note: review ? 'Review suggested categories' : 'You’re all caught up', icon: CircleAlert, color: review ? 'stat-amber' : 'stat-green' },
  ];
  return <div className="stats-grid">{stats.map(({label,value,note,icon:Icon,color}) => <article className="stat-card" key={label}><div className="stat-top"><span>{label}</span><span className={`stat-icon ${color}`}><Icon size={18}/></span></div><strong className="stat-value">{value}</strong><span className="stat-note">{note}</span></article>)}</div>;
}
