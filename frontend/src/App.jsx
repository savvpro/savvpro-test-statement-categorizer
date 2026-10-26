import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import SampleSelector from './components/SampleSelector';
import MetricsOverview from './components/MetricsOverview';
import TaxSummaryCard from './components/TaxSummaryCard';
import TransactionTable from './components/TransactionTable';
import ReviewModal from './components/ReviewModal';
import ExportModal from './components/ExportModal';

import {
  getCategories,
  getSampleStatements,
  loadSampleStatement,
  uploadStatement,
  addCustomRule,
  recalculateTransactions,
} from './services/api';

export default function App() {
  const [samples, setSamples] = useState([]);
  const [activeSampleId, setActiveSampleId] = useState('freelance-cc');
  const [transactions, setTransactions] = useState([]);
  const [taxSummary, setTaxSummary] = useState(null);
  const [allCategories, setAllCategories] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const [activeFilterTab, setActiveFilterTab] = useState('ALL');
  const [reviewingTransaction, setReviewingTransaction] = useState(null);
  const [isExportOpen, setIsExportOpen] = useState(false);

  // Initial load
  useEffect(() => {
    async function init() {
      setIsLoading(true);
      setError(null);
      try {
        const [catsRes, samplesRes] = await Promise.all([
          getCategories(),
          getSampleStatements(),
        ]);
        setAllCategories(catsRes.categories || []);
        setSamples(samplesRes || []);

        // Load default preset: freelance-cc
        const defaultData = await loadSampleStatement('freelance-cc');
        setTransactions(defaultData.transactions || []);
        setTaxSummary(defaultData.tax_summary || null);
      } catch (err) {
        console.error('Initialization error:', err);
        setError('Failed to load initial data. Ensure the backend server is running on http://127.0.0.1:8000.');
      } finally {
        setIsLoading(false);
      }
    }
    init();
  }, []);

  // Handle selecting a sample preset
  const handleSelectSample = async (sampleId) => {
    setActiveSampleId(sampleId);
    setIsLoading(true);
    setError(null);
    try {
      const data = await loadSampleStatement(sampleId);
      setTransactions(data.transactions || []);
      setTaxSummary(data.tax_summary || null);
      setActiveFilterTab('ALL');
    } catch (err) {
      console.error(err);
      setError(`Failed to load preset ${sampleId}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle CSV file upload
  const handleFileUpload = async (file) => {
    setActiveSampleId(null);
    setIsLoading(true);
    setError(null);
    try {
      const data = await uploadStatement(file);
      setTransactions(data.transactions || []);
      setTaxSummary(data.tax_summary || null);
      setActiveFilterTab('ALL');
    } catch (err) {
      console.error(err);
      setError(err.message || 'Error parsing statement file');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle saving a review / categorization fix
  const handleSaveReview = async ({ id, category, applyToMerchant, merchantPattern, notes }) => {
    try {
      setIsLoading(true);
      if (applyToMerchant && merchantPattern) {
        await addCustomRule(merchantPattern, category);
      }

      // Update matching or current transaction
      const updatedTxs = transactions.map((tx) => {
        const shouldUpdate =
          tx.id === id ||
          (applyToMerchant &&
            (tx.cleaned_merchant || '').toUpperCase() === merchantPattern.toUpperCase());

        if (shouldUpdate) {
          const catMeta = allCategories.find((c) => c.name === category);
          const deductPct = catMeta ? catMeta.deductibility_pct : 1.0;
          const isExp = catMeta ? catMeta.is_expense : true;
          const isInc = catMeta ? catMeta.is_income : false;
          const absAmt = Math.abs(tx.amount);
          const dedAmt = isExp ? Math.round(absAmt * deductPct * 100) / 100 : 0.0;

          return {
            ...tx,
            category: category,
            confidence: 1.0,
            needs_review: false,
            schedule_c_line: catMeta ? catMeta.schedule_c_line : tx.schedule_c_line,
            deductibility_pct: deductPct,
            deductible_amount: dedAmt,
            is_expense: isExp,
            is_income: isInc,
            color: catMeta ? catMeta.color : '#6366f1',
            reason: `User assigned category for '${merchantPattern || tx.cleaned_merchant}'.`,
            user_overridden: true,
            notes: notes || tx.notes,
          };
        }
        return tx;
      });

      // Recalculate summary from backend
      const res = await recalculateTransactions(updatedTxs);
      setTransactions(res.transactions);
      setTaxSummary(res.tax_summary);
      setReviewingTransaction(null);
    } catch (err) {
      console.error('Error saving review:', err);
      setError('Failed to update category.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFilterNeedsReview = () => {
    if (activeFilterTab === 'NEEDS_REVIEW') {
      setActiveFilterTab('ALL');
    } else {
      setActiveFilterTab('NEEDS_REVIEW');
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header
        onExportClick={() => setIsExportOpen(true)}
        transactionCount={transactions.length}
        needsReviewCount={taxSummary ? taxSummary.needs_review_count : 0}
      />

      <main style={{ maxWidth: 1400, margin: '0 auto', width: '100%', padding: '24px', display: 'flex', flexDirection: 'column', gap: 24 }}>
        {/* Error Alert */}
        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            color: '#f87171',
            padding: '12px 18px',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.85rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span>{error}</span>
            <button onClick={() => setError(null)} className="btn btn-secondary btn-sm">
              Dismiss
            </button>
          </div>
        )}

        {/* Preset Selector & File Dropzone */}
        <SampleSelector
          samples={samples}
          activeSampleId={activeSampleId}
          onSelectSample={handleSelectSample}
          onFileUpload={handleFileUpload}
          isLoading={isLoading}
        />

        {/* Financial KPI Cards */}
        {taxSummary && (
          <MetricsOverview
            taxSummary={taxSummary}
            onFilterNeedsReview={handleFilterNeedsReview}
            isNeedsReviewActive={activeFilterTab === 'NEEDS_REVIEW'}
          />
        )}

        {/* IRS Schedule C Breakdown Bar */}
        {taxSummary && <TaxSummaryCard taxSummary={taxSummary} />}

        {/* Main Transactions Table */}
        <TransactionTable
          transactions={transactions}
          onReviewClick={(tx) => setReviewingTransaction(tx)}
          activeFilterTab={activeFilterTab}
          onTabChange={(tab) => setActiveFilterTab(tab)}
          allCategories={allCategories}
        />
      </main>

      {/* Footer */}
      <footer style={{
        marginTop: 'auto',
        borderTop: '1px solid var(--border-subtle)',
        padding: '20px 24px',
        textAlign: 'center',
        fontSize: '0.78rem',
        color: 'var(--text-muted)',
      }}>
        TaxBrain Statement Categorizer • Built for Freelancers & Sole Proprietors • IRS Schedule C Compliance Engine
      </footer>

      {/* Review Modal */}
      {reviewingTransaction && (
        <ReviewModal
          transaction={reviewingTransaction}
          allCategories={allCategories}
          onClose={() => setReviewingTransaction(null)}
          onSave={handleSaveReview}
        />
      )}

      {/* Export Modal */}
      {isExportOpen && taxSummary && (
        <ExportModal
          transactions={transactions}
          taxSummary={taxSummary}
          onClose={() => setIsExportOpen(false)}
        />
      )}
    </div>
  );
}
