import React, { useState, useEffect } from 'react';
import {
  StatementPreviewResponse,
  SummaryResponse,
  Transaction,
  CategoryInfo,
  ParseIssue,
} from './types';
import {
  fetchHealth,
  fetchCategories,
  uploadStatement,
  loadDemoStatement,
  recalculateSummary,
  exportTransactionsCsv,
} from './services/api';

import { Header } from './components/Header';
import { UploadDropzone } from './components/UploadDropzone';
import { SummaryCards } from './components/SummaryCards';
import { CategoryBreakdown } from './components/CategoryBreakdown';
import { TransactionTable } from './components/TransactionTable';
import { ExplainModal } from './components/ExplainModal';
import { AlertTriangle, Info, CheckCircle2 } from 'lucide-react';

export const App: React.FC = () => {
  const [backendConnected, setBackendConnected] = useState(false);
  const [categories, setCategories] = useState<string[]>([]);
  const [categoryDescriptions, setCategoryDescriptions] = useState<Record<string, string>>({});

  const [statementData, setStatementData] = useState<StatementPreviewResponse | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [issues, setIssues] = useState<ParseIssue[]>([]);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);

  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [isExplainModalOpen, setIsExplainModalOpen] = useState(false);

  // Check health and load categories on mount
  useEffect(() => {
    fetchHealth()
      .then(() => setBackendConnected(true))
      .catch(() => setBackendConnected(false));

    fetchCategories()
      .then((data: CategoryInfo) => {
        setCategories(data.categories);
        setCategoryDescriptions(data.descriptions);
      })
      .catch((err) => console.error('Categories load error:', err));
  }, []);

  const handleFileUpload = async (file: File) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await uploadStatement(file);
      setStatementData(res);
      setTransactions(res.transactions);
      setSummary(res.summary);
      setIssues(res.issues);
      setSelectedCategory('');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to upload statement.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadDemo = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await loadDemoStatement();
      setStatementData(res);
      setTransactions(res.transactions);
      setSummary(res.summary);
      setIssues(res.issues);
      setSelectedCategory('');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load demo statement.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setStatementData(null);
    setTransactions([]);
    setSummary(null);
    setIssues([]);
    setErrorMessage(null);
    setSelectedCategory('');
  };

  // Inline category update with immediate summary recalculation
  const handleUpdateCategory = async (txnId: string, newCategory: string) => {
    const updated = transactions.map((tx) => {
      if (tx.id === txnId) {
        return {
          ...tx,
          category: newCategory,
          user_edited: true,
          needs_review: newCategory === 'Needs Review',
          reason: `Manually verified as ${newCategory}`,
        };
      }
      return tx;
    });

    setTransactions(updated);

    // Recalculate summary with updated transactions
    try {
      const newSummary = await recalculateSummary(updated);
      setSummary(newSummary);
    } catch (err) {
      console.error('Failed to recalculate summary:', err);
    }
  };

  const handleExportCsv = async () => {
    if (transactions.length === 0) return;
    setIsExporting(true);
    try {
      const blob = await exportTransactionsCsv(transactions);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `freelance-ledger-reviewed-transactions-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert(`Export failed: ${err.message || 'Unknown error'}`);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="app-container">
      <Header
        backendConnected={backendConnected}
        onOpenExplain={() => setIsExplainModalOpen(true)}
        onLoadDemo={handleLoadDemo}
        onReset={handleReset}
        hasTransactions={transactions.length > 0}
      />

      {/* Upload Zone / Welcome Screen */}
      {!summary && (
        <UploadDropzone
          onFileUpload={handleFileUpload}
          onLoadDemo={handleLoadDemo}
          isLoading={isLoading}
          errorMessage={errorMessage}
        />
      )}

      {/* Parse Issues Banner if any */}
      {issues.length > 0 && (
        <div className="issues-banner">
          <div className="issues-title">
            <AlertTriangle size={18} />
            <span>Notice: {issues.length} row(s) had formatting issues and were excluded from processing</span>
          </div>
          <ul style={{ paddingLeft: '20px', fontSize: '0.825rem', color: '#fca5a5' }}>
            {issues.slice(0, 3).map((iss, i) => (
              <li key={i}>
                Row {iss.row_number}: {iss.issue}
              </li>
            ))}
            {issues.length > 3 && <li>...and {issues.length - 3} more row(s)</li>}
          </ul>
        </div>
      )}

      {/* Main Workspace (Summary Cards, Distribution, and Transaction Table) */}
      {summary && (
        <>
          <SummaryCards
            summary={summary}
            onFilterNeedsReview={() =>
              setSelectedCategory(selectedCategory === 'Needs Review' ? '' : 'Needs Review')
            }
            isNeedsReviewActive={selectedCategory === 'Needs Review'}
          />

          <CategoryBreakdown
            breakdown={summary.category_breakdown}
            selectedCategory={selectedCategory}
            onSelectCategory={setSelectedCategory}
          />

          <TransactionTable
            transactions={transactions}
            categories={categories}
            selectedCategory={selectedCategory}
            onSelectCategory={setSelectedCategory}
            onUpdateCategory={handleUpdateCategory}
            onExportCsv={handleExportCsv}
            isExporting={isExporting}
          />
        </>
      )}

      {/* Educational / Explanatory Modal */}
      <ExplainModal
        isOpen={isExplainModalOpen}
        onClose={() => setIsExplainModalOpen(false)}
      />
    </div>
  );
};
