import { useMemo, useState } from 'react';
import { Landmark, Bell, CircleHelp, ChevronDown, Sparkles, ShieldCheck, ArrowRight, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react';
import UploadPanel from './components/UploadPanel.jsx';
import TransactionTable from './components/TransactionTable.jsx';
import Stats from './components/Stats.jsx';
import { uploadStatement, updateTransactionCategory, normalizeTransaction } from './lib/api.js';

export default function App() {
  const [transactions, setTransactions] = useState([]);
  const [busy, setBusy] = useState(false);
  const [savingId, setSavingId] = useState(null);
  const [notice, setNotice] = useState(null);
  const [statementName, setStatementName] = useState('');
  const reviewCount = useMemo(() => transactions.filter(t => t.needs_review || t.category.toLowerCase() === 'needs review').length, [transactions]);

  async function handleUpload(file) {
    setBusy(true); setNotice(null);
    try {
      const result = await uploadStatement(file);
      if (!result.transactions.length) {
        throw new Error('The upload succeeded, but the response did not contain a transaction list. Check the backend response format in FRONTEND_SETUP.md.');
      }
      setTransactions(result.transactions);
      setStatementName(file.name);
      setNotice({ type: 'success', text: `${result.transactions.length} transactions imported from ${file.name}.` });
      return true;
    } catch (error) {
      setNotice({ type: 'error', text: error.message });
      return false;
    } finally { setBusy(false); }
  }

  async function handleCategoryChange(row, category) {
    if (category === row.category) return true;
    setSavingId(row.id); setNotice(null);
    try {
      await updateTransactionCategory(row, category);
      setTransactions(current => current.map(t => t.id === row.id ? { ...t, category, needs_review: category.toLowerCase() === 'needs review' } : t));
      setNotice({ type: 'success', text: `Category updated to “${category}”.` });
      return true;
    } catch (error) {
      setNotice({ type: 'error', text: error.message });
      return false;
    } finally { setSavingId(null); }
  }

  function clearData() { setTransactions([]); setStatementName(''); setNotice(null); }

  return <div className="app-shell">
    <aside className="sidebar"><a className="brand" href="#top"><span className="brand-mark"><Landmark size={21}/></span><span>ledgerly<span className="brand-dot">.</span><small>STATEMENT CATEGORIZER</small></span></a>
      <div className="workspace-label">WORKSPACE</div><nav className="side-nav"><a className="nav-item active" href="#overview"><span className="nav-dot"/> Overview</a><a className="nav-item" href="#transactions"><span className="nav-dot nav-dot-blue"/> Transactions {reviewCount > 0 && <span className="nav-count">{reviewCount}</span>}</a><a className="nav-item" href="#import"><span className="nav-dot nav-dot-green"/> Import statement</a></nav>
      <div className="sidebar-spacer"/><div className="sidebar-security"><div className="security-icon"><ShieldCheck size={18}/></div><strong>Your data, your control</strong><p>Transactions stay with your local backend. No third-party AI categorization.</p><a href="#privacy">Privacy principles <ArrowRight size={13}/></a></div><div className="profile-row"><div className="avatar">YL</div><div><strong>Your workspace</strong><span>Personal account</span></div><ChevronDown size={16}/></div>
    </aside>
    <main className="main-content" id="top"><header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <strong>Overview</strong></div><div className="top-actions"><span className="backend-indicator"><span/> Local workspace</span><button className="top-icon" aria-label="Help" title="Help"><CircleHelp size={18}/></button><button className="top-icon notification-button" aria-label="Notifications" title="Notifications"><Bell size={18}/></button><div className="avatar avatar-small">YL</div></div></header>
      <div className="page-content"><section className="welcome-row" id="overview"><div><div className="welcome-kicker"><Sparkles size={14}/> YOUR FINANCES, ORGANIZED</div><h1>Good overview.<br/><span>Clearer money decisions.</span></h1><p>Bring your statement in. We’ll organize the details so you can focus on what matters.</p></div><div className="welcome-art" aria-hidden="true"><div className="art-orbit orbit-one"/><div className="art-orbit orbit-two"/><div className="art-card"><div className="art-card-top"><span/><span/><span/></div><div className="art-chart"><i/><i/><i/><i/><i/><i/><i/></div><div className="art-card-line"/><div className="art-card-line short"/></div><div className="art-spark">✳</div></div></section>
        {notice && <div className={`notice notice-${notice.type}`} role="status">{notice.type === 'success' ? <CheckCircle2 size={18}/> : <AlertTriangle size={18}/>}<span>{notice.text}</span><button onClick={() => setNotice(null)} aria-label="Dismiss message">×</button></div>}
        <Stats transactions={transactions}/>
        <div className="section-row" id="import"><div><h2>Statement workspace</h2><p>Import your transactions and review the results in one place.</p></div>{transactions.length > 0 && <button className="button button-quiet" onClick={clearData}><RefreshCw size={15}/> Start over</button>}</div>
        <UploadPanel onUpload={handleUpload} busy={busy}/>
        {statementName && <div className="loaded-statement"><div className="loaded-file-icon"><CheckCircle2 size={17}/></div><div><strong>{statementName}</strong><span>Imported successfully · {transactions.length} transactions</span></div><span className="loaded-status">Ready to review</span></div>}
        <div id="transactions"><TransactionTable transactions={transactions} onCategoryChange={handleCategoryChange} savingId={savingId}/></div>
        {transactions.length > 0 && reviewCount > 0 && <div className="review-banner"><div className="review-banner-icon"><AlertTriangle size={18}/></div><div><strong>{reviewCount} transaction{reviewCount === 1 ? '' : 's'} need your attention</strong><p>Review these items to keep your categories accurate. Ambiguous transactions are intentionally not guessed.</p></div><a href="#transactions">Review now <ArrowRight size={15}/></a></div>}
        <footer className="footer" id="privacy"><span>© 2026 Ledgerly · Statement Categorizer</span><span><ShieldCheck size={14}/> Built with privacy in mind</span><span>Categories are suggestions — always review your statements.</span></footer>
      </div>
    </main>
  </div>;
}
