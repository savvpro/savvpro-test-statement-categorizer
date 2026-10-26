
import { useEffect, useRef, useState } from "react";
import axios from "axios";
import {
  Activity,
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  ChevronDown,
  CircleHelp,
  FileSpreadsheet,
  FileUp,
  Filter,
  RefreshCw,
  Search,
  ShieldCheck,
  Wallet,
  X,
} from "lucide-react";
import { api } from "./api";
import "./App.css";

type Transaction = {
  id: number;
  statement_id?: number;
  date: string;
  description: string;
  amount: number;
  currency?: string | null;
  balance?: number | null;
  source_row?: number | null;
  category: string;
  status: string;
  reason?: string | null;
  confidence?: number;
  source?: string;
  corrected_category?: string | null;
};

type Summary = {
  transaction_count: number;
  total_income: number;
  total_spending: number;
  total_refunds: number;
  net_spending: number;
  needs_review_count: number;
};

const EMPTY_SUMMARY: Summary = {
  transaction_count: 0,
  total_income: 0,
  total_spending: 0,
  total_refunds: 0,
  net_spending: 0,
  needs_review_count: 0,
};

const CATEGORIES = [
  "Software",
  "Transportation",
  "Groceries",
  "Restaurants",
  "Subscription",
  "Income",
  "Utilities",
  "Healthcare",
  "Travel",
  "Refund",
  "Transfer",
  "Needs Review",
];

function formatMoney(value: number) {
  return new Intl.NumberFormat("en-PK", {
    style: "currency",
    currency: "PKR",
    maximumFractionDigits: 2,
  }).format(value || 0);
}

