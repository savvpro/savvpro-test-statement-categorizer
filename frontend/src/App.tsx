
import { useState } from "react";
import "./App.css";

type Transaction = {
  description: string;
  amount: number;
  category: string;
  status: string;
  reason: string;
};

type UploadResponse = {
  filename: string;
  transaction_count: number;
  transactions: Transaction[];
};

const CATEGORIES = [
  "Software & Subscriptions",
  "Office Supplies",
  "Travel",
  "Meals",
  "Utilities",
  "Refund",
  "Transfer",
  "Income",
  "Other",
  "Needs Review",
];

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function uploadStatement() {
    if (!file) {
      setMessage("Please select a CSV file first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    setMessage("");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/transactions/upload",
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Unable to process this CSV file."
        );
      }

      const result = data as UploadResponse;

      setTransactions(result.transactions);
      setMessage(
        `Successfully processed ${result.transaction_count} transactions.`
      );
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Could not connect to the backend. Check that the API is running."
      );
    } finally {
      setLoading(false);
    }
  }

  function updateCategory(index: number, category: string) {
    setTransactions((current) =>
      current.map((transaction, i) =>
        i === index
          ? {
              ...transaction,
              category,
              status:
                category === "Needs Review" ? "Needs Review" : "Reviewed",
              reason: "Category manually reviewed by the user.",
            }
          : transaction
      )
    );
  }

  function exportCSV() {
    if (transactions.length === 0) {
      setMessage("Upload a statement before exporting.");
      return;
    }

    const headers = [
      "description",
      "amount",
      "category",
      "status",
      "reason",
    ];

    const escapeCSV = (value: string | number) =>
      `"${String(value).replace(/"/g, '""')}"`;

    const rows = transactions.map((transaction) =>
      [
        transaction.description,
        transaction.amount,
        transaction.category,
        transaction.status,
        transaction.reason,
      ]
        .map(escapeCSV)
        .join(",")
    );

    const csvContent = [headers.join(","), ...rows].join("\r\n");
    const blob = new Blob(["\uFEFF", csvContent], {
      type: "text/csv;charset=utf-8;",
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = "categorized_transactions.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);

    setMessage("Your reviewed transactions have been exported.");
  }

  const reviewCount = transactions.filter(
    (transaction) => transaction.status === "Needs Review"
  ).length;

  return (
    <main className="container">
      <header>
        <p className="eyebrow">FREELANCER FINANCE</p>
        <h1>Statement Categorizer</h1>
        <p className="subtitle">
          Organize transactions with transparent, rule-based categorization.
        </p>
      </header>

      <section className="upload-card">
        <h2>Upload your statement</h2>
        <p>Choose a CSV containing description and amount columns.</p>

        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setMessage("");
          }}
        />

        <button onClick={uploadStatement} disabled={loading}>
          {loading ? "Processing..." : "Upload and categorize"}
        </button>

        {message && (
          <p role="status" className="message">
            {message}
          </p>
        )}
      </section>

      {transactions.length > 0 && (
        <section className="results">
          <div className="results-heading">
            <div>
              <h2>Transaction review</h2>
              <p>{transactions.length} transactions processed</p>
            </div>

            <span>
              {reviewCount} {reviewCount === 1 ? "needs" : "need"} review
            </span>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Description</th>
                  <th>Amount</th>
                  <th>Category</th>
                  <th>Status</th>
                  <th>Reason</th>
                </tr>
              </thead>

              <tbody>
                {transactions.map((transaction, index) => (
                  <tr key={`${transaction.description}-${index}`}>
                    <td>{transaction.description}</td>
                    <td>{transaction.amount.toFixed(2)}</td>

                    <td>
                      <select
                        value={transaction.category}
                        onChange={(event) =>
                          updateCategory(index, event.target.value)
                        }
                        aria-label={`Category for ${transaction.description}`}
                      >
                        {!CATEGORIES.includes(transaction.category) && (
                          <option value={transaction.category}>
                            {transaction.category}
                          </option>
                        )}

                        {CATEGORIES.map((category) => (
                          <option key={category} value={category}>
                            {category}
                          </option>
                        ))}
                      </select>
                    </td>

                    <td>
                      <span
                        className={
                          transaction.status === "Needs Review"
                            ? "status review"
                            : "status"
                        }
                      >
                        {transaction.status}
                      </span>
                    </td>

                    <td>{transaction.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button className="export-button" onClick={exportCSV}>
            Export reviewed transactions (CSV)
          </button>
        </section>
      )}

      <footer>
        Categories are suggestions, not a determination of tax deductibility.
        Review transactions before using them for tax purposes.
      </footer>
    </main>
  );
}

export default App;
