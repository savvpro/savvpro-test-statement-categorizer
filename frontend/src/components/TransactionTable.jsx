import React, { useState, useMemo } from 'react';
import TransactionRow from './TransactionRow';

export default function TransactionTable({
  transactions = [],
  categories = {},
  filter = 'all',
  onTransactionUpdate,
}) {
  const [sortField, setSortField] = useState('date');
  const [sortDirection, setSortDirection] = useState('desc');
  const [expandedRowId, setExpandedRowId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Filter transactions
  const filteredTransactions = useMemo(() => {
    return transactions.filter((t) => {
      // Category filter
      if (filter === 'needs_review' && !t.needs_review) return false;
      if (filter === 'deductions' && (!t.tax_deductible || t.direction !== 'OUTFLOW')) return false;
      if (filter !== 'all' && filter !== 'needs_review' && filter !== 'deductions' && t.category !== filter) return false;

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const m = (t.clean_merchant || '').toLowerCase();
        const r = (t.raw_description || '').toLowerCase();
        const c = (t.category || '').toLowerCase();
        return m.includes(q) || r.includes(q) || c.includes(q);
      }
      return true;
    });
  }, [transactions, filter, searchQuery]);

  // Sort transactions
  const sortedTransactions = useMemo(() => {
    return [...filteredTransactions].sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      if (sortField === 'amount' || sortField === 'confidence') {
        aVal = Number(aVal) || 0;
        bVal = Number(bVal) || 0;
      } else {
        aVal = String(aVal || '').toLowerCase();
        bVal = String(bVal || '').toLowerCase();
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredTransactions, sortField, sortDirection]);

  const handleSingleUpdate = (updatedTx) => {
    const updatedList = transactions.map((t) => (t.id === updatedTx.id ? updatedTx : t));
    onTransactionUpdate(updatedList);
  };

  const toggleExpand = (txId) => {
    setExpandedRowId((prev) => (prev === txId ? null : txId));
  };

  const getSortIndicator = (field) => {
    if (sortField !== field) return ' ↕';
    return sortDirection === 'asc' ? ' ↑' : ' ↓';
  };

  return (
    <div className="glass-card ledger-card">
      <div className="ledger-header">
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.02em' }}>
            Recent Transactions
          </h2>
          <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Showing {sortedTransactions.length} of {transactions.length} reconciled bank items
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Quick Search */}
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              placeholder="Search merchant, category..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                padding: '6px 12px 6px 30px',
                fontSize: '12px',
                borderRadius: 'var(--radius-pill)',
                border: '1px solid var(--glass-border-subtle)',
                background: 'rgba(255, 255, 255, 0.9)',
                outline: 'none',
                width: '210px',
                fontFamily: 'inherit',
              }}
            />
            <span style={{ position: 'absolute', left: '10px', top: '7px', fontSize: '12px', color: 'var(--text-muted)' }}>
              🔍
            </span>
          </div>
        </div>
      </div>

      <div className="table-glass-container">
        <table className="frosted-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('date')}>Date{getSortIndicator('date')}</th>
              <th onClick={() => handleSort('clean_merchant')}>Merchant{getSortIndicator('clean_merchant')}</th>
              <th onClick={() => handleSort('amount')}>Amount{getSortIndicator('amount')}</th>
              <th>Direction</th>
              <th onClick={() => handleSort('category')}>Tax Category{getSortIndicator('category')}</th>
              <th onClick={() => handleSort('confidence')}>Confidence{getSortIndicator('confidence')}</th>
              <th>Status</th>
              <th style={{ textAlign: 'right' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {sortedTransactions.length === 0 ? (
              <tr>
                <td colSpan="8" style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                  No transactions match the selected filter.
                </td>
              </tr>
            ) : (
              sortedTransactions.map((tx) => (
                <TransactionRow
                  key={tx.id}
                  transaction={tx}
                  categories={categories}
                  onUpdate={handleSingleUpdate}
                  isExpanded={expandedRowId === tx.id}
                  onToggleExpand={() => toggleExpand(tx.id)}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
