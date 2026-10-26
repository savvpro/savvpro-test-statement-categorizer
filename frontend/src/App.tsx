import React, { useState, useEffect } from "react";
import { Header } from "./components/Header";
import { FileUpload } from "./components/FileUpload";
import { SummaryCards } from "./components/SummaryCards";
import { CategoryTotals } from "./components/CategoryTotals";
import { TransactionTable } from "./components/TransactionTable";
import {
  getCategories,
  uploadStatement,
  recalculateStatement,
  submitRuleCorrection,
  exportCategorizedCsv,
} from "./services/api";
import type { CategorizationResponse, CategorizedTransaction } from "./types";
import { Loader2 } from "lucide-react";
import "./App.css";

export const App: React.FC = () => {
  const [categories, setCategories] = useState<string[]>([]);
  const [statementData, setStatementData] = useState<CategorizationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState<string | null>(null);

  useEffect(() => {
    getCategories()
      .then((cats) => setCategories(cats))
      .catch((err) => {
        console.error("Failed to load tax categories:", err);
        setCategories([
          "Software & Subscriptions",
          "Cloud & Infrastructure",
          "Hardware & Office Equipment",
          "Internet & Utilities",
          "Professional & Legal Services",
          "Bank & Merchant Fees",
          "Travel & Transportation",
          "Meals & Client Entertainment",
          "Advertising & Marketing",
          "Client Income & Revenue",
          "Transfers & Card Payments",
          "Needs Review",
        ]);
      });
  }, []);

  const handleFileSelected = async (file: File) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await uploadStatement(file);
      setStatementData(response);
      setSelectedCategoryFilter(null);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to process statement.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCategoryChange = async (
    transactionId: string,
    newCategory: string,
    saveAsRule: boolean,
    normalizedDesc: string
  ) => {
    if (!statementData) return;

    const updatedTransactions: CategorizedTransaction[] = statementData.transactions.map((tx) => {
      if (tx.id === transactionId) {
        return {
          ...tx,
          category: newCategory,
          needs_review: newCategory === "Needs Review",
          confidence: 1.0,
          reason: saveAsRule
            ? `User rule override: ${normalizedDesc}`
            : "Manual user correction",
          user_overridden: true,
        };
      }
      return tx;
    });

    try {
      if (saveAsRule) {
        await submitRuleCorrection(transactionId, newCategory, true, normalizedDesc);
      }

      const updatedResponse = await recalculateStatement(
        updatedTransactions,
        statementData.filename
      );
      setStatementData(updatedResponse);
    } catch (err) {
      console.error("Error updating category:", err);
    }
  };

  const handleExport = async () => {
    if (!statementData) return;
    try {
      await exportCategorizedCsv(statementData);
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    }
  };

  const handleReset = () => {
    setStatementData(null);
    setErrorMessage(null);
    setSelectedCategoryFilter(null);
  };

  return (
    <div className="app-shell">
      <Header
        filename={statementData?.filename}
        onExport={handleExport}
        onReset={handleReset}
        isExportDisabled={!statementData || statementData.transactions.length === 0}
      />

      <main className="app-main-content">
        {!statementData ? (
          <div className="upload-view">
            <FileUpload
              onFileSelected={handleFileSelected}
              isLoading={isLoading}
              error={errorMessage}
            />
          </div>
        ) : (
          <div className="dashboard-view">
            {/* Top Metrics Cards */}
            <SummaryCards
              summary={statementData.summary}
              onFilterNeedsReview={() =>
                setSelectedCategoryFilter("Needs Review")
              }
            />

            {/* Split Content: Category Totals on Left, Table on Right */}
            <div className="dashboard-grid">
              <aside className="sidebar-totals">
                <CategoryTotals
                  totals={statementData.category_totals}
                  selectedCategory={selectedCategoryFilter}
                  onSelectCategory={(cat) =>
                    setSelectedCategoryFilter(cat || null)
                  }
                />
              </aside>

              <section className="main-table-section">
                <TransactionTable
                  transactions={statementData.transactions}
                  categories={categories}
                  onCategoryChange={handleCategoryChange}
                  activeFilterCategory={selectedCategoryFilter}
                  onClearCategoryFilter={() =>
                    setSelectedCategoryFilter(null)
                  }
                />
              </section>
            </div>
          </div>
        )}

        {isLoading && (
          <div className="loading-overlay">
            <div className="loading-card">
              <Loader2 size={36} className="spinner-icon" />
              <p>Analyzing statement with deterministic brain...</p>
              <span>Normalizing descriptions, linking refunds & checking rules</span>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
