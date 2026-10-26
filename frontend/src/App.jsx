import React, { useEffect, useMemo, useState } from 'react';
import { checkHealth, getCurrentStatement, updateTransactionCategory } from './api';
import FilterBar from './components/FilterBar';
import Navbar from './components/Navbar';
import SpendingBreakdown from './components/SpendingBreakdown';
import SummaryCards from './components/SummaryCards';
import TransactionTable from './components/TransactionTable';
import UploadSection from './components/UploadSection';

export default function App() {
  const [statement, setStatement] = useState(null);
  const [loading, setLoading] = useState(false);
  const [updatingTxId, setUpdatingTxId] = useState(null);
  const [error, setError] = useState(null);
  const [warnings, setWarnings] = useState([]);
  const [backendConnected, setBackendConnected] = useState(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [selectedStatus, setSelectedStatus] = useState('ALL');

  // Verify backend connectivity on mount
  useEffect(() => {
    async function init() {
      try {
        await checkHealth();
        setBackendConnected(true);
        // Attempt to restore any session statement if present
        const curr = await getCurrentStatement();
        if (curr) {
          setStatement(curr);
        }
      } catch (err) {
        setBackendConnected(false);
      }
    }
    init();
  }, []);

  const handleUploadSuccess = (data) => {
    setStatement(data);
    setWarnings(data.warnings || []);
    // Reset filters
    setSearchQuery('');
    setSelectedCategory('ALL');
    setSelectedStatus('ALL');
  };

  const handleCategoryChange = async (txId, newCategory) => {
    try {
      setUpdatingTxId(txId);
      const res = await updateTransactionCategory(txId, newCategory);

      // Update local statement with updated transaction and fresh summary
      setStatement((prev) => {
        if (!prev) return prev;
        const updatedList = prev.transactions.map((tx) =>
          tx.id === txId ? res.transaction : tx
        );
        return {
          ...prev,
          transactions: updatedList,
          summary: res.summary,
        };
      });
    } catch (err) {
      setError(err.message || 'Failed to update category.');
    } finally {
      setUpdatingTxId(null);
    }
  };

  // Filtered transactions computation
  const filteredTransactions = useMemo(() => {
    if (!statement || !statement.transactions) return [];

    return statement.transactions.filter((tx) => {
      // 1. Text search (description, date, or matched rule)
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesDesc = tx.description.toLowerCase().includes(q);
        const matchesDate = tx.date.toLowerCase().includes(q);
        const matchesRule = tx.matched_rule.toLowerCase().includes(q);
        if (!matchesDesc && !matchesDate && !matchesRule) {
          return false;
        }
      }

      // 2. Category filter
      if (selectedCategory !== 'ALL' && tx.category !== selectedCategory) {
        return false;
      }

      // 3. Status filter
      if (selectedStatus === 'needs_review') {
        return tx.category === 'Needs Review' || tx.status === 'needs_review';
      }
      if (selectedStatus === 'categorized') {
        return tx.status === 'categorized';
      }
      if (selectedStatus === 'manual') {
        return tx.status === 'manual' || tx.is_reviewed;
      }

      return true;
    });
  }, [statement, searchQuery, selectedCategory, selectedStatus]);

  return (
    <div className="container">
      <Navbar backendConnected={backendConnected} />

      <UploadSection
        onUploadSuccess={handleUploadSuccess}
        loading={loading}
        setLoading={setLoading}
        error={error}
        setError={setError}
        warnings={warnings}
        setWarnings={setWarnings}
      />

      {statement && statement.summary && (
        <>
          <SummaryCards summary={statement.summary} />

          <SpendingBreakdown
            summary={statement.summary}
            selectedCategory={selectedCategory}
            onSelectCategory={setSelectedCategory}
          />

          <FilterBar
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            selectedCategory={selectedCategory}
            setSelectedCategory={setSelectedCategory}
            selectedStatus={selectedStatus}
            setSelectedStatus={setSelectedStatus}
            needsReviewCount={statement.summary.needs_review_count}
            totalCount={statement.transactions.length}
            filteredCount={filteredTransactions.length}
          />

          <TransactionTable
            transactions={filteredTransactions}
            onCategoryChange={handleCategoryChange}
            updatingTxId={updatingTxId}
          />
        </>
      )}

      {!statement && !loading && (
        <div className="empty-state">
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📋</div>
          <h3>No Statement Loaded</h3>
          <p>
            Upload your bank or credit card CSV file above, or click <strong>Load Freelancer Sample</strong> to explore the app with realistic sample data.
          </p>
          <div style={{ display: 'inline-flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'center' }}>
            <span className="badge badge-neutral">⚡ 100% Deterministic Engine</span>
            <span className="badge badge-neutral">🔒 Runs Locally — No External AI</span>
            <span className="badge badge-neutral">📝 Full Audit Trail per Row</span>
          </div>
        </div>
      )}
    </div>
  );
}
