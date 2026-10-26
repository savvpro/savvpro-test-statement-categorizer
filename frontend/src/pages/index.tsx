import { useState, useRef } from 'react'
import axios from 'axios'
import styles from '@/styles/Home.module.css'

interface Transaction {
  date: string
  description: string
  amount: number
  category: string
  confidence: string
}

interface CategorizationResponse {
  transactions: Transaction[]
  summary: Record<string, number>
  total_transactions: number
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CategorizationResponse | null>(null)
  const [editedCategories, setEditedCategories] = useState<Record<number, string>>({})
  const fileInputRef = useRef<HTMLInputElement>(null)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      if (!selectedFile.name.endsWith('.csv')) {
        setError('Please upload a CSV file')
        return
      }
      setFile(selectedFile)
      setError(null)
      setResult(null)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first')
      return
    }

    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await axios.post<CategorizationResponse>(
        `${API_URL}/api/upload`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      )
      setResult(response.data)
      setEditedCategories({})
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 'Failed to process file. Please try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  const handleCategoryChange = (index: number, newCategory: string) => {
    setEditedCategories(prev => ({
      ...prev,
      [index]: newCategory
    }))
  }

  const getEffectiveCategory = (index: number, originalCategory: string): string => {
    return editedCategories[index] || originalCategory
  }

  const calculateUpdatedSummary = (): Record<string, number> => {
    if (!result) return {}

    const summary: Record<string, number> = {
      'Software & Tools': 0,
      'Travel & Transport': 0,
      'Office & Supplies': 0,
      'Client Income': 0,
      'Expense Refund': 0,
      'Needs Review': 0,
    }

    result.transactions.forEach((transaction, index) => {
      const category = getEffectiveCategory(index, transaction.category)
      summary[category] = (summary[category] || 0) + 1
    })

    return summary
  }

  const handleReset = () => {
    setFile(null)
    setResult(null)
    setError(null)
    setEditedCategories({})
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const categories = [
    'Software & Tools',
    'Travel & Transport',
    'Office & Supplies',
    'Client Income',
    'Expense Refund',
    'Needs Review',
  ]

  const getCategoryColor = (category: string): string => {
    const colors: Record<string, string> = {
      'Software & Tools': '#3b82f6',
      'Travel & Transport': '#8b5cf6',
      'Office & Supplies': '#ec4899',
      'Client Income': '#10b981',
      'Expense Refund': '#f59e0b',
      'Needs Review': '#ef4444',
    }
    return colors[category] || '#6b7280'
  }

  const getConfidenceColor = (confidence: string): string => {
    if (confidence === 'High') return '#10b981'
    if (confidence === 'Medium') return '#f59e0b'
    return '#ef4444'
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Statement Categorizer</h1>
        <p className={styles.subtitle}>
          Upload your bank or credit card statement to automatically categorize transactions
        </p>
      </header>

      <main className={styles.main}>
        <div className={styles.uploadSection}>
          <div className={styles.uploadCard}>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className={styles.fileInput}
              id="file-upload"
            />
            <label htmlFor="file-upload" className={styles.fileLabel}>
              <svg className={styles.uploadIcon} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              {file ? file.name : 'Choose CSV file'}
            </label>
            
            <div className={styles.buttonGroup}>
              <button
                onClick={handleUpload}
                disabled={!file || loading}
                className={styles.uploadButton}
              >
                {loading ? 'Processing...' : 'Categorize Transactions'}
              </button>
              
              {(file || result) && (
                <button
                  onClick={handleReset}
                  className={styles.resetButton}
                >
                  Reset
                </button>
              )}
            </div>

            {error && (
              <div className={styles.error}>
                <svg className={styles.errorIcon} fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                {error}
              </div>
            )}
          </div>
        </div>

        {result && (
          <>
            <div className={styles.summarySection}>
              <h2 className={styles.sectionTitle}>Summary</h2>
              <div className={styles.summaryGrid}>
                {Object.entries(calculateUpdatedSummary()).map(([category, count]) => (
                  <div key={category} className={styles.summaryCard}>
                    <div 
                      className={styles.summaryIndicator}
                      style={{ backgroundColor: getCategoryColor(category) }}
                    />
                    <div className={styles.summaryContent}>
                      <div className={styles.summaryCategory}>{category}</div>
                      <div className={styles.summaryCount}>{count}</div>
                    </div>
                  </div>
                ))}
              </div>
              <div className={styles.totalCount}>
                Total Transactions: {result.total_transactions}
              </div>
            </div>

            <div className={styles.transactionsSection}>
              <h2 className={styles.sectionTitle}>Transactions</h2>
              <div className={styles.tableContainer}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Description</th>
                      <th>Amount</th>
                      <th>Category</th>
                      <th>Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.transactions.map((transaction, index) => {
                      const effectiveCategory = getEffectiveCategory(index, transaction.category)
                      const isEdited = editedCategories[index] !== undefined

                      return (
                        <tr key={index} className={isEdited ? styles.editedRow : ''}>
                          <td>{transaction.date}</td>
                          <td className={styles.description}>{transaction.description}</td>
                          <td className={transaction.amount >= 0 ? styles.positive : styles.negative}>
                            ${Math.abs(transaction.amount).toFixed(2)}
                          </td>
                          <td>
                            <select
                              value={effectiveCategory}
                              onChange={(e) => handleCategoryChange(index, e.target.value)}
                              className={styles.categorySelect}
                              style={{ 
                                borderColor: getCategoryColor(effectiveCategory),
                                backgroundColor: isEdited ? '#fef3c7' : 'white'
                              }}
                            >
                              {categories.map(cat => (
                                <option key={cat} value={cat}>{cat}</option>
                              ))}
                            </select>
                          </td>
                          <td>
                            <span 
                              className={styles.confidenceBadge}
                              style={{ backgroundColor: getConfidenceColor(transaction.confidence) }}
                            >
                              {transaction.confidence}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              
              {Object.keys(editedCategories).length > 0 && (
                <div className={styles.editNotice}>
                  <svg className={styles.infoIcon} fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  You've edited {Object.keys(editedCategories).length} transaction(s). Summary has been updated.
                </div>
              )}
            </div>
          </>
        )}
      </main>

      <footer className={styles.footer}>
        <p>Statement Categorizer - Built for Freelancers & Agencies</p>
      </footer>
    </div>
  )
}