function App() {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summary, setSummary] = useState<Summary>(EMPTY_SUMMARY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [uploadName, setUploadName] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [savingId, setSavingId] = useState<number | null>(null);


  async function loadData() {
    setLoading(true);
    setError("");

    try {
      const transactionsResponse = await api.get("/transactions/");
      const statementId = transactionsResponse.data.statement_id;

      const summaryResponse = statementId
        ? await api.get("/reports/summary", {
            params: { statement_id: statementId },
          })
        : { data: EMPTY_SUMMARY };

      setTransactions(transactionsResponse.data.transactions ?? []);
      setSummary({ ...EMPTY_SUMMARY, ...summaryResponse.data });
    } catch (err) {
      if (axios.isAxiosError(err) && err.response) {
        setError(
          `Could not load dashboard data (${err.response.status}). Check the backend API.`,
        );
      } else {
        setError(
          "Could not connect to the backend. Make sure FastAPI is running on port 8000 and CORS is configured.",
        );
      }
    } finally {
      setLoading(false);
    }
  }


  useEffect(() => {
    void loadData();
  }, []);

  async function uploadStatement(file?: File) {
    if (!file) return;

    setError("");
    setMessage("");
    setUploadName(file.name);

    const extension = file.name.split(".").pop()?.toLowerCase();
    if (!["csv", "xlsx", "xls"].includes(extension ?? "")) {
      setError("Unsupported file type. Please upload a CSV, XLSX, or XLS file.");
      return;
    }

    if (file.size === 0) {
      setError("The selected file is empty. Please choose another file.");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setError("This file exceeds the 10 MB limit. Please upload a smaller file.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);

    try {
      // Let the browser/Axios set the multipart boundary automatically.
      const response = await api.post("/uploads/", formData, {
  headers: {
    "Content-Type": undefined,
  },
});

      if (!response.data?.success) {
        const details = response.data?.errors;
        setError(
          (Array.isArray(details) ? details.join(" ") : "") ||
            response.data?.message ||
            "The statement could not be processed. Check its column headers and data.",
        );
        return;
      }

      const count = response.data.transaction_count ?? 0;
      const reviewCount = response.data.review_count ?? 0;

      setMessage(
        `Successfully imported ${count} transaction${count === 1 ? "" : "s"}. ${
          reviewCount > 0
            ? `${reviewCount} need${reviewCount === 1 ? "s" : ""} review.`
            : "All transactions were categorized."
        }`,
      );

      await loadData();
    } catch (err) {
      if (axios.isAxiosError(err) && err.response) {
        const data = err.response.data;
        const detail = data?.detail;

        let readableDetail = "";
        if (typeof detail === "string") {
          readableDetail = detail;
        } else if (Array.isArray(detail)) {
          readableDetail = detail
            .map((item) => {
              const location = Array.isArray(item?.loc)
                ? item.loc.filter(Boolean).join(" â†’ ")
                : "";
              const message = typeof item?.msg === "string" ? item.msg : "";
              return [location, message].filter(Boolean).join(": ");
            })
            .filter(Boolean)
            .join("; ");
        } else if (typeof data?.message === "string") {
          readableDetail = data.message;
        }

        setError(
          readableDetail ||
            `Upload failed (${err.response.status}). ${
              err.response.status === 422
                ? "The backend rejected the upload fields. Check the file input and multipart request."
                : "Please check the file and try again."
            }`,
        );
      } else {
        setError(
          "Could not reach the backend. Check that FastAPI is running on port 8000 and CORS is configured.",
        );
      }
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function saveCategory(transactionId: number) {
    if (!selectedCategory.trim()) return;

    setSavingId(transactionId);
    setError("");
    setMessage("");

    try {
      await api.patch(
        `/transactions/${transactionId}/category`,
        null,
        { params: { category: selectedCategory } },
      );

      setMessage("Transaction category updated successfully.");
      setEditingId(null);
      await loadData();
    } catch (err) {
      if (axios.isAxiosError(err) && err.response) {
        const detail = err.response.data?.detail;
        setError(
          typeof detail === "string"
            ? detail
            : "Could not update the category. Please try again.",
        );
      } else {
        setError("Could not reach the backend. Check the API connection.");
      }
    } finally {
      setSavingId(null);
    }
  }

  function downloadCategorizedCsv() {
    if (filteredTransactions.length === 0) {
      setError("There are no transactions to export. Upload a statement first.");
      return;
    }

    const headers = [
      "Date",
      "Description",
      "Amount",
      "Category",
      "Status",
      "Reason",
      "Confidence",
      "Source",
      "Currency",
      "Balance",
    ];

    const escapeCsv = (value: unknown) => {
      const text = value == null ? "" : String(value);
      return `"${text.replace(/"/g, '""')}"`;
    };

    const rows = filteredTransactions.map((transaction) => [
      transaction.date,
      transaction.description,
      transaction.amount,
      transaction.category,
      transaction.status,
      transaction.reason ?? "",
      transaction.confidence ?? "",
      transaction.source ?? "",
      transaction.currency ?? "",
      transaction.balance ?? "",
    ]);

    const csv = [headers, ...rows]
      .map((row) => row.map(escapeCsv).join(","))
      .join("\r\n");

    const blob = new Blob(["\uFEFF", csv], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "categorized_transactions.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function downloadSampleCsv() {
    const sample = [
      "Transaction Date,Transaction Details,Debit,Credit,Balance",
      "2026-10-01,ADOBE CREATIVE CLOUD,2500,,47500",
      "2026-10-02,UBER TRIP,800,,46700",
      "2026-10-03,SALARY PAYMENT,,100000,146700",
      "2026-10-04,TRANSFER TO SAVINGS,5000,,141700",
      "2026-10-05,ONLINE PAYMENT REFUND,,1200,142900",
    ].join("\r\n");

    const blob = new Blob(["\uFEFF", sample], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "statement_categorizer_sample.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  const filteredTransactions = transactions.filter((transaction) => {
    const matchesSearch =
      transaction.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      transaction.category.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus =
      statusFilter === "all" || transaction.status === statusFilter;

    const matchesCategory =
      categoryFilter === "all" || transaction.category === categoryFilter;

    return matchesSearch && matchesStatus && matchesCategory;
  });

  const uniqueCategories = Array.from(
    new Set(transactions.map((transaction) => transaction.category)),
  ).sort();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Activity size={23} />
          </div>
          <div>
            <div className="brand-name">Ledgerly</div>
            <div className="brand-caption">STATEMENT CATEGORIZER</div>
          </div>
        </div>

        <div className="sidebar-label">WORKSPACE</div>
        <button className="nav-item active" type="button">
          <Wallet size={18} />
          <span>Overview</span>
        </button>
        <button
          className="nav-item"
          type="button"
          onClick={() => {
            document.getElementById("transactions")?.scrollIntoView({
              behavior: "smooth",
            });
          }}
        >
          <FileSpreadsheet size={18} />
          <span>Transactions</span>
          {summary.transaction_count > 0 && (
            <span className="nav-count">{summary.transaction_count}</span>
          )}
        </button>

        <div className="sidebar-spacer" />

        <div className="sidebar-note">
          <ShieldCheck size={20} />
          <div>
            <strong>Your data, your decisions</strong>
            <p>Review uncertain matches before relying on your reports.</p>
          </div>
        </div>

        <div className="sidebar-footer">STATEMENT CATEGORIZER Â· MVP</div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <div className="breadcrumb">Workspace / Overview</div>
            <h1>Financial overview</h1>
            <p className="page-subtitle">
              Understand your transactions, spot patterns, and review uncertain categories.
            </p>
          </div>

          <button
            className="button button-secondary refresh-button"
            onClick={() => void loadData()}
            disabled={loading}
            type="button"
          >
            <RefreshCw size={16} className={loading ? "spin" : ""} />
            Refresh
          </button>
        </header>

        {error && (
          <div className="alert alert-error" role="alert">
            <AlertCircle size={19} />
            <span>{error}</span>
            <button
              type="button"
              className="alert-close"
              aria-label="Dismiss error"
              onClick={() => setError("")}
            >
              <X size={16} />
            </button>
          </div>
        )}

        {message && (
          <div className="alert alert-success" role="status">
            <CheckCircle2 size={19} />
            <span>{message}</span>
            <button
              type="button"
              className="alert-close"
              aria-label="Dismiss message"
              onClick={() => setMessage("")}
            >
              <X size={16} />
            </button>
          </div>
        )}

        <section className="upload-section">
          <div className="section-heading">
            <div>
              <h2>Import a statement</h2>
              <p>Upload your bank or credit card statement to get started.</p>
            </div>
            <span className="format-badge">
              <ShieldCheck size={14} />
              CSV Â· XLSX Â· XLS
            </span>
          </div>

          <div
            className="upload-dropzone"
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              void uploadStatement(event.dataTransfer.files[0]);
            }}
          >
            <div className="upload-icon">
              <FileUp size={27} />
            </div>
            <div className="upload-title">Choose a statement to upload</div>
            <div className="upload-description">
              Select a CSV or Excel file from your device
            </div>

            <input
              ref={fileInputRef}
              id="statement-file"
              type="file"
              accept=".csv,.xlsx,.xls"
              className="visually-hidden"
              onChange={(event) => void uploadStatement(event.target.files?.[0])}
            />

            <button
              className="button button-primary"
              type="button"
              disabled={loading}
              onClick={() => fileInputRef.current?.click()}
            >
              <FileUp size={16} />
              {loading ? "Processingâ€¦" : "Choose file"}
            </button>

            {uploadName && (
              <div className="selected-file">
                <FileSpreadsheet size={15} />
                {uploadName}
              </div>
            )}

            <div className="upload-limits">Maximum file size: 10 MB</div>
          </div>

          <div className="format-help">
            <div className="format-help-heading">
              <div className="help-icon">
                <CircleHelp size={19} />
              </div>
              <div>
                <h3>How should your file be formatted?</h3>
                <p>Check these requirements before uploading.</p>
              </div>
              <button
                type="button"
                className="button button-outline sample-button"
                onClick={downloadSampleCsv}
              >
                <FileSpreadsheet size={15} />
                Download sample CSV
              </button>
            </div>

            <div className="format-requirements">
              <div className="requirement">
                <CheckCircle2 size={16} />
                <div>
                  <strong>Required: Date and Description</strong>
                  <p>
                    Date can be â€œTransaction Dateâ€ or â€œPosting Dateâ€.
                    Description can be â€œTransaction Detailsâ€, â€œNarrationâ€,
                    â€œMerchantâ€, â€œPayeeâ€, or â€œMemoâ€.
                  </p>
                </div>
              </div>
              <div className="requirement">
                <CheckCircle2 size={16} />
                <div>
                  <strong>Required: Amount or Debit and Credit</strong>
                  <p>
                    Use one Amount column, or provide both Debit and Credit
                    columns. For debit/credit files, debits are treated as
                    money out and credits as money in.
                  </p>
                </div>
              </div>
              <div className="requirement">
                <CheckCircle2 size={16} />
                <div>
                  <strong>One transaction per row</strong>
                  <p>
                    Put column headers in the first row and use valid dates and
                    numeric amounts. Currency and Balance columns are optional.
                  </p>
                </div>
              </div>
            </div>

            <div className="sample-table-wrap">
              <div className="sample-table-heading">Example file preview</div>
              <table className="sample-table">
                <thead>
                  <tr>
                    <th>Transaction Date</th>
                    <th>Transaction Details</th>
                    <th className="number-cell">Debit</th>
                    <th className="number-cell">Credit</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>2026-10-01</td>
                    <td>ADOBE CREATIVE CLOUD</td>
                    <td className="number-cell">2,500</td>
                    <td className="number-cell">â€”</td>
                  </tr>
                  <tr>
                    <td>2026-10-02</td>
                    <td>UBER TRIP</td>
                    <td className="number-cell">800</td>
                    <td className="number-cell">â€”</td>
                  </tr>
                  <tr>
                    <td>2026-10-03</td>
                    <td>SALARY PAYMENT</td>
                    <td className="number-cell">â€”</td>
                    <td className="number-cell">100,000</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <p className="format-footnote">
              <AlertCircle size={14} />
              Unrecognized transactions are marked â€œNeeds Reviewâ€ instead of
              being assigned a category without sufficient evidence.
            </p>
          </div>
        </section>

        <section className="metrics-grid">
          <div className="metric-card">
            <div className="metric-top">
              <span>Total transactions</span>
              <span className="metric-icon metric-icon-blue">
                <FileSpreadsheet size={18} />
              </span>
            </div>
            <div className="metric-value">{summary.transaction_count}</div>
            <div className="metric-footnote">Imported transactions</div>
          </div>

          <div className="metric-card">
            <div className="metric-top">
              <span>Total income</span>
              <span className="metric-icon metric-icon-green">
                <ArrowDownRight size={18} />
              </span>
            </div>
            <div className="metric-value">{formatMoney(summary.total_income)}</div>
            <div className="metric-footnote">Recognized incoming funds</div>
          </div>

          <div className="metric-card">
            <div className="metric-top">
              <span>Total spending</span>
              <span className="metric-icon metric-icon-orange">
                <ArrowUpRight size={18} />
              </span>
            </div>
            <div className="metric-value">
              {formatMoney(summary.total_spending)}
            </div>
            <div className="metric-footnote">Excludes recognized transfers</div>
          </div>

          <div className="metric-card">
            <div className="metric-top">
              <span>Needs review</span>
              <span className="metric-icon metric-icon-purple">
                <CircleHelp size={18} />
              </span>
            </div>
            <div className="metric-value">{summary.needs_review_count}</div>
            <div className="metric-footnote">Transactions needing attention</div>
          </div>
        </section>

        <section className="transactions-section" id="transactions">
          <div className="section-heading transaction-heading">
            <div>
              <h2>Transactions</h2>
              <p>Inspect categories and correct any mistakes.</p>
            </div>
            <span className="result-count">
              {filteredTransactions.length} result
              {filteredTransactions.length === 1 ? "" : "s"}
            </span>
          </div>

          <div className="table-toolbar">
            <div className="search-box">
              <Search size={17} />
              <input
                type="search"
                placeholder="Search descriptions or categoriesâ€¦"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
              />
            </div>

            <label className="filter-control">
              <Filter size={15} />
              <select
                aria-label="Filter by status"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
              >
                <option value="all">All statuses</option>
                <option value="categorized">Categorized</option>
                <option value="needs_review">Needs review</option>
                <option value="reviewed">Reviewed</option>
              </select>
              <ChevronDown size={14} />
            </label>

            <label className="filter-control">
              <select
                aria-label="Filter by category"
                value={categoryFilter}
                onChange={(event) => setCategoryFilter(event.target.value)}
              >
                <option value="all">All categories</option>
                {uniqueCategories.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
              <ChevronDown size={14} />
            </label>
          </div>

          <div className="table-container">
            <table className="transactions-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Description</th>
                  <th>Category</th>
                  <th>Status</th>
                  <th className="number-cell">Amount</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredTransactions.map((transaction) => (
                  <tr key={transaction.id}>
                    <td className="date-cell">{transaction.date}</td>
                    <td>
                      <div className="transaction-description">
                        {transaction.description}
                      </div>
                      {transaction.reason && (
                        <div className="transaction-reason">
                          {transaction.reason}
                        </div>
                      )}
                    </td>
                    <td>
                      {editingId === transaction.id ? (
                        <select
                          className="category-select"
                          aria-label={`Choose category for ${transaction.description}`}
                          value={selectedCategory}
                          onChange={(event) =>
                            setSelectedCategory(event.target.value)
                          }
                        >
                          {CATEGORIES.map((category) => (
                            <option key={category} value={category}>
                              {category}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span
                          className={`category-pill ${
                            transaction.category === "Needs Review"
                              ? "category-review"
                              : transaction.category === "Income"
                                ? "category-income"
                                : transaction.category === "Transfer" ||
                                    transaction.category === "Refund"
                                  ? "category-neutral"
                                  : "category-default"
                          }`}
                        >
                          {transaction.category}
                        </span>
                      )}
                    </td>
                    <td>
                      <span
                        className={`status-pill ${
                          transaction.status === "needs_review"
                            ? "status-review"
                            : transaction.status === "reviewed"
                              ? "status-reviewed"
                              : "status-categorized"
                        }`}
                      >
                        {transaction.status === "needs_review"
                          ? "Needs review"
                          : transaction.status === "reviewed"
                            ? "Reviewed"
                            : "Categorized"}
                      </span>
                    </td>
                    <td
                      className={`number-cell amount-cell ${
                        transaction.amount > 0 ? "amount-positive" : ""
                      }`}
                    >
                      {transaction.amount > 0 ? "+" : ""}
                      {formatMoney(transaction.amount)}
                    </td>
                    <td>
                      {editingId === transaction.id ? (
                        <div className="row-actions">
                          <button
                            type="button"
                            className="small-action save-action"
                            disabled={savingId === transaction.id}
                            onClick={() => void saveCategory(transaction.id)}
                          >
                            {savingId === transaction.id ? "Savingâ€¦" : "Save"}
                          </button>
                          <button
                            type="button"
                            className="small-action cancel-action"
                            onClick={() => setEditingId(null)}
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className="small-action edit-action"
                          onClick={() => {
                            setEditingId(transaction.id);
                            setSelectedCategory(transaction.category);
                          }}
                        >
                          Review
                        </button>
                      )}
                    </td>
                  </tr>
                ))}

                {filteredTransactions.length === 0 && (
                  <tr>
                    <td colSpan={6} className="empty-state">
                      <div className="empty-state-icon">
                        <FileSpreadsheet size={25} />
                      </div>
                      <strong>
                        {transactions.length === 0
                          ? "No transactions yet"
                          : "No matching transactions"}
                      </strong>
                      <p>
                        {transactions.length === 0
                          ? "Upload a CSV or Excel statement to see your transactions here."
                          : "Try changing your search or filters."}
                      </p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="table-footer">
            <span>
              Showing {filteredTransactions.length} of {transactions.length} transactions
            </span>
            <div className="row-actions">
              <button
                type="button"
                className="text-button"
                onClick={downloadCategorizedCsv}
                disabled={filteredTransactions.length === 0}
              >
                Download categorized CSV
              </button>
              <button
                type="button"
                className="text-button"
                onClick={() => {
                  setSearchTerm("");
                  setStatusFilter("all");
                  setCategoryFilter("all");
                }}
              >
                Clear filters
              </button>
            </div>
          </div>
        </section>

        <footer className="page-footer">
          <span>Statement Categorizer</span>
          <span>Review uncertain transactions before making financial decisions.</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
