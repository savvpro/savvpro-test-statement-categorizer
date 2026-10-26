export type Confidence = 'high' | 'medium' | 'low' | 'unknown'

export interface CategorizedTransaction {
  id: string
  date: string
  description: string
  amount: number
  category: string
  confidence: Confidence
  reason: string
  user_category: string | null
}

export interface CategorySummary {
  category: string
  total: number
  count: number
}

export interface CategorizeResponse {
  transactions: CategorizedTransaction[]
  summaries: CategorySummary[]
  needs_review_count: number
}
