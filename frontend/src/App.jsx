import { useState } from "react";
import "./App.css";

const CATEGORIES = [
  "Software",
  "Cloud Services",
  "Travel",
  "Food",
  "Office Supplies",
  "Internet & Phone",
  "Transfer / Not Expense",
  "Refund",
  "Needs Review",
];

function App() {
  const [file, setFile] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [totals, setTotals] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
    setError("");
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a CSV file first.");
      return;
    }

    setLoading(true);
    setError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/categorize",
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to process statement.");
      }

      setTransactions(data.transactions);
      setTotals(data.totals);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const updateCategory = (index, newCategory) => {
    const updatedTransactions = [...transactions];

    updatedTransactions[index] = {
      ...updatedTransactions[index],
      category: newCategory,
      needs_review: newCategory === "Needs Review",
    };

    setTransactions(updatedTransactions);

    calculateTotals(updatedTransactions);
  };

  const calculateTotals = (items) => {
    const newTotals = {};

    items.forEach((transaction) => {
      const category = transaction.category;

      if (!newTotals[category]) {
        newTotals[category] = 0;
      }

      newTotals[category] += Math.abs(
        Number(transaction.amount)
      );
    });

    setTotals(newTotals);
  };

  return (
    <div className="app">
      <header>
        <h1>Freelancer Expense Categorizer</h1>
        <p>
          Upload a CSV statement and automatically categorize
          your transactions.
        </p>
      </header>

      <main>
        <section className="upload-card">
          <h2>Upload Statement</h2>

          <input
            type="file"
            accept=".csv"
            onChange={handleFileChange}
          />

          {file && (
            <p className="file-name">
              Selected: {file.name}
            </p>
          )}

          <button
            onClick={handleUpload}
            disabled={loading}
          >
            {loading ? "Analyzing..." : "Analyze Statement"}
          </button>

          {error && (
            <p className="error">
              {error}
            </p>
          )}
        </section>

        {Object.keys(totals).length > 0 && (
          <section>
            <h2>Category Summary</h2>

            <div className="summary-grid">
              {Object.entries(totals).map(
                ([category, total]) => (
                  <div
                    className="summary-card"
                    key={category}
                  >
                    <span>{category}</span>

                    <strong>
                      PKR {total.toLocaleString()}
                    </strong>
                  </div>
                )
              )}
            </div>
          </section>
        )}

        {transactions.length > 0 && (
          <section>
            <h2>Transactions</h2>

            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Description</th>
                    <th>Amount</th>
                    <th>Category</th>
                    <th>Confidence</th>
                    <th>Status</th>
                  </tr>
                </thead>

                <tbody>
                  {transactions.map(
                    (transaction, index) => (
                      <tr key={index}>
                        <td>
                          {transaction.date}
                        </td>

                        <td>
                          {transaction.description}
                        </td>

                        <td>
                          PKR{" "}
                          {Number(
                            transaction.amount
                          ).toLocaleString()}
                        </td>

                        <td>
                          <select
                            value={
                              transaction.category
                            }
                            onChange={(event) =>
                              updateCategory(
                                index,
                                event.target.value
                              )
                            }
                          >
                            {CATEGORIES.map(
                              (category) => (
                                <option
                                  key={category}
                                  value={category}
                                >
                                  {category}
                                </option>
                              )
                            )}
                          </select>
                        </td>

                        <td>
                          {Math.round(
                            transaction.confidence *
                              100
                          )}
                          %
                        </td>

                        <td>
                          {transaction.needs_review ? (
                            <span className="review">
                              Needs Review
                            </span>
                          ) : (
                            <span className="approved">
                              Categorized
                            </span>
                          )}
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;