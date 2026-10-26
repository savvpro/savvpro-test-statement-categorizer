import React, { useState, useEffect, useMemo } from 'react';
import TopNavbar from './components/TopNavbar';
import FileUpload from './components/FileUpload';
import TaxDashboard from './components/TaxDashboard';
import OverviewChartCard from './components/OverviewChartCard';
import SideStatusCards from './components/SideStatusCards';
import CategoryFilter from './components/CategoryFilter';
import TransactionTable from './components/TransactionTable';
import { getCategories, recalculateSummary } from './utils/api';

export default function App() {
  const [statementData, setStatementData] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [summary, setSummary] = useState(null);
  const [categories, setCategories] = useState({});
  const [activeFilter, setActiveFilter] = useState('all');
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [warnings, setWarnings] = useState([]);

  useEffect(() => {
    getCategories()
      .then((catMap) => setCategories(catMap))
      .catch((err) => console.error('Failed to load category definitions:', err));
  }, []);

  const handleUploadComplete = (data) => {
    setStatementData(data);
    setTransactions(data.transactions || []);
    setSummary(data.summary || null);
    setWarnings(data.warnings || []);
    setActiveFilter('all');
    setActiveTab('Dashboard');
  };

  const handleReset = () => {
    setStatementData(null);
    setTransactions([]);
    setSummary(null);
    setWarnings([]);
    setActiveFilter('all');
    setActiveTab('Dashboard');
  };

  const handleTransactionsUpdate = async (updatedTxList) => {
    setTransactions(updatedTxList);
    try {
      const newSummary = await recalculateSummary(updatedTxList);
      setSummary(newSummary);
    } catch (err) {
      console.error('Recalculation error:', err);
    }
  };

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    if (tabId === 'Needs Review') {
      setActiveFilter('needs_review');
    } else if (tabId === 'Deductions') {
      setActiveFilter('deductions');
    } else {
      setActiveFilter('all');
    }
  };

  const handleFilterChange = (filterVal) => {
    setActiveFilter(filterVal);
    if (filterVal === 'needs_review') {
      setActiveTab('Needs Review');
    } else if (filterVal === 'deductions') {
      setActiveTab('Deductions');
    } else if (filterVal === 'all') {
      setActiveTab('Dashboard');
    }
  };

  const handleExportCsv = () => {
    if (!transactions || transactions.length === 0) return;

    const headers = [
      'Date', 'Raw Description', 'Clean Merchant', 'Amount', 'Direction',
      'Category', 'Tax Deductible', 'Deductible %', 'Deductible Amount',
      'Confidence', 'Status', 'Schedule C Line', 'Review Reason'
    ];

    const escapeCsv = (str) => {
      if (str === null || str === undefined) return '""';
      const s = String(str).replace(/"/g, '""');
      return `"${s}"`;
    };

    const rows = transactions.map((t) => [
      escapeCsv(t.date),
      escapeCsv(t.raw_description),
      escapeCsv(t.clean_merchant),
      t.amount,
      escapeCsv(t.direction),
      escapeCsv(t.category),
      t.tax_deductible ? 'YES' : 'NO',
      `${Math.round((t.deductible_percentage || 0) * 100)}%`,
      t.deductible_amount || 0.0,
      `${Math.round((t.confidence || 0) * 100)}%`,
      escapeCsv(t.status),
      escapeCsv(t.schedule_c_line),
      escapeCsv(t.review_reason || ''),
    ]);

    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\r\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${statementData?.filename || 'statement'}_tax_ledger.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const needsReviewCount = transactions.filter((t) => t.needs_review).length;

  const activeCategoryNames = useMemo(() => {
    const set = new Set();
    transactions.forEach((t) => {
      if (t.category && t.category !== 'Needs Review') {
        set.add(t.category);
      }
    });
    return Array.from(set).sort();
  }, [transactions]);

  return (
    <div className="dashboard-wrapper">
      {/* Top Application Bar matching reference */}
      <TopNavbar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        onReset={handleReset}
        hasData={Boolean(statementData)}
        needsReviewCount={needsReviewCount}
        onExportCsv={handleExportCsv}
      />

      {!statementData ? (
        <FileUpload onUploadComplete={handleUploadComplete} />
      ) : (
        <main>
          {/* Welcome Header from Reference */}
          <div className="welcome-banner">
            <h1 className="welcome-title">Good morning, Consultant! 👋</h1>
            <p className="welcome-subtitle">
              Statement <strong style={{ color: 'var(--text-main)' }}>{statementData.filename}</strong> reconciled with {transactions.length} transactions.
            </p>
          </div>

          {/* Warnings Banner */}
          {warnings && warnings.length > 0 && (
            <div className="warning-banner">
              <div>
                <strong>Notice:</strong> {warnings.join(' • ')}
              </div>
              <button
                type="button"
                onClick={() => setWarnings([])}
                style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontWeight: 700 }}
              >
                ✕
              </button>
            </div>
          )}

          {/* Top 4 Metrics Row */}
          <TaxDashboard summary={summary} needsReviewCount={needsReviewCount} />

          {/* 2-Column Main Layout: Left Overview & Table, Right Status & Radial Gauge */}
          <div className="main-two-columns">
            {/* Left Column Stack */}
            <div className="left-col-stack">
              {/* Average Sales / Deduction Overview Card */}
              <OverviewChartCard summary={summary} transactions={transactions} />

              {/* Filter Pills */}
              <CategoryFilter
                categories={activeCategoryNames}
                activeFilter={activeFilter}
                onFilterChange={handleFilterChange}
                needsReviewCount={needsReviewCount}
                totalCount={transactions.length}
              />

              {/* Transaction Ledger Table */}
              <TransactionTable
                transactions={transactions}
                categories={categories}
                filter={activeFilter}
                onTransactionUpdate={handleTransactionsUpdate}
              />
            </div>

            {/* Right Column Stack */}
            <SideStatusCards
              summary={summary}
              totalTransactions={transactions.length}
              onExport={handleExportCsv}
            />
          </div>
        </main>
      )}
    </div>
  );
}
