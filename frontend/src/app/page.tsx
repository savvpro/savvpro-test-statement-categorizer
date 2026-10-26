"use client";
import { useState } from "react";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return alert("Please select a file first.");
    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      // Pointing to your working Django URL
      const response = await fetch("http://127.0.0.1:8000/categorizer/api/upload/", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      setResults(data.data);
    } catch (error) {
      console.error("Upload failed", error);
      alert("Failed to upload the statement.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 p-10">
      <div className="max-w-4xl mx-auto bg-white p-8 rounded-lg shadow">
        <h1 className="text-2xl font-bold mb-2 text-gray-800">Freelancer Statement Categorizer</h1>
        <p className="text-gray-600 mb-6">Upload your business bank statement (CSV) to automatically sort your transactions for tax time.</p>

        {/* Upload Section */}
        <div className="flex items-center gap-4 mb-8 p-4 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50">
          <input 
            type="file" 
            accept=".csv" 
            onChange={handleFileChange} 
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          <button 
            onClick={handleUpload} 
            disabled={loading}
            className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap"
          >
            {loading ? "Processing..." : "Categorize Statement"}
          </button>
        </div>

        {/* Results Table */}
        {results.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-100 text-gray-700 uppercase text-xs">
                  <th className="p-4 border-b">Date</th>
                  <th className="p-4 border-b">Description</th>
                  <th className="p-4 border-b">Amount</th>
                  <th className="p-4 border-b">Category</th>
                  <th className="p-4 border-b">Status</th>
                </tr>
              </thead>
              <tbody>
                {results.map((row, index) => (
                  <tr key={index} className="border-b hover:bg-gray-50">
                    <td className="p-4 text-gray-600">{row.date}</td>
                    <td className="p-4 font-medium text-gray-800">{row.description}</td>
                    <td className="p-4 text-gray-600">${Math.abs(row.amount).toFixed(2)}</td>
                    <td className="p-4">
                      {row.status === "Pending" ? (
                        <select className="border border-red-300 rounded p-1 text-sm bg-red-50 text-red-700 focus:outline-none focus:ring-2 focus:ring-red-500">
                          <option value="Needs Review">Needs Review...</option>
                          <option value="Software & Tools">Software & Tools</option>
                          <option value="Travel">Travel</option>
                          <option value="Hardware & Office">Hardware & Office</option>
                          <option value="Income">Income</option>
                          <option value="Meals & Entertainment">Meals & Entertainment</option>
                        </select>
                      ) : (
                        <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full font-medium">
                          {row.category}
                        </span>
                      )}
                    </td>
                    <td className="p-4 text-sm text-gray-500">{row.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}